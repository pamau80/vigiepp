const API = "";
const TEMPLATE_DEFAULTS = {
  general: { meters_per_pixel: 0.045, max_machinery_kmh: 15, max_person_kmh: 8, min_distance_m: 2 },
  mineria: { meters_per_pixel: 0.05, max_machinery_kmh: 12, max_person_kmh: 6, min_distance_m: 3 },
  portuario: { meters_per_pixel: 0.045, max_machinery_kmh: 18, max_person_kmh: 8, min_distance_m: 2.5 },
  bodega: { meters_per_pixel: 0.04, max_machinery_kmh: 15, max_person_kmh: 8, min_distance_m: 2 },
  construccion: { meters_per_pixel: 0.048, max_machinery_kmh: 10, max_person_kmh: 6, min_distance_m: 2.5 },
};

async function api(path, opts = {}) {
  const token = sessionStorage.getItem("forense.token");
  const headers = { ...(opts.headers || {}) };
  if (token) headers["X-VigiEPP-Key"] = token;
  const res = await fetch(`${API}${path}`, { credentials: "include", ...opts, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.message || res.statusText);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

function captureBridgeToken() {
  const params = new URLSearchParams(window.location.search);
  const key = params.get("key");
  if (key) {
    sessionStorage.setItem("forense.token", key);
    params.delete("key");
    const qs = params.toString();
    const clean = `${window.location.pathname}${qs ? `?${qs}` : ""}`;
    window.history.replaceState({}, "", clean);
  }
}

const $ = (s) => document.querySelector(s);
const authGate = $("#authGate");
const app = $("#app");

let templatesCache = [];

function applyTemplateDefaults(templateId) {
  const d = TEMPLATE_DEFAULTS[templateId] || TEMPLATE_DEFAULTS.general;
  $("#caseMpp").value = d.meters_per_pixel;
  $("#caseMachKmh").value = d.max_machinery_kmh;
  $("#casePersonKmh").value = d.max_person_kmh;
  $("#caseMinDist").value = d.min_distance_m;
  const tpl = templatesCache.find((t) => t.id === templateId);
  $("#templateHint").textContent = tpl ? `Perfil: ${tpl.profile}` : "";
}

async function loadTemplates() {
  const data = await api("/api/forense/templates");
  templatesCache = data.templates || [];
  const sel = $("#caseTemplate");
  sel.innerHTML = "";
  for (const t of templatesCache) {
    const opt = document.createElement("option");
    opt.value = t.id;
    opt.textContent = t.name;
    sel.appendChild(opt);
  }
  sel.onchange = () => applyTemplateDefaults(sel.value);
  applyTemplateDefaults(sel.value || "general");
}

function refreshReferenceSelect(jobs) {
  const sel = $("#caseReference");
  const current = sel.value;
  sel.innerHTML = '<option value="">— Sin referencia —</option>';
  for (const j of jobs || []) {
    if (j.status !== "done") continue;
    const opt = document.createElement("option");
    opt.value = j.id;
    opt.textContent = `${j.title || j.id} (${j.event_count || 0} ev.)`;
    sel.appendChild(opt);
  }
  if (current) sel.value = current;
}

async function checkSession() {
  try {
    const h = await api("/api/forense/health");
    $("#licenseLine").textContent = h.license?.valid
      ? `Licencia activa · ${h.build}`
      : `Sin licencia: ${h.license?.detail || "—"}`;
    const st = await fetch("/api/forense/auth/status", { credentials: "include", headers: sessionStorage.getItem("forense.token") ? { "X-VigiEPP-Key": sessionStorage.getItem("forense.token") } : {} }).then((r) => r.json());
    if (st.can_access) {
      authGate.classList.add("hidden");
      app.classList.remove("hidden");
      await loadTemplates();
      await refreshJobs();
      return;
    }
  } catch {
    /* mostrar gate */
  }
  authGate.classList.remove("hidden");
  app.classList.add("hidden");
}

$("#authForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const pin = $("#authPin").value;
  $("#authHint").textContent = "";
  try {
    const res = await api("/api/forense/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin }),
    });
    if (res.token) sessionStorage.setItem("forense.token", res.token);
    await checkSession();
  } catch (err) {
    $("#authHint").textContent = err.message;
  }
});

let pollTimer = null;
let currentJobId = null;

async function refreshJobs() {
  const data = await api("/api/forense/jobs");
  refreshReferenceSelect(data.jobs);
  const ul = $("#jobList");
  ul.innerHTML = "";
  for (const j of data.jobs || []) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    const label = j.status === "error" ? "error" : j.status;
    btn.textContent = `${j.title || j.id} · ${label} (${j.progress || 0}%)`;
    btn.classList.toggle("active", j.id === currentJobId);
    if (j.status === "error") btn.classList.add("job-error");
    btn.onclick = () => selectJob(j.id);
    li.appendChild(btn);
    ul.appendChild(li);
  }
}

function drawSpeedChart(series) {
  const canvas = $("#speedChart");
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#0b1220";
  ctx.fillRect(0, 0, w, h);

  if (!series?.length) {
    $("#chartsSection").classList.add("hidden");
    return;
  }
  $("#chartsSection").classList.remove("hidden");

  let maxT = 0;
  let maxK = 1;
  for (const s of series) {
    for (const p of s.points || []) {
      maxT = Math.max(maxT, p.t);
      maxK = Math.max(maxK, p.kmh);
    }
  }

  const pad = { l: 48, r: 16, t: 16, b: 32 };
  const plotW = w - pad.l - pad.r;
  const plotH = h - pad.t - pad.b;

  ctx.strokeStyle = "#243552";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad.l, pad.t);
  ctx.lineTo(pad.l, h - pad.b);
  ctx.lineTo(w - pad.r, h - pad.b);
  ctx.stroke();

  ctx.fillStyle = "#8fa3bf";
  ctx.font = "11px sans-serif";
  ctx.fillText("km/h", 8, pad.t + 12);
  ctx.fillText("0", pad.l - 8, h - pad.b + 4);
  ctx.fillText(String(Math.round(maxK)), pad.l - 16, pad.t + 4);
  ctx.fillText(String(maxT.toFixed(1)) + "s", w - pad.r - 24, h - pad.b + 16);

  const colors = ["#3d8bfd", "#3ecf8e", "#f0b429", "#f07178", "#b794f4"];
  const legend = [];
  series.slice(0, 5).forEach((s, idx) => {
    const color = colors[idx % colors.length];
    legend.push(`#${s.track_id} ${s.kind} (${s.max_kmh} km/h)`);
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    let started = false;
    for (const p of s.points || []) {
      const x = pad.l + (p.t / Math.max(maxT, 0.1)) * plotW;
      const y = h - pad.b - (p.kmh / maxK) * plotH;
      if (!started) {
        ctx.moveTo(x, y);
        started = true;
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();
  });
  $("#chartLegend").textContent = legend.join(" · ");
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
  const srcCount = j.sources?.length || j.analysis?.sources_count || 1;
  $("#jobMeta").textContent =
    `${j.site || ""} · ${j.template_name || j.template_id || ""} · ${j.status} · ` +
    `${j.analysis?.event_count || 0} eventos · ${srcCount} cámara(s)`;

  const pw = $("#progressWrap");
  if (j.status === "processing" || j.status === "queued") {
    pw.classList.remove("hidden");
    $("#progressBar").style.width = `${j.progress || 0}%`;
    $("#progressText").textContent = j.progress_message || "";
  } else if (j.status === "error") {
    pw.classList.remove("hidden");
    $("#progressBar").style.width = `${j.progress || 0}%`;
    $("#progressText").textContent = `Error: ${j.error || j.progress_message || "Análisis falló"}`;
    $("#progressText").style.color = "#f07178";
  } else {
    pw.classList.add("hidden");
    $("#progressText").style.color = "";
    if (j.status === "done" && pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  const compSec = $("#comparisonSection");
  const comp = j.comparison || {};
  if (comp.available) {
    compSec.classList.remove("hidden");
    $("#comparisonText").textContent =
      `Referencia: ${comp.reference_title} — ${comp.summary}. ${comp.interpretation}`;
  } else {
    compSec.classList.add("hidden");
  }

  const kin = j.analysis?.kinematics || {};
  const tbody = $("#kinematicsTable tbody");
  tbody.innerHTML = "";
  for (const row of kin.track_speeds || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>#${row.track_id}</td><td>${row.kind}</td><td>${row.max_kmh}</td><td>${row.avg_kmh}</td>`;
    tbody.appendChild(tr);
  }
  if (!tbody.children.length) {
    tbody.innerHTML = "<tr><td colspan='4' class='muted'>Sin tracks suficientes</td></tr>";
  }
  const viol = $("#kinViolations");
  viol.innerHTML = "";
  for (const v of [...(kin.speed_violations || []), ...(kin.proximity_events || [])]) {
    const li = document.createElement("li");
    li.textContent = v.message;
    viol.appendChild(li);
  }

  if (j.status === "done") {
    const charts = await api(`/api/forense/jobs/${id}/charts`);
    drawSpeedChart(charts.speed_series || []);
  } else {
    $("#chartsSection").classList.add("hidden");
  }

  const hmSec = $("#heatmapSection");
  if (j.has_heatmap) {
    hmSec.classList.remove("hidden");
    $("#heatmapImg").src = `/api/forense/jobs/${id}/heatmap.jpg?t=${Date.now()}`;
  } else {
    hmSec.classList.add("hidden");
  }

  const tl = $("#timeline");
  tl.innerHTML = "";
  for (const ev of j.analysis?.timeline || []) {
    const li = document.createElement("li");
    li.className = `sev-${ev.severity || "medium"}`;
    const cam = ev.camera ? ` [${ev.camera}]` : "";
    li.textContent = `${ev.time_label}${cam} · ${ev.type}: ${ev.message}`;
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

  const pdf = $("#downloadPdf");
  const committee = $("#downloadCommittee");
  const bundle = $("#downloadBundle");
  const ehsBtn = $("#exportEhs");

  if (j.status === "done") {
    const md = await api(`/api/forense/jobs/${id}/report.md`);
    $("#reportMd").textContent = md;
    const dl = $("#downloadMd");
    dl.href = `/api/forense/jobs/${id}/report.md`;
    dl.download = `forense-${id}.md`;
    if (j.has_pdf) {
      pdf.classList.remove("hidden");
      pdf.href = `/api/forense/jobs/${id}/report.pdf`;
      pdf.download = `forense-${id}.pdf`;
    } else {
      pdf.classList.add("hidden");
    }
    if (j.has_committee) {
      committee.classList.remove("hidden");
      committee.href = `/api/forense/jobs/${id}/committee.md`;
      committee.download = `forense-committee-${id}.md`;
    } else {
      committee.classList.add("hidden");
    }
    if (j.has_bundle) {
      bundle.classList.remove("hidden");
      bundle.href = `/api/forense/jobs/${id}/case_bundle.zip`;
      bundle.download = `forense-case-${id}.zip`;
    } else {
      bundle.classList.add("hidden");
    }
    ehsBtn.classList.remove("hidden");
    const ehs = j.ehs_push;
    $("#ehsStatus").textContent = ehs?.length
      ? `Último push EHS: ${ehs.map((r) => (r.ok ? "OK" : r.error || "error")).join(", ")}`
      : "";
  } else {
    if (!quiet) $("#reportMd").textContent = "Informe disponible al completar el análisis…";
    pdf.classList.add("hidden");
    committee.classList.add("hidden");
    bundle.classList.add("hidden");
    ehsBtn.classList.add("hidden");
  }
}

$("#exportEhs")?.addEventListener("click", async () => {
  if (!currentJobId) return;
  $("#ehsStatus").textContent = "Exportando…";
  try {
    const res = await api(`/api/forense/jobs/${currentJobId}/export-ehs`, { method: "POST" });
    const msg = (res.results || []).map((r) => (r.ok ? "OK" : r.error || "error")).join(", ");
    $("#ehsStatus").textContent = `EHS: ${msg || "sin respuesta"}`;
  } catch (err) {
    $("#ehsStatus").textContent = err.message;
  }
});

$("#uploadForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = $("#caseVideo").files?.[0];
  if (!file) {
    alert("Seleccioná un video principal (MP4 o MOV) antes de iniciar el análisis.");
    return;
  }
  const btn = $("#btnStartAnalysis");
  const hint = $("#uploadHint");
  const prevLabel = btn?.textContent || "Iniciar análisis";
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Subiendo video…";
  }
  if (hint) {
    hint.textContent = `Procesando «${file.name}» — puede tardar 1–3 min según duración.`;
    hint.classList.remove("hidden");
  }
  const fd = new FormData();
  fd.append("video", file);
  const v2 = $("#caseVideo2").files?.[0];
  const v3 = $("#caseVideo3").files?.[0];
  if (v2) fd.append("video2", v2);
  if (v3) fd.append("video3", v3);
  fd.append("title", $("#caseTitle").value);
  fd.append("site", $("#caseSite").value);
  fd.append("template_id", $("#caseTemplate").value);
  fd.append("meters_per_pixel", $("#caseMpp").value);
  fd.append("max_machinery_kmh", $("#caseMachKmh").value);
  fd.append("max_person_kmh", $("#casePersonKmh").value);
  fd.append("min_distance_m", $("#caseMinDist").value);
  fd.append("reference_job_id", $("#caseReference").value);
  fd.append("offset2", $("#caseOffset2").value);
  fd.append("offset3", $("#caseOffset3").value);
  try {
    const res = await api("/api/forense/jobs", { method: "POST", body: fd });
    if (hint) hint.textContent = "Análisis iniciado. Seguí el progreso en el panel central.";
    await refreshJobs();
    await selectJob(res.job.id);
  } catch (err) {
    if (hint) {
      hint.textContent = err.message;
      hint.style.color = "#f07178";
    }
    alert(err.message || "No se pudo iniciar el análisis");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = prevLabel;
    }
  }
});

captureBridgeToken();
checkSession();
