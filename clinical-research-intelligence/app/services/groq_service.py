"""
groq_service.py - the ONLY file that talks to Groq.

Groq gives us a hosted LLM through an OpenAI-style REST API:
    POST https://api.groq.com/openai/v1/chat/completions
    Header : Authorization: Bearer <GROQ_API_KEY>
    Body   : {"model": "...", "messages": [{"role": "system"|"user", "content": "..."}],
              "response_format": {"type": "json_object"}}      <- asks for JSON back
    Reply  : {"choices": [{"message": {"content": "<the model's text>"}}]}

Rules we follow:
  * The model only INTERPRETS text that Python already extracted. It never extracts or compares.
  * The prompt tells the model: use only the given text, write "Not stated" if unsure.
  * The key is read from .env and is never printed or returned to the browser.
"""
import base64
import json
import re

import httpx

from app.config import settings
from app.errors import ServiceError

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_CHARS = 12000          # keep prompts small for the free tier
MAX_IMAGE_BYTES = 3_500_000  # Groq limits base64 images to ~4 MB


class GroqService:
    def __init__(self, api_key=None, model=None, vision_model=None):
        self.api_key = settings.groq_api_key if api_key is None else api_key
        self.model = model or settings.groq_model
        self.vision_model = vision_model or settings.groq_vision_model

    # ------------------------------------------------------------ low level
    def _chat(self, messages, model=None) -> dict:
        """Send messages to Groq, return the reply parsed as a dictionary."""
        if not self.api_key or self.api_key == "your_api_key_here":
            raise ServiceError("Groq is not configured. Add GROQ_API_KEY to your .env file.", 503)
        body = {"model": model or self.model, "messages": messages, "temperature": 0.2,
                "response_format": {"type": "json_object"}}
        try:
            response = httpx.post(GROQ_URL, json=body, timeout=60,
                                  headers={"Authorization": f"Bearer {self.api_key}"})
        except httpx.HTTPError:
            raise ServiceError("Could not reach Groq. Check your internet connection.", 503)
        if response.status_code == 401:
            raise ServiceError("Groq rejected the API key. Check GROQ_API_KEY in .env.", 401)
        if response.status_code == 429:
            raise ServiceError("Groq free-tier rate limit reached. Wait a minute and try again.", 429)
        if response.status_code != 200:
            raise ServiceError(f"Groq returned an error (HTTP {response.status_code}).", 502)
        try:
            text = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError):
            raise ServiceError("Groq sent an unexpected reply.", 502)
        return self._parse_json(text)

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Models sometimes wrap JSON in ```json fences. Strip them, then parse."""
        text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
        try:
            return json.loads(text)
        except ValueError:
            match = re.search(r"\{.*\}", text, re.S)
            if match:
                try:
                    return json.loads(match.group())
                except ValueError:
                    pass
        raise ServiceError("The AI reply was not valid JSON. Please try again.", 502)

    # ------------------------------------------------------------ the three jobs
    def summarize_article(self, article_text: str) -> dict:
        if not article_text or not article_text.strip():
            raise ServiceError("There is no abstract text to analyze.", 400)
        system = ("You are a careful medical research assistant. Use ONLY the text the user gives you. "
                  "If something is not stated, write 'Not stated'. Never invent numbers. "
                  "Reply with a JSON object with exactly these keys: "
                  "summary (2-3 sentences, plain English), key_findings (list of 3-5 short strings), "
                  "study_type (e.g. randomized controlled trial, cohort study, review), "
                  "study_population (who was studied), methodology (how it was done, 1-2 sentences).")
        result = self._chat([{"role": "system", "content": system},
                             {"role": "user", "content": article_text[:MAX_CHARS]}])
        return self._with_defaults(result, {"summary": "", "key_findings": [], "study_type": "Not stated",
                                            "study_population": "Not stated", "methodology": "Not stated"})

    def analyze_trial(self, trial_text: str) -> dict:
        system = ("You are a clinical research analyst. Use ONLY the trial information given. "
                  "If something is not stated, write 'Not stated'. Reply with a JSON object with exactly "
                  "these keys, each a short string (1-2 sentences): "
                  "investigating (what is the trial investigating), intervention (which drug/intervention is evaluated), "
                  "indication (which disease/indication is targeted), population (who is studied), "
                  "primary_objective (the main research objective), differentiator (what makes this trial different "
                  "from a typical trial for this indication), development_stage (stage of development, e.g. early safety, "
                  "proof of concept, confirmatory).")
        result = self._chat([{"role": "system", "content": system},
                             {"role": "user", "content": trial_text[:MAX_CHARS]}])
        keys = ["investigating", "intervention", "indication", "population",
                "primary_objective", "differentiator", "development_stage"]
        return self._with_defaults(result, {k: "Not stated" for k in keys})

    def analyze_figure(self, caption: str, article_context: str, image_bytes=None, mime_type="image/jpeg") -> dict:
        """
        Two honest modes:
          * image_bytes given  -> multimodal call (image + caption + context) with the vision model
          * no image           -> caption/context-based analysis with the normal text model
        The result always says which mode produced it in the key 'analysis_type'.
        """
        system = ("You analyze figures from medical research papers. Use ONLY what is provided. "
                  "Never invent numbers. If something is not stated or not visible, write 'Not stated'. "
                  "Reply with a JSON object with exactly these keys: "
                  "figure_type (graph, flowchart, table, clinical image, diagram, other), "
                  "description (2-3 sentences), study_groups (list of strings), sample_sizes (string), "
                  "outcomes (string), key_findings (list of short strings), statistical_significance (string).")
        context = f"Figure caption:\n{caption or 'No caption'}\n\nArticle context:\n{article_context[:6000]}"

        if image_bytes and len(image_bytes) <= MAX_IMAGE_BYTES:
            data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode()}"
            messages = [{"role": "system", "content": system},
                        {"role": "user", "content": [{"type": "text", "text": context},
                                                     {"type": "image_url", "image_url": {"url": data_url}}]}]
            result = self._chat(messages, model=self.vision_model)
            result["analysis_type"] = "image+caption"
        else:
            result = self._chat([{"role": "system", "content": system},
                                 {"role": "user", "content": context}])
            result["analysis_type"] = "caption/context-based"
        return result

    @staticmethod
    def _with_defaults(result: dict, defaults: dict) -> dict:
        """Make sure every expected key exists, even if the model forgot one."""
        return {key: result.get(key, default) for key, default in defaults.items()}
