const $ = id => document.getElementById(id);
let trials = [], lastComparison = null;

const selected = () => [...document.querySelectorAll(".pick:checked")].map(c => c.value);

$("btnSearch").onclick = e => withButton(e.target, "Searching...", async () => {
  showMsg("msg", ""); $("compareCard").classList.add("hidden");
  try {
    let url = `/api/trials/search?drug=${encodeURIComponent($("drug").value)}&indication=${encodeURIComponent($("indication").value)}` +
              `&use_sample=${$("sample").checked}` + ($("recent").checked ? "&days=30" : "");
    const r = await api(url);
    trials = r.trials;
    $("resultsCard").classList.remove("hidden");
    $("resultsTitle").textContent = `${r.count} trial(s) found - source: ${r.source}`;
    $("aiBox").innerHTML = "";
    if (!trials.length) { $("resultsTable").innerHTML = ""; return showMsg("msg", "No trials found. (The sample data only contains pembrolizumab + melanoma trials.)", "info"); }
    $("resultsTable").innerHTML = "<tr><th></th><th>NCT ID</th><th>Title</th><th>Phase</th><th>Status</th><th>Drugs</th><th>Sponsor</th><th>Updated</th></tr>" +
      trials.map((t, i) => `<tr><td><input type="checkbox" class="pick" value="${esc(t.nct_id)}" ${i < 3 ? "checked" : ""}></td>` +
        `<td>${esc(t.nct_id)}</td><td>${esc(t.data.study_title)}</td><td>${esc(t.data.phase)}</td><td>${esc(t.data.recruitment_status)}</td>` +
        `<td>${esc(t.data.drugs.join(", "))}</td><td>${esc(t.data.sponsor)}</td><td>${esc(t.data.last_update_date)}</td></tr>`).join("");
  } catch (err) { showMsg("msg", err.message); }
});

function analysisCard(nctId, a) {
  return `<div class="card" style="background:#faf8ff"><h4>${esc(nctId)} <span class="pill ai">AI</span></h4><div class="kv">` +
    `<b>Investigating</b><div>${esc(a.investigating)}</div><b>Intervention</b><div>${esc(a.intervention)}</div>` +
    `<b>Indication</b><div>${esc(a.indication)}</div><b>Population</b><div>${esc(a.population)}</div>` +
    `<b>Primary objective</b><div>${esc(a.primary_objective)}</div><b>Differentiator</b><div>${esc(a.differentiator)}</div>` +
    `<b>Development stage</b><div>${esc(a.development_stage)}</div></div></div>`;
}

$("btnAnalyze").onclick = e => withButton(e.target, "Asking Groq...", async () => {
  showMsg("msg", "");
  const ids = selected();
  if (!ids.length) return showMsg("msg", "Tick at least one trial.");
  try {
    const r = await jsonPost("/api/trials/analyze", { nct_ids: ids });
    $("aiBox").innerHTML = r.results.map(x => analysisCard(x.nct_id, x.analysis)).join("") +
      r.errors.map(x => `<div class="msg error">${esc(x.nct_id)}: ${esc(x.error)}</div>`).join("");
  } catch (err) { showMsg("msg", err.message); }
});

function drawComparison() {
  if (!lastComparison) return;
  const only = $("onlyDiff").checked;
  const head = "<tr><th>Category</th>" + lastComparison.trials.map(t => `<th>${esc(t.nct_id)}<div class="meta" style="font-weight:400">${esc(t.title)}</div></th>`).join("") + "</tr>";
  const rows = lastComparison.rows.filter(r => !only || r.differs).map(r =>
    `<tr class="${r.differs ? "diffrow" : ""}"><td>${esc(r.category)}${r.ai ? ' <span class="pill ai">AI</span>' : ""}${r.differs ? " &#9888;" : ""}</td>` +
    r.values.map(v => `<td><div class="cell">${nl2br(v)}</div></td>`).join("") + "</tr>").join("");
  $("compareTable").innerHTML = `<table>${head}${rows}</table>`;
}
$("onlyDiff").onchange = drawComparison;

$("btnCompare").onclick = e => withButton(e.target, "Comparing...", async () => {
  showMsg("msg", "");
  const ids = selected();
  if (ids.length < 2 || ids.length > 4) return showMsg("msg", "Tick between 2 and 4 trials to compare.");
  try {
    lastComparison = await jsonPost("/api/trials/compare", { nct_ids: ids });
    $("compareCard").classList.remove("hidden"); drawComparison();
    $("compareCard").scrollIntoView({ behavior: "smooth" });
  } catch (err) { showMsg("msg", err.message); }
});
