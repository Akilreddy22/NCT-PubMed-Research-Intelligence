// NCT page: upload / fetch / compare / history.
const $ = id => document.getElementById(id);

function renderResult(r) {
  $("result").classList.remove("hidden");
  $("resTitle").textContent = `${r.nct_id} - version ${r.previous_version} \u2192 version ${r.current_version}`;
  $("resBadges").innerHTML =
    `<span class="pill added">${r.summary.added} added</span><span class="pill removed">${r.summary.removed} removed</span>` +
    `<span class="pill modified">${r.summary.modified} modified</span>`;

  if (r.previous_source !== r.current_source)
    showMsg("msg", "Note: the two versions came from different sources (" + r.previous_source + " vs " + r.current_source +
      "), so some differences may come from formatting.", "info");

  // Change log table
  if (!r.changes.length) {
    $("viewLog").innerHTML = "<p>No meaningful changes found.</p>";
  } else {
    $("viewLog").innerHTML = "<table><tr><th>Field</th><th>Change</th><th>Previous</th><th>Current</th><th>Changed at</th></tr>" +
      r.changes.map(c => {
        let extra = "";
        if (c.added_items.length) extra += "<div><b>Added:</b><ul class='clean'>" + c.added_items.map(i => `<li>${esc(i)}</li>`).join("") + "</ul></div>";
        if (c.removed_items.length) extra += "<div><b>Removed:</b><ul class='clean'>" + c.removed_items.map(i => `<li>${esc(i)}</li>`).join("") + "</ul></div>";
        return `<tr class="${c.change_type}"><td><b>${esc(c.label)}</b><br><span class="meta">${esc(c.field)}</span></td>` +
          `<td><span class="pill ${c.change_type}">${c.change_type}</span></td>` +
          `<td class="old"><div class="cell">${nl2br(c.previous_value) || "-"}</div></td>` +
          `<td class="new"><div class="cell">${nl2br(c.new_value) || "-"}</div>${extra ? "<hr>" + extra : ""}</td>` +
          `<td class="meta">${esc(c.changed_at.replace("T", " "))}<br>v${c.previous_version} \u2192 v${c.current_version}</td></tr>`;
      }).join("") + "</table>";
  }

  // Side-by-side table
  $("viewSide").innerHTML = "<table><tr><th>Field</th><th>Previous</th><th>Current</th><th>Status</th></tr>" +
    r.side_by_side.map(row => `<tr class="${row.status}"><td>${esc(row.label)}</td>` +
      `<td class="old"><div class="cell">${nl2br(row.previous)}</div></td><td class="new"><div class="cell">${nl2br(row.current)}</div></td>` +
      `<td><span class="pill ${row.status}">${row.status}</span></td></tr>`).join("") + "</table>";
  $("result").scrollIntoView({ behavior: "smooth" });
  loadStudies(r.nct_id);
}

$("tabLog").onclick = () => { $("viewLog").classList.remove("hidden"); $("viewSide").classList.add("hidden"); $("tabLog").className = "on"; $("tabSide").className = ""; };
$("tabSide").onclick = () => { $("viewSide").classList.remove("hidden"); $("viewLog").classList.add("hidden"); $("tabSide").className = "on"; $("tabLog").className = ""; };

$("btnDemo").onclick = e => withButton(e.target, "Comparing...", async () => {
  showMsg("msg", "");
  try { renderResult(await api("/api/nct/demo", { method: "POST" })); } catch (err) { showMsg("msg", err.message); }
});

$("btnUpload").onclick = e => withButton(e.target, "Comparing...", async () => {
  showMsg("msg", "");
  if (!$("filePrev").files[0] || !$("fileCur").files[0]) return showMsg("msg", "Please choose both the previous and the current HTML file.");
  const form = new FormData();
  form.append("previous", $("filePrev").files[0]); form.append("current", $("fileCur").files[0]);
  form.append("nct_id", $("nctManual").value);
  try { renderResult(await api("/api/nct/compare", { method: "POST", body: form })); } catch (err) { showMsg("msg", err.message); }
});

$("btnFetch").onclick = e => withButton(e.target, "Fetching...", async () => {
  showMsg("msg", "");
  if (!$("url").value.trim()) return showMsg("msg", "Please enter a ClinicalTrials.gov URL.");
  try {
    const r = await jsonPost("/api/nct/fetch", { url: $("url").value });
    if (r.comparison) { renderResult(r.comparison); }
    else showMsg("msg", `${r.nct_id}: version ${r.version_number} stored (via ${r.fetched_via}). ${r.message || ""}`, "ok");
    loadStudies(r.nct_id);
  } catch (err) { showMsg("msg", err.message); }
});

// Version history section
async function loadStudies(select) {
  const studies = await api("/api/nct");
  $("studySelect").innerHTML = '<option value="">- select a study -</option>' +
    studies.map(s => `<option value="${esc(s.nct_id)}">${esc(s.nct_id)} (${s.versions} versions)</option>`).join("");
  if (select) { $("studySelect").value = select; loadStudy(select); }
}

async function loadStudy(nctId) {
  if (!nctId) { $("historyCard").classList.add("hidden"); return; }
  const s = await api("/api/nct/" + nctId);
  const options = s.versions.map(v => `<option value="${v.version_number}">v${v.version_number} (${esc(v.created_at.replace("T", " "))})</option>`).join("");
  $("fromV").innerHTML = options; $("toV").innerHTML = options;
  if (s.versions.length > 1) $("toV").value = s.versions[s.versions.length - 1].version_number;
  $("historyCard").classList.remove("hidden");
  $("history").innerHTML = s.history.length ? s.history.map(g =>
    `<h4>v${g.previous_version} \u2192 v${g.current_version} <span class="meta">(${esc(g.changed_at.replace("T", " "))})</span></h4>` +
    "<table><tr><th>Field</th><th>Type</th><th>Previous</th><th>Current</th></tr>" + g.changes.map(c =>
      `<tr><td>${esc(c.field)}</td><td><span class="pill ${c.change_type}">${c.change_type}</span></td>` +
      `<td><div class="cell">${nl2br(c.previous_value)}</div></td><td><div class="cell">${nl2br(c.new_value)}</div></td></tr>`).join("") + "</table>"
  ).join("<br>") : "<p>No comparisons saved yet for this study.</p>";
}
$("studySelect").onchange = () => loadStudy($("studySelect").value).catch(err => showMsg("msg", err.message));

$("btnVersions").onclick = e => withButton(e.target, "Comparing...", async () => {
  showMsg("msg", "");
  if (!$("studySelect").value) return showMsg("msg", "Select a study first.");
  try {
    renderResult(await jsonPost("/api/nct/compare-versions",
      { nct_id: $("studySelect").value, from_version: +$("fromV").value, to_version: +$("toV").value }));
  } catch (err) { showMsg("msg", err.message); }
});

loadStudies().catch(() => {});
