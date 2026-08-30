const API = "";

async function api(path, opts = {}) {
  const res = await fetch(`${API}${path}`, { credentials: "include", ...opts });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.message || res.statusText);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

const $ = (s) => document.querySelector(s);
const authGate = $("#authGate");
const app = $("#app");

async function checkSession() {
  try {
    const h = await api("/api/forense/health");
    $("#licenseLine").textContent = h.license?.valid
      ? `Licencia activa · ${h.build}`
      : `Sin licencia: ${h.license?.detail || "—"}`;
    await api("/api/forense/auth/me");
    authGate.classList.add("hidden");
    app.classList.remove("hidden");
    refreshJobs();
  } catch {
    authGate.classList.remove("hidden");
    app.classList.add("hidden");
  }
}

$("#authForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const pin = $("#authPin").value;
  $("#authHint").textContent = "";
  try {
    await api("/api/forense/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin }),
    });
    await checkSession();
  } catch (err) {
    $("#authHint").textContent = err.message;
  }
});

let pollTimer = null;
let currentJobId = null;

async function refreshJobs() {
  const data = await api("/api/forense/jobs");
  const ul = $("#jobList");
  ul.innerHTML = "";
  for (const j of data.jobs || []) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = `${j.title || j.id} · ${j.status} (${j.progress || 0}%)`;
    btn.classList.toggle("active", j.id === currentJobId);
    btn.onclick = () => selectJob(j.id);
    li.appendChild(btn);
    ul.appendChild(li);
  }
}

async function selectJob(id) {
  currentJobId = id;
  $("#emptyState").classList.add("hidden");
  $("#jobView").classList.remove("hidden");
  await loadJob(id);
  refreshJobs();
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(() => loadJob(id, true), 2000);
}

async function loadJob(id, quiet = false) {
  const data = await api(`/api/forense/jobs/${id}`);
  const j = data.job;
  $("#jobTitle").textContent = j.title || id;
  $("#jobMeta").textContent = `${j.site || ""} · ${j.status} · ${(j.analysis?.event_count || 0)} eventos`;

  const pw = $("#progressWrap");
  if (j.status === "processing" || j.status === "queued") {
    pw.classList.remove("hidden");
    $("#progressBar").style.width = `${j.progress || 0}%`;
    $("#progressText").textContent = j.progress_message || "";
  } else {
    pw.classList.add("hidden");
    if (j.status === "done" && pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  const tl = $("#timeline");
  tl.innerHTML = "";
  for (const ev of j.analysis?.timeline || []) {
    const li = document.createElement("li");
    li.className = `sev-${ev.severity || "medium"}`;
    li.textContent = `${ev.time_label} · ${ev.type}: ${ev.message}`;
    tl.appendChild(li);
  }
  if (!tl.children.length) {
    tl.innerHTML = "<li class='muted'>Sin eventos detectados en el muestreo.</li>";
  }

  const kf = $("#keyframes");
  kf.innerHTML = "";
  for (const frame of j.analysis?.keyframes || []) {
    if (!frame.image) continue;
    const img = document.createElement("img");
    img.src = `/api/forense/jobs/${id}/keyframes/${frame.image}`;
    img.alt = frame.time_label;
    img.title = (frame.events || []).join("; ");
    kf.appendChild(img);
  }

  if (j.status === "done") {
    const md = await api(`/api/forense/jobs/${id}/report.md`);
    $("#reportMd").textContent = md;
    const dl = $("#downloadMd");
    dl.href = `/api/forense/jobs/${id}/report.md`;
    dl.download = `forense-${id}.md`;
  } else if (!quiet) {
    $("#reportMd").textContent = "Informe disponible al completar el análisis…";
  }
}

$("#uploadForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = $("#caseVideo").files?.[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("video", file);
  fd.append("title", $("#caseTitle").value);
  fd.append("site", $("#caseSite").value);
  fd.append("meters_per_pixel", $("#caseMpp").value);
  fd.append("profile", "epp_completo");
  try {
    const res = await api("/api/forense/jobs", { method: "POST", body: fd });
    await refreshJobs();
    selectJob(res.job.id);
  } catch (err) {
    alert(err.message);
  }
});

checkSession();
