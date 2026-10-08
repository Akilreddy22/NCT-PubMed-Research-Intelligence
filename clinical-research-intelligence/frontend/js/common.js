// Shared helpers used by every page.

// Call our FastAPI backend and return the JSON. Throws an Error with a friendly message.
async function api(url, options) {
  let response;
  try {
    response = await fetch(url, options);
  } catch (e) {
    throw new Error("Cannot reach the server. Is the app running?");
  }
  let data = {};
  try { data = await response.json(); } catch (e) { /* no JSON body */ }
  if (!response.ok) {
    let detail = data.detail;
    if (Array.isArray(detail)) detail = detail.map(d => d.msg).join("; ");   // FastAPI validation errors
    throw new Error(detail || "Request failed (HTTP " + response.status + ")");
  }
  return data;
}

// Escape text before putting it into innerHTML (prevents HTML injection).
function esc(value) {
  return String(value === null || value === undefined ? "" : value)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function showMsg(id, text, kind) {
  const el = document.getElementById(id);
  el.className = "msg " + (kind || "error");
  el.textContent = text || "";
  if (!text) el.className = "msg";
}

// Disable a button while a request is running.
async function withButton(button, label, fn) {
  const original = button.textContent;
  button.disabled = true; button.textContent = label;
  try { return await fn(); } finally { button.disabled = false; button.textContent = original; }
}

function jsonPost(url, body) {
  return api(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

function nl2br(text) { return esc(text).replace(/\n/g, "<br>"); }
