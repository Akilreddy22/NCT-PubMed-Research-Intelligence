from typing import List

from pydantic import BaseModel, Field


class TrialAnalyzeRequest(BaseModel):
    nct_ids: List[str] = Field(min_length=1, max_length=5)
    force: bool = False              # True = ignore saved analysis and ask Groq again


class TrialCompareRequest(BaseModel):
    nct_ids: List[str] = Field(min_length=2, max_length=4)
