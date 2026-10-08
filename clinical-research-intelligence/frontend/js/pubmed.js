const $ = id => document.getElementById(id);
let articles = [];

$("btnSearch").onclick = e => withButton(e.target, "Searching...", async () => {
  showMsg("msg", "");
  const q = $("query").value.trim();
  if (!q && !$("sample").checked) return showMsg("msg", "Please type a search topic.");
  try {
    const url = `/api/pubmed/search?query=${encodeURIComponent(q)}&max_results=${$("max").value}&use_sample=${$("sample").checked}`;
    const r = await api(url);
    articles = r.articles;
    $("resultsCard").classList.remove("hidden");
    $("resultsTitle").textContent = `${r.count} article(s) - source: ${r.source}`;
    $("results").innerHTML = articles.length ? articles.map((a, i) =>
      `<div class="article"><h4>${esc(a.title)}</h4>` +
      `<div class="meta">${esc(a.authors.slice(0, 4).join(", "))}${a.authors.length > 4 ? " et al." : ""} &middot; ${esc(a.journal)} &middot; ${esc(a.publication_date)}</div>` +
      `<div class="meta">PMID ${esc(a.pmid)} &middot; DOI ${esc(a.doi || "n/a")} &middot; ${esc(a.study_type || "type n/a")}</div>` +
      `<p><button class="secondary" onclick="openArticle(${i})">View details &amp; AI analysis</button></p></div>`).join("")
      : "<p>No articles found.</p>";
  } catch (err) { showMsg("msg", err.message); }
});

function analysisHtml(an) {
  if (!an) return "<p class='meta'>No AI analysis yet.</p>";
  return `<div class="kv"><b>Summary</b><div>${esc(an.summary)}</div><b>Key findings</b><div><ul class="clean">${an.key_findings.map(k => `<li>${esc(k)}</li>`).join("")}</ul></div>` +
    `<b>Study type</b><div>${esc(an.study_type)}</div><b>Population</b><div>${esc(an.study_population)}</div><b>Methodology</b><div>${esc(an.methodology)}</div>` +
    `<b>Model</b><div class="meta">${esc(an.model_used || "")}</div></div>`;
}

// If an image link fails, try the other PubMed Central mirror once, then give up quietly.
function imgFallback(img) {
  const epmc = "https://europepmc.org/articles/", ncbi = "https://pmc.ncbi.nlm.nih.gov/articles/";
  if (img.dataset.tried) { img.style.display = "none"; return; }
  img.dataset.tried = "1";
  if (img.src.startsWith(epmc)) img.src = ncbi + img.src.slice(epmc.length);
  else if (img.src.startsWith(ncbi)) img.src = epmc + img.src.slice(ncbi.length);
  else img.style.display = "none";
}

function figuresHtml(a) {
  if (!a.figures.length) return "<p class='meta'>No figures saved. Click 'Get full text &amp; figures' (works for open-access PMC articles).</p>";
  return a.figures.map(f => {
    const an = f.ai_analysis, src = f.web_url || f.image_url;
    const status = f.web_url ? "(image saved on server - analysis can use the image)"
      : f.image_url ? "(image linked from PubMed Central - analysis uses the caption unless the server can download it)"
      : "(caption only - no image available)";
    return `<div class="card" style="background:#fafbff">` +
      (src ? `<img class="fig" src="${esc(src)}" alt="${esc(f.label)}" onerror="imgFallback(this)"><br>` : "") +
      `<b>${esc(f.label)}</b> <span class="meta">${status}</span>` +
      (f.image_url ? ` <a class="meta" href="${esc(f.image_url)}" target="_blank" rel="noopener">open image link</a>` : "") +
      `<p>${esc(f.caption)}</p>` +
      `<button class="secondary" onclick="analyzeFigure(${f.id}, this)">Analyze figure with Groq</button>` +
      `<div id="fig${f.id}">${an ? figAnalysisHtml(an, f.analysis_type) : ""}</div></div>`;
  }).join("");
}

function figAnalysisHtml(an, type) {
  const label = type === "image+caption" ? "Image + caption analysis (multimodal)" : "Caption/context-based analysis (image pixels were NOT analyzed)";
  return `<div class="notice"><b>${esc(label)}</b></div><div class="kv"><b>Figure type</b><div>${esc(an.figure_type)}</div>` +
    `<b>Description</b><div>${esc(an.description)}</div><b>Groups</b><div>${esc([].concat(an.study_groups || []).join("; "))}</div>` +
    `<b>Sample sizes</b><div>${esc(an.sample_sizes)}</div><b>Outcomes</b><div>${esc(an.outcomes)}</div>` +
    `<b>Key findings</b><div><ul class="clean">${[].concat(an.key_findings || []).map(k => `<li>${esc(k)}</li>`).join("")}</ul></div>` +
    `<b>Significance</b><div>${esc(an.statistical_significance)}</div></div>`;
}

function renderDetail(a) {
  $("detail").classList.remove("hidden");
  $("detail").innerHTML = `<h3>${esc(a.title)}</h3>` +
    `<div class="kv"><b>PMID</b><div>${esc(a.pmid)}</div><b>Authors</b><div>${esc(a.authors.join(", "))}</div><b>Journal</b><div>${esc(a.journal)} (${esc(a.publication_date)})</div>` +
    `<b>DOI</b><div>${esc(a.doi || "n/a")}</div><b>Study type</b><div>${esc(a.study_type)}</div><b>Topic</b><div>${esc(a.research_topic)}</div>` +
    `<b>Keywords</b><div>${esc(a.keywords.join(", "))}</div><b>References</b><div>${a.references.length} listed${a.has_full_text ? " &middot; full text saved" : ""}</div></div>` +
    `<h4>Abstract</h4><p>${nl2br(a.abstract)}</p>` +
    `<p><button id="btnAnalyze">Analyze with Groq</button> <button class="secondary" id="btnFigs">Get full text &amp; figures</button></p>` +
    `<div id="dmsg" class="msg"></div>` +
    `<h4>AI analysis</h4><div id="analysis">${analysisHtml(a.analysis)}</div><h4>Figures</h4><div id="figures">${figuresHtml(a)}</div>`;
  $("btnAnalyze").onclick = e => withButton(e.target, "Asking Groq...", async () => {
    showMsg("dmsg", "");
    try { const r = await jsonPost("/api/pubmed/analyze", { pmid: a.pmid }); $("analysis").innerHTML = analysisHtml({ ...r, model_used: r.model }); }
    catch (err) { showMsg("dmsg", err.message); }
  });
  $("btnFigs").onclick = e => withButton(e.target, "Loading...", async () => {
    showMsg("dmsg", "");
    try {
      const r = await jsonPost("/api/pubmed/figures", { pmid: a.pmid });
      $("figures").innerHTML = figuresHtml(r.article);
      showMsg("dmsg", `${r.figures_found} figure(s), ${r.images_downloaded} image(s) downloaded. ${r.notes.join(" ")}`, "info");
    } catch (err) { showMsg("dmsg", err.message); }
  });
  $("detail").scrollIntoView({ behavior: "smooth" });
}

async function openArticle(i) {
  try { renderDetail(await api("/api/pubmed/article/" + articles[i].pmid)); } catch (err) { showMsg("msg", err.message); }
}

async function analyzeFigure(id, button) {
  await withButton(button, "Asking Groq...", async () => {
    try {
      const r = await jsonPost("/api/pubmed/analyze-figure", { figure_id: id });
      $("fig" + id).innerHTML = (r.note ? `<div class="msg info">${esc(r.note)}</div>` : "") + figAnalysisHtml(r.analysis, r.analysis_type);
    } catch (err) { $("fig" + id).innerHTML = `<div class="msg error">${esc(err.message)}</div>`; }
  });
}