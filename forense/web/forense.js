import { statusLabel, kindLabel, eventTypeLabel, sourceLabel } from "./i18n-es-cl.js";

const API = "";
const TOKEN_KEY = "forense.token";
const SUPPORTED_VIDEO_EXT = [
  ".avi", ".mp4", ".m4v", ".mov", ".mkv", ".webm", ".ts", ".mts", ".m2ts",
  ".wmv", ".asf", ".flv", ".f4v", ".3gp", ".3g2", ".mpg", ".mpeg", ".mpe",
  ".dav", ".h264", ".264", ".ogv", ".ogg",
];

function isSupportedVideoFile(file) {
  if (!file?.name) return false;
  const dot = file.name.lastIndexOf(".");
  if (dot < 0) return (file.type || "").startsWith("video/");
  const ext = file.name.slice(dot).toLowerCase();
  return SUPPORTED_VIDEO_EXT.includes(ext);
}

function getForenseToken() {
  return sessionStorage.getItem(TOKEN_KEY) || "";
}

function setForenseToken(token) {
  if (token) sessionStorage.setItem(TOKEN_KEY, token);
  else sessionStorage.removeItem(TOKEN_KEY);
}

function clearForenseToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

function authHeaders(extra = {}) {
  const headers = { ...extra };
  const token = getForenseToken();
  if (token) headers["X-VigiEPP-Key"] = token;
  return headers;
}

function showToast(message, type = "info") {
  const host = $("#toastHost");
  if (!host || !message) return;
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = message;
  host.appendChild(el);
  requestAnimationFrame(() => el.classList.add("visible"));
  setTimeout(() => {
    el.classList.remove("visible");
    setTimeout(() => el.remove(), 280);
  }, type === "error" ? 5200 : 3600);
}

function showAuthGate(message = "") {
  authGate?.classList.remove("hidden");
  app?.classList.add("hidden");
  $("#sessionBadge")?.classList.add("hidden");
  $("#btnLogout")?.classList.add("hidden");
  if (message && $("#authHint")) $("#authHint").textContent = message;
}

function showAppShell() {
  authGate?.classList.add("hidden");
  app?.classList.remove("hidden");
  $("#sessionBadge")?.classList.remove("hidden");
  $("#btnLogout")?.classList.remove("hidden");
}

function updateSessionBadge(st) {
  const badge = $("#sessionBadge");
  if (!badge) return;
  const role = st?.role === "admin" ? "Administrador" : "Sesión activa";
  badge.textContent = role;
  badge.title = st?.auth_enabled === false ? "Autenticación desactivada (desarrollo)" : "Sesión Forense válida";
}

function hydrateTokenFromStatus(st) {
  if (st?.token) setForenseToken(st.token);
}

async function fetchAuthStatus() {
  const res = await fetch(`${API}/api/forense/auth/status`, {
    credentials: "include",
    headers: authHeaders(),
  });
  if (!res.ok) return { can_access: false };
  return res.json();
}

async function api(path, opts = {}, allowRetry = true) {
  const res = await fetch(`${API}${path}`, {
    credentials: "include",
    ...opts,
    headers: authHeaders(opts.headers || {}),
  });
  if (res.status === 401 && allowRetry) {
    clearForenseToken();
    const st = await fetchAuthStatus();
    hydrateTokenFromStatus(st);
    if (st.can_access) return api(path, opts, false);
    showAuthGate("Sesión expirada. Ingresá de nuevo con PIN administrador.");
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "No autorizado");
  }
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
    setForenseToken(key);
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
let situationTypesCache = {};
let teachClassesCache = [];
let selectedKeyframeName = null;
let pollTimer = null;
let currentJobId = null;
let frameCache = [];
let lastFrameFetchSec = -1;
let overlayRaf = null;
let videoSyncBound = false;
let videoBlobUrl = null;
let videoLoadedJobId = null;
let videoLoadingJobId = null;
let videoLoadPromise = null;
let videoLoadRetryAfter = 0;
let currentVideoCam = 0;
let showDismissedEvents = localStorage.getItem("forenseShowDismissed") !== "0";
const imageBlobUrls = new Map();

const INCIDENT_PRESETS = {
  general: {
    template: "general",
    focus: "cualquier riesgo visible: EPP, proximidad, velocidad, zonas, conducta, caídas",
    notes: "Incidente general — revisar secuencia completa del video.",
    strict: false,
  },
  proximity: {
    template: "portuario",
    focus: "persona cerca de maquinaria móvil, proximidad crítica, retroceso sin guía, velocidad",
    notes: "Proximidad persona–maquinaria o vehículo en movimiento.",
    strict: true,
  },
  epp: {
    template: "general",
    focus: "personal sin casco, chaleco reflectante, lentes, guantes o EPP incompleto",
    notes: "Incumplimiento o ausencia de elementos de protección personal.",
    strict: false,
  },
  fall: {
    template: "construccion",
    focus: "caída de persona, golpe, atrapamiento, postura insegura en altura o superficie",
    notes: "Caída, golpe contra objeto o atrapamiento.",
    strict: true,
  },
  machinery: {
    template: "portuario",
    focus: "maniobras de grúa, reach stacker, carga suspendida, línea de fuego",
    notes: "Maniobra de maquinaria pesada o carga suspendida.",
    strict: true,
  },
  zone: {
    template: "mineria",
    focus: "ingreso a zona restringida, señalética, delimitación, tránsito no autorizado",
    notes: "Ingreso o tránsito en zona restringida o no autorizada.",
    strict: false,
  },
  fire: {
    template: "incendio_emergencia",
    focus: "fuego, humo, respuesta de emergencia, EPP, evacuación del sector",
    notes: "Emergencia con fuego, humo o respuesta de brigada.",
    strict: false,
  },
};

function revokeImageBlobs(prefix = "") {
  for (const [key, url] of imageBlobUrls.entries()) {
    if (!prefix || key.startsWith(prefix)) {
      URL.revokeObjectURL(url);
      imageBlobUrls.delete(key);
    }
  }
}

async function loadAuthedImage(imgEl, url, blobKey = "") {
  if (!imgEl || !url) return;
  try {
    const res = await fetch(url, { credentials: "include", headers: authHeaders() });
    if (res.status === 401) {
      clearForenseToken();
      const st = await fetchAuthStatus();
      hydrateTokenFromStatus(st);
      if (!st.can_access) throw new Error("auth");
      return loadAuthedImage(imgEl, url, blobKey);
    }
    if (!res.ok) throw new Error(String(res.status));
    const blob = await res.blob();
    if (!blob.size) throw new Error("empty");
    if (blobKey) {
      const prev = imageBlobUrls.get(blobKey);
      if (prev) URL.revokeObjectURL(prev);
      const blobUrl = URL.createObjectURL(blob);
      imageBlobUrls.set(blobKey, blobUrl);
      imgEl.src = blobUrl;
    } else {
      imgEl.src = URL.createObjectURL(blob);
    }
    imgEl.classList.remove("kn-thumb-broken");
  } catch {
    imgEl.removeAttribute("src");
    imgEl.classList.add("kn-thumb-broken");
    imgEl.alt = "sin vista previa";
  }
}

function formatTs(sec) {
  const s = Math.max(0, Math.floor(sec));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
}

function seekVideoTo(timeSec, cameraLabel = null) {
  const video = $("#forenseVideo");
  const sec = $("#videoSection");
  if (!video || timeSec == null || Number.isNaN(Number(timeSec))) return;
  sec?.classList.remove("hidden");
  const doSeek = () => {
    video.currentTime = Math.max(0, Number(timeSec));
    video.play().catch(() => {});
    video.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };
  if (cameraLabel && currentJobId) {
    const cam = parseCameraIndex(cameraLabel);
    if (cam !== currentVideoCam) {
      void switchVideoCamera(currentJobId, cam, { quiet: true }).then(doSeek);
      return;
    }
  }
  doSeek();
}

function parseCameraIndex(cameraLabel) {
  if (!cameraLabel) return currentVideoCam;
  const m = String(cameraLabel).match(/(\d+)/);
  if (m) return Math.max(0, parseInt(m[1], 10) - 1);
  return currentVideoCam;
}

function applyIncidentPreset(presetId) {
  const preset = INCIDENT_PRESETS[presetId];
  if (!preset) return;
  const focus = $("#caseFocus");
  const notes = $("#caseNotes");
  const strict = $("#caseStrict");
  const tpl = $("#caseTemplate");
  if (focus) focus.value = preset.focus;
  if (notes && preset.notes) notes.value = preset.notes;
  if (strict) strict.checked = Boolean(preset.strict);
  if (tpl && preset.template) {
    tpl.value = preset.template;
    applyTemplateDefaults(preset.template);
  }
  showToast(`Escenario: ${presetId}`, "info");
}

function renderCriticalAlerts(job, jobId) {
  const sec = $("#criticalAlertsSection");
  const grid = $("#criticalAlerts");
  if (!sec || !grid) return;
  const alerts = job.critical_alerts || [];
  grid.innerHTML = "";
  if (!alerts.length || job.status !== "done") {
    sec.classList.add("hidden");
    return;
  }
  sec.classList.remove("hidden");
  for (const a of alerts) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `alert-card sev-${a.severity || "high"}`;
    const timeTxt = a.time_label ? `${a.time_label}` : "IA visual / global";
    btn.innerHTML = `<strong>${a.label}</strong><span class="alert-time">${timeTxt}</span><p class="muted small">${a.message || ""}</p>`;
    btn.onclick = () => {
      if (a.time_sec != null) seekVideoTo(a.time_sec, a.camera);
      else if (a.evidence_image) highlightKeyframe(jobId, a.evidence_image);
    };
    grid.appendChild(btn);
  }
}

function highlightKeyframe(jobId, imageName) {
  const buttons = document.querySelectorAll("#keyframes .keyframe-btn");
  for (const b of buttons) {
    const img = b.querySelector("img");
    if (img?.alt && imageName) {
      b.classList.toggle("selected", b.dataset.image === imageName);
    }
  }
  const match = document.querySelector(`#keyframes .keyframe-btn[data-image="${imageName}"]`);
  match?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  match?.focus();
}

function nearestCachedFrame(timeSec) {
  if (!frameCache.length) return null;
  let best = frameCache[0];
  let bestDt = Math.abs((best.time_sec || 0) - timeSec);
  for (const fr of frameCache) {
    const dt = Math.abs((fr.time_sec || 0) - timeSec);
    if (dt < bestDt) {
      bestDt = dt;
      best = fr;
    }
  }
  return bestDt <= 1.5 ? best : null;
}

function resizeOverlayCanvas() {
  const video = $("#forenseVideo");
  const canvas = $("#forenseOverlay");
  if (!video || !canvas || !video.videoWidth) return;
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
}

function drawFrameOverlay(frameRec) {
  const video = $("#forenseVideo");
  const canvas = $("#forenseOverlay");
  if (!video || !canvas || !frameRec) return;
  resizeOverlayCanvas();
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const fw = frameRec.frame_w || canvas.width;
  const fh = frameRec.frame_h || canvas.height;
  const sx = canvas.width / fw;
  const sy = canvas.height / fh;

  for (const det of frameRec.detections || []) {
    const [x1, y1, x2, y2] = det.box || [];
    if (x1 == null) continue;
    const kind = det.kind || "other";
    ctx.strokeStyle = kind === "person" ? "#3ecf8e" : kind === "machinery" ? "#f0b429" : "#8fa3bf";
    ctx.lineWidth = 2;
    ctx.strokeRect(x1 * sx, y1 * sy, (x2 - x1) * sx, (y2 - y1) * sy);
    const label = `${det.label || kind} ${Math.round((det.confidence || 0) * 100)}%`;
    ctx.font = "12px system-ui,sans-serif";
    const tw = ctx.measureText(label).width + 8;
    ctx.fillStyle = ctx.strokeStyle;
    ctx.fillRect(x1 * sx, Math.max(0, y1 * sy - 18), tw, 16);
    ctx.fillStyle = "#0b1220";
    ctx.fillText(label, x1 * sx + 4, Math.max(12, y1 * sy - 5));
  }

  const speedByTrack = new Map((frameRec.speeds || []).map((s) => [s.track_id, s]));
  for (const tr of frameRec.tracks || []) {
    const sp = speedByTrack.get(tr.track_id);
    if (!sp) continue;
    const cx = (tr.cx || 0) * sx;
    const cy = (tr.cy || 0) * sy;
    ctx.fillStyle = tr.kind === "machinery" ? "#f0b429" : "#3ecf8e";
    ctx.font = "bold 11px system-ui,sans-serif";
    ctx.fillText(`${sp.speed_kmh} km/h`, cx + 6, cy - 8);
  }

  for (const prox of frameRec.proximity || []) {
    const pTr = (frameRec.tracks || []).find((t) => t.track_id === prox.person_track);
    const mTr = (frameRec.tracks || []).find((t) => t.track_id === prox.machinery_track);
    if (!pTr || !mTr) continue;
    const px = pTr.cx * sx;
    const py = pTr.cy * sy;
    const mx = mTr.cx * sx;
    const my = mTr.cy * sy;
    ctx.strokeStyle = prox.alert ? "#f07178" : "#8fa3bf";
    ctx.setLineDash(prox.alert ? [] : [4, 4]);
    ctx.lineWidth = prox.alert ? 2 : 1;
    ctx.beginPath();
    ctx.moveTo(px, py);
    ctx.lineTo(mx, my);
    ctx.stroke();
    ctx.setLineDash([]);
    const midX = (px + mx) / 2;
    const midY = (py + my) / 2;
    ctx.fillStyle = prox.alert ? "#f07178" : "#8fa3bf";
    ctx.font = "10px system-ui,sans-serif";
    ctx.fillText(`${prox.distance_m} m`, midX + 4, midY - 4);
  }
}

function updateLiveStats(frameRec, totalStored) {
  const timeEl = $("#liveTime");
  const countsEl = $("#liveCounts");
  const speedsEl = $("#liveSpeeds");
  const proxEl = $("#liveProximity");
  const framesEl = $("#liveFrames");
  if (!frameRec) {
    if (timeEl) timeEl.textContent = "—";
    if (countsEl) countsEl.textContent = "Esperando análisis…";
    if (speedsEl) speedsEl.textContent = "";
    if (proxEl) proxEl.textContent = "";
    if (framesEl) framesEl.textContent = totalStored ? `${totalStored} fotogramas` : "";
    return;
  }
  if (timeEl) timeEl.textContent = frameRec.time_label || formatTs(frameRec.time_sec || 0);
  const c = frameRec.counts || {};
  if (countsEl) {
    countsEl.textContent = `👤 ${c.persons || 0} · 🚛 ${c.vehicles || 0} objetos`;
  }
  const speeds = (frameRec.speeds || []).map((s) => `#${s.track_id} ${s.speed_kmh} km/h`).join(" · ");
  if (speedsEl) speedsEl.textContent = speeds ? `Vel.: ${speeds}` : "Vel.: —";
  const prox = frameRec.proximity || [];
  const closest = prox[0];
  if (proxEl) {
    if (!closest) {
      proxEl.textContent = "Dist.: —";
      proxEl.classList.remove("alert");
    } else {
      proxEl.textContent = `Dist. mín.: ${closest.distance_m} m (persona #${closest.person_track} – máq. #${closest.machinery_track})`;
      proxEl.classList.toggle("alert", !!closest.alert);
    }
  }
  if (framesEl) framesEl.textContent = `${totalStored || frameCache.length} fotogramas analizados`;
}

function onVideoTimeUpdate() {
  const video = $("#forenseVideo");
  if (!video) return;
  const t = video.currentTime || 0;
  const fr = nearestCachedFrame(t);
  drawFrameOverlay(fr);
  updateLiveStats(fr, frameCache.length);
}

function bindVideoSync() {
  if (videoSyncBound) return;
  const video = $("#forenseVideo");
  if (!video) return;
  videoSyncBound = true;
  video.addEventListener("loadedmetadata", resizeOverlayCanvas);
  video.addEventListener("timeupdate", onVideoTimeUpdate);
  video.addEventListener("seeked", onVideoTimeUpdate);
  video.addEventListener("play", () => {
    const tick = () => {
      if (!video.paused) {
        onVideoTimeUpdate();
        overlayRaf = requestAnimationFrame(tick);
      }
    };
    overlayRaf = requestAnimationFrame(tick);
  });
  video.addEventListener("pause", () => {
    if (overlayRaf) cancelAnimationFrame(overlayRaf);
    onVideoTimeUpdate();
  });
  video.addEventListener("error", () => {
    const code = video.error?.code;
    if (code === 4) {
      showToast("Formato de video no soportado en este navegador. Reintentá recargar el caso.", "error");
    } else if (code) {
      showToast("No se pudo reproducir el video en el navegador.", "error");
    }
  });
}

async function fetchIncrementalFrames(jobId) {
  const fromSec = Math.max(0, lastFrameFetchSec);
  try {
    const data = await api(
      `/api/forense/jobs/${jobId}/analysis/frames?from_sec=${fromSec.toFixed(2)}&limit=400`,
    );
    const frames = data.frames || [];
    if (frames.length) {
      const seen = new Set(frameCache.map((f) => f.time_sec));
      for (const fr of frames) {
        if (!seen.has(fr.time_sec)) {
          frameCache.push(fr);
          seen.add(fr.time_sec);
        }
      }
      frameCache.sort((a, b) => (a.time_sec || 0) - (b.time_sec || 0));
      lastFrameFetchSec = frameCache[frameCache.length - 1].time_sec || fromSec;
    }
    const total = data.total_stored ?? frameCache.length;
    const video = $("#forenseVideo");
    if (video && !video.paused) onVideoTimeUpdate();
    else updateLiveStats(nearestCachedFrame(video?.currentTime || 0), total);
    return total;
  } catch {
    return frameCache.length;
  }
}

function releaseVideoBlob() {
  if (videoBlobUrl) {
    URL.revokeObjectURL(videoBlobUrl);
    videoBlobUrl = null;
  }
}

function resetVideoViewerState() {
  releaseVideoBlob();
  videoLoadedJobId = null;
  videoLoadingJobId = null;
  videoLoadPromise = null;
  videoLoadRetryAfter = 0;
  const video = $("#forenseVideo");
  if (video) {
    video.removeAttribute("src");
    video.removeAttribute("data-src");
    video.removeAttribute("data-job-id");
  }
}

async function loadJobVideo(jobId, { quiet = false, cam = currentVideoCam } = {}) {
  const video = $("#forenseVideo");
  if (!video) return;
  const path = `/api/forense/jobs/${jobId}/video?cam=${cam}`;
  const loadKey = `${jobId}:${cam}`;

  if (videoLoadedJobId === loadKey && video.src && video.getAttribute("data-src") === path) return;
  if (videoLoadingJobId === loadKey && videoLoadPromise) return videoLoadPromise;
  if (Date.now() < videoLoadRetryAfter) return;

  videoLoadingJobId = loadKey;
  video.setAttribute("data-src", path);
  video.setAttribute("data-job-id", jobId);
  video.setAttribute("data-cam", String(cam));

  if (!quiet) {
    showToast("Preparando video para reproducción (puede tardar si requiere conversión)…", "info");
  }

  videoLoadPromise = (async () => {
    try {
      const res = await fetch(path, { credentials: "include", headers: authHeaders() });
      if (res.status === 401) {
        clearForenseToken();
        const st = await fetchAuthStatus();
        hydrateTokenFromStatus(st);
        if (!st.can_access) throw new Error("Sesión expirada");
        videoLoadingJobId = null;
        videoLoadPromise = null;
        return loadJobVideo(jobId, { quiet, cam });
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        if (res.status === 404) {
          videoLoadRetryAfter = Date.now() + 8000;
          return;
        }
        throw new Error(err.detail || "No se pudo cargar el video");
      }
      const blob = await res.blob();
      if (!blob.size) throw new Error("El video está vacío o no se pudo convertir");
      if (videoLoadingJobId !== loadKey) return;
      releaseVideoBlob();
      videoBlobUrl = URL.createObjectURL(blob);
      video.src = videoBlobUrl;
      videoLoadedJobId = loadKey;
      currentVideoCam = cam;
      await video.play().catch(() => {});
      video.pause();
      video.currentTime = 0;
    } catch (err) {
      if (!quiet) showToast(err.message || "Error al cargar el video", "error");
      video.removeAttribute("data-src");
      videoLoadRetryAfter = Date.now() + 5000;
    } finally {
      if (videoLoadingJobId === loadKey) {
        videoLoadingJobId = null;
        videoLoadPromise = null;
      }
    }
  })();

  return videoLoadPromise;
}

async function switchVideoCamera(jobId, cam, { quiet = false } = {}) {
  if (cam === currentVideoCam && videoLoadedJobId === `${jobId}:${cam}`) return;
  currentVideoCam = cam;
  videoLoadedJobId = null;
  await loadJobVideo(jobId, { quiet, cam });
}

function renderVideoCameraSelector(job, jobId) {
  const row = $("#videoCamRow");
  const sel = $("#videoCamSelect");
  if (!row || !sel) return;
  const cams = job.video_cameras || [];
  if (cams.length <= 1) {
    row.classList.add("hidden");
    currentVideoCam = 0;
    return;
  }
  row.classList.remove("hidden");
  sel.innerHTML = "";
  for (const c of cams) {
    const opt = document.createElement("option");
    opt.value = String(c.index);
    opt.textContent = c.label || `Cám. ${c.index + 1}`;
    sel.appendChild(opt);
  }
  if (!sel.dataset.bound) {
    sel.dataset.bound = "1";
    sel.addEventListener("change", () => {
      if (!currentJobId) return;
      void switchVideoCamera(currentJobId, parseInt(sel.value, 10) || 0);
    });
  }
  sel.value = String(currentVideoCam);
  if (!cams.some((c) => c.index === currentVideoCam)) {
    currentVideoCam = cams[0]?.index ?? 0;
    sel.value = String(currentVideoCam);
  }
}

function setupVideoViewer(job, jobId, { isPoll = false } = {}) {
  const section = $("#videoSection");
  const video = $("#forenseVideo");
  if (!section || !video) return;
  if (!job.has_video) {
    section.classList.add("hidden");
    resetVideoViewerState();
    frameCache = [];
    lastFrameFetchSec = -1;
    return;
  }
  section.classList.remove("hidden");
  renderVideoCameraSelector(job, jobId);
  const sameJob = video.getAttribute("data-job-id") === jobId;
  if (!sameJob) {
    resetVideoViewerState();
    currentVideoCam = 0;
    frameCache = [];
    lastFrameFetchSec = -1;
    video.setAttribute("data-job-id", jobId);
  }
  bindVideoSync();

  const processing = job.status === "processing" || job.status === "queued";
  const loadKey = `${jobId}:${currentVideoCam}`;
  const shouldLoad =
    !isPoll ||
    (!processing && videoLoadedJobId !== loadKey && videoLoadingJobId !== loadKey);
  if (shouldLoad && (!video.src || videoLoadedJobId !== loadKey)) {
    void loadJobVideo(jobId, { quiet: processing || isPoll, cam: currentVideoCam });
  }
  if (!isPoll || !sameJob) fetchIncrementalFrames(jobId);
}

$("#btnLearnMoment")?.addEventListener("click", async () => {
  if (!currentJobId) return;
  const video = $("#forenseVideo");
  const timeSec = video?.currentTime || 0;
  const timeLabel = formatTs(timeSec);
  const title = prompt("Título de la situación:", `Evento en ${timeLabel}`);
  if (!title) return;
  const description = prompt("¿Qué ocurrió en este instante?", "") || "";
  const situationType = $("#knSituationType")?.value || "other";
  const industry = $("#knIndustry")?.value || "general";
  try {
    await api(`/api/forense/jobs/${currentJobId}/events/learn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        time_sec: timeSec,
        title,
        description,
        situation_type: situationType,
        industry,
      }),
    });
    await loadKnowledge();
    alert("Momento guardado en la biblioteca de aprendizaje.");
  } catch (err) {
    alert(err.message);
  }
});

function applyTemplateDefaults(templateId) {
  const tpl = templatesCache.find((t) => t.id === templateId) || templatesCache.find((t) => t.id === "general");
  if (!tpl) return;
  $("#caseMpp").value = tpl.meters_per_pixel;
  $("#caseMachKmh").value = tpl.max_machinery_kmh;
  $("#casePersonKmh").value = tpl.max_person_kmh;
  $("#caseMinDist").value = tpl.min_distance_m;
  const focus = (tpl.situation_focus || []).join(", ");
  $("#templateHint").textContent = tpl.intro
    ? `${tpl.intro}${focus ? ` · Foco: ${focus}` : ""}`
    : `Perfil: ${tpl.profile}`;
}

async function loadTemplates() {
  const data = await api("/api/forense/templates");
  templatesCache = data.templates || [];
  const sel = $("#caseTemplate");
  const knIndustry = $("#knIndustry");
  sel.innerHTML = "";
  knIndustry.innerHTML = "";
  for (const t of templatesCache) {
    const opt = document.createElement("option");
    opt.value = t.id;
    opt.textContent = t.name;
    sel.appendChild(opt);
    const opt2 = document.createElement("option");
    opt2.value = t.id;
    opt2.textContent = t.name;
    knIndustry.appendChild(opt2);
  }
  sel.onchange = () => applyTemplateDefaults(sel.value);
  applyTemplateDefaults(sel.value || "general");
}

function clearUploadForm() {
  $("#uploadForm")?.reset();
  const title = $("#caseTitle");
  const notes = $("#caseNotes");
  const site = $("#caseSite");
  if (title) title.value = "";
  if (notes) notes.value = "";
  if (site) site.value = "";
  const focus = $("#caseFocus");
  if (focus) focus.value = "";
  const ff = $("#caseFocusFrom");
  const fu = $("#caseFocusUntil");
  if (ff) ff.value = "";
  if (fu) fu.value = "";
  const strict = $("#caseStrict");
  if (strict) strict.checked = false;
  const tpl = $("#caseTemplate");
  if (tpl) tpl.value = "general";
  applyTemplateDefaults("general");
  const ref = $("#caseReference");
  if (ref) ref.value = "";
  const off2 = $("#caseOffset2");
  const off3 = $("#caseOffset3");
  if (off2) off2.value = "0";
  if (off3) off3.value = "0";
  for (const id of ["caseVideo", "caseVideo2", "caseVideo3"]) {
    const el = document.getElementById(id);
    if (el) el.value = "";
  }
  const hint = $("#uploadHint");
  if (hint) {
    hint.textContent = "";
    hint.style.color = "";
    hint.classList.add("hidden");
  }
}

function resetNewCaseForm() {
  clearUploadForm();
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  currentJobId = null;
  frameCache = [];
  lastFrameFetchSec = -1;
  resetVideoViewerState();
  revokeImageBlobs();
  $("#jobView")?.classList.add("hidden");
  $("#emptyState")?.classList.remove("hidden");
  refreshJobs();
}

function refreshReferenceSelect(jobs) {
  const sel = $("#caseReference");
  const current = sel.value;
  sel.innerHTML = '<option value="">— Sin referencia —</option>';
  for (const j of jobs || []) {
    if (j.status !== "done") continue;
    const opt = document.createElement("option");
    opt.value = j.id;
    opt.textContent = `${j.title || j.id} (${j.event_count || 0} eventos)`;
    sel.appendChild(opt);
  }
  if (current) sel.value = current;
}

async function loadTeachStatus() {
  try {
    const data = await api("/api/forense/teach/status");
    teachClassesCache = data.teach_classes || [];
    const pick = $("#teachClassPick");
    if (pick) {
      pick.innerHTML = "";
      for (const c of teachClassesCache) {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = c.name || c.id;
        pick.appendChild(opt);
      }
    }
    const modelLine = data.custom_active
      ? `✓ ${data.model_name}`
      : data.custom_weights_exist
        ? `Pesos listos — activar modelo personalizado`
        : `Modelo base (genérico)`;
    $("#teachModelLine").textContent = modelLine;
    $("#teachSamplesLine").textContent = `${data.total_samples || 0} fotos · ${
      data.ready_to_train ? "listo para entrenar" : `mín. ${data.min_recommended || 30} recomendadas`
    }`;
    const btnAct = $("#btnTeachActivate");
    const btnTrain = $("#btnTeachTrain");
    if (btnAct) btnAct.disabled = !data.custom_weights_exist && !data.custom_model_ready;
    if (btnTrain) btnTrain.disabled = !data.ready_to_train || data.training_running;
    if (data.training_running) {
      $("#teachHint").textContent = "Entrenamiento en curso…";
    } else if (data.custom_active) {
      $("#teachHint").textContent = "Forense analiza con el modelo entrenado de tu faena.";
    }
    const link = $("#teachOpenVigi");
    if (link && data.vigiepp_teach_url) link.href = data.vigiepp_teach_url;
  } catch {
  /* Teach opcional si backend compartido no está */
  }
}

let sourcesCatalogCache = [];

async function loadSourcesCatalog() {
  try {
    const data = await api("/api/forense/knowledge/sources/catalog");
    sourcesCatalogCache = data.sources || [];
    const line = $("#sourcesCatalogLine");
    if (line) {
      line.textContent = `${sourcesCatalogCache.length} fuentes · DOL API: ${data.dol_api_configured ? "configurada" : "no configurada"}`;
    }
    renderSourceButtons();
  } catch {
    $("#sourcesCatalogLine").textContent = "Catálogo de fuentes no disponible";
  }
}

function renderSourceButtons() {
  const wrap = $("#sourceButtons");
  const industry = $("#sourceIndustry")?.value || "general";
  if (!wrap) return;
  wrap.innerHTML = "";
  const filtered = sourcesCatalogCache.filter((s) => (s.industry || "general") === industry);
  for (const src of filtered) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn secondary small";
    btn.title = src.description || "";
    btn.textContent = src.name;
    btn.onclick = () => syncKnowledgeSource(src.id, src.name, btn);
    wrap.appendChild(btn);
  }
  if (!filtered.length) {
    wrap.innerHTML = '<span class="muted small">Sin fuentes para esta industria</span>';
  }
}

async function syncKnowledgeSource(sourceId, label, btn) {
  const hint = $("#sourcesHint");
  hint.textContent = `Sincronizando ${label}…`;
  if (btn) btn.disabled = true;
  try {
    const res = await api("/api/forense/knowledge/sources/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_id: sourceId, skip_existing: true }),
    });
    const msg = `${label}: ${res.imported ?? 0} nuevas, ${res.skipped ?? 0} ya existían.`;
    hint.textContent = msg;
    showToast(msg, "ok");
    await loadKnowledge();
  } catch (err) {
    hint.textContent = err.message;
    showToast(err.message, "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

$("#sourceIndustry")?.addEventListener("change", renderSourceButtons);

$("#btnSyncIndustry")?.addEventListener("click", async () => {
  const industry = $("#sourceIndustry")?.value || "general";
  const hint = $("#sourcesHint");
  const btn = $("#btnSyncIndustry");
  hint.textContent = `Sincronizando industria ${industry}…`;
  if (btn) btn.disabled = true;
  try {
    const res = await api("/api/forense/knowledge/sources/sync-industry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ industry, limit_per_source: 12, skip_existing: true }),
    });
    const msg = `Industria ${industry}: ${res.total_imported ?? 0} situaciones importadas en total.`;
    hint.textContent = msg;
    showToast(msg, "ok");
    await loadKnowledge();
  } catch (err) {
    hint.textContent = err.message;
    showToast(err.message, "error");
  } finally {
    if (btn) btn.disabled = false;
  }
});

$("#btnIngestUrl")?.addEventListener("click", async () => {
  const url = $("#sourceUrl")?.value?.trim();
  if (!url) {
    alert("Ingresá una URL de informe oficial.");
    return;
  }
  const hint = $("#sourcesHint");
  hint.textContent = "Descargando e importando URL…";
  try {
    const res = await api("/api/forense/knowledge/sources/ingest-url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        title: $("#sourceUrlTitle")?.value || "",
        industry: $("#sourceIndustry")?.value || "general",
        save: true,
      }),
    });
    hint.textContent = res.saved
      ? `Importado: ${res.entry?.title || "informe"}`
      : "Vista previa generada (no guardado).";
    await loadKnowledge();
  } catch (err) {
    hint.textContent = err.message;
  }
});

async function loadKnowledge() {
  const data = await api("/api/forense/knowledge");
  situationTypesCache = data.situation_types || {};
  const typeSel = $("#knSituationType");
  if (typeSel && !typeSel.options.length) {
    typeSel.innerHTML = "";
    for (const [id, label] of Object.entries(situationTypesCache)) {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = label;
      typeSel.appendChild(opt);
    }
  }
  const stats = data.stats || {};
  const srcParts = stats.by_source
    ? Object.entries(stats.by_source).map(([k, v]) => `${k}: ${v}`).join(" · ")
    : "";
  $("#knowledgeStats").textContent = `${stats.total || 0} situación(es)${srcParts ? ` (${srcParts})` : ""}`;
  const ul = $("#knowledgeList");
  ul.innerHTML = "";
  for (const e of data.entries || []) {
    const li = document.createElement("li");
    li.className = "knowledge-item";
    const thumbWrap = document.createElement("div");
    thumbWrap.className = "kn-thumb-wrap";
    if (e.has_thumb) {
      const img = document.createElement("img");
      img.alt = "";
      img.className = "kn-thumb";
      img.loading = "lazy";
      loadKnowledgeThumb(e.id, img);
      thumbWrap.appendChild(img);
    } else {
      thumbWrap.innerHTML = '<span class="kn-thumb placeholder">📷</span>';
    }
    const body = document.createElement("div");
    body.className = "kn-body";
    const src = e.source && e.source !== "user"
      ? `<span class="kn-source-badge">${sourceLabel(e.source) || e.source}</span>`
      : "";
    body.innerHTML = `
        <strong>${e.title}${src}</strong>
        <span class="muted small">${e.situation_label || e.situation_type} · ${e.industry}${e.reinforce_count ? ` · ×${e.reinforce_count}` : ""}</span>
        <p class="small">${e.description || ""}</p>
      `;
    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "btn ghost small";
    delBtn.textContent = "✕";
    delBtn.onclick = async () => {
      if (!confirm(`¿Eliminar «${e.title}» de la biblioteca?`)) return;
      await api(`/api/forense/knowledge/${e.id}`, { method: "DELETE" });
      await loadKnowledge();
    };
    li.appendChild(thumbWrap);
    li.appendChild(body);
    li.appendChild(delBtn);
    ul.appendChild(li);
  }
}

async function loadKnowledgeThumb(entryId, imgEl) {
  await loadAuthedImage(imgEl, `/api/forense/knowledge/${entryId}/thumb.jpg`, `kn:${entryId}`);
}

function updateVigiEppLink() {
  const a = $("#lnkVigiEpp");
  if (!a) return;
  a.href = `${window.location.protocol}//${window.location.hostname}:8000/`;
}

async function checkSession() {
  captureBridgeToken();
  updateVigiEppLink();
  try {
    const h = await api("/api/forense/health");
    $("#licenseLine").textContent = h.license?.valid
      ? `Licencia activa · ${h.build} · IA + aprendizaje`
      : `Sin licencia: ${h.license?.detail || "—"}`;
    const st = await fetchAuthStatus();
    hydrateTokenFromStatus(st);
    if (st.can_access) {
      showAppShell();
      updateSessionBadge(st);
      await loadTemplates();
      await loadTeachStatus();
      await loadKnowledge();
      await loadSuppressionRules();
      await loadSourcesCatalog();
      await refreshJobs();
      return;
    }
  } catch {
    /* mostrar gate */
  }
  showAuthGate();
}

$("#btnLogout")?.addEventListener("click", async () => {
  try {
    await api("/api/forense/auth/logout", { method: "POST" });
  } catch {
    /* ignorar */
  }
  clearForenseToken();
  showAuthGate();
  if ($("#authHint")) $("#authHint").textContent = "Sesión cerrada.";
});

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
    if (res.token) setForenseToken(res.token);
    await checkSession();
    showToast("Sesión Forense iniciada", "ok");
  } catch (err) {
    $("#authHint").textContent = err.message;
  }
});

$("#btnNewCase")?.addEventListener("click", resetNewCaseForm);
$("#btnResetForm")?.addEventListener("click", () => {
  clearUploadForm();
  showToast("Formulario limpiado", "info");
});

$("#btnTeachActivate")?.addEventListener("click", async () => {
  $("#teachHint").textContent = "Activando modelo…";
  try {
    const res = await api("/api/forense/teach/activate", { method: "POST" });
    $("#teachHint").textContent = res.message || "Modelo activado.";
    await loadTeachStatus();
  } catch (err) {
    $("#teachHint").textContent = err.message;
  }
});

$("#btnTeachTrain")?.addEventListener("click", async () => {
  if (!confirm("¿Iniciar entrenamiento YOLO con las fotos de Teach? Puede tardar varios minutos.")) return;
  $("#teachHint").textContent = "Iniciando entrenamiento…";
  try {
    const res = await api("/api/forense/teach/train", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ epochs: 40 }),
    });
    $("#teachHint").textContent = res.message || "Entrenamiento iniciado.";
    await loadTeachStatus();
  } catch (err) {
    $("#teachHint").textContent = err.message;
  }
});

$("#btnKeyframeTeach")?.addEventListener("click", async () => {
  if (!currentJobId || !selectedKeyframeName) {
    alert("Seleccioná una captura clave primero (clic en la imagen).");
    return;
  }
  const classId = $("#teachClassPick")?.value;
  if (!classId) {
    alert("Elegí una clase de enseñanza.");
    return;
  }
  try {
    const res = await api(`/api/forense/jobs/${currentJobId}/teach`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keyframe_name: selectedKeyframeName, class_id: classId }),
    });
    $("#teachHint").textContent = res.message || "Captura enviada a enseñanza.";
    await loadTeachStatus();
  } catch (err) {
    alert(err.message);
  }
});

$("#btnResetKnowledge")?.addEventListener("click", async () => {
  const confirm = prompt("Esto borra TODA la biblioteca de aprendizaje. Escribí RESETEAR para confirmar:");
  if (confirm?.trim().toUpperCase() !== "RESETEAR") return;
  try {
    const res = await api("/api/forense/knowledge/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirm: "RESETEAR" }),
    });
    $("#knowledgeHint").textContent = `Biblioteca reseteada (${res.removed} entradas eliminadas).`;
    await loadKnowledge();
  } catch (err) {
    alert(err.message);
  }
});

async function runKnowledgeImport(endpoint, body, label) {
  const hint = $("#importHint");
  hint.textContent = `Importando ${label}…`;
  try {
    const res = await api(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    hint.textContent =
      `${label}: ${res.imported} nuevas, ${res.skipped || 0} ya existían` +
      (res.fetched ? ` (consultadas ${res.fetched} en OSHA)` : "") +
      (res.candidates ? ` de ${res.candidates} candidatas` : "") +
      ".";
    await loadKnowledge();
  } catch (err) {
    hint.textContent = err.message;
  }
}

$("#btnImportSeeds")?.addEventListener("click", () =>
  runKnowledgeImport("/api/forense/knowledge/import/seeds", { skip_existing: true }, "Plantillas")
);

$("#btnImportOshaPort")?.addEventListener("click", () =>
  runKnowledgeImport(
    "/api/forense/knowledge/import/osha",
    {
      keywords: ["CRANE", "HOIST", "MARITIME", "DOCK", "STEVEDORE"],
      default_industry: "portuario",
      limit_per_keyword: 8,
      skip_existing: true,
    },
    "OSHA portuario"
  )
);

$("#btnImportOshaBodega")?.addEventListener("click", () =>
  runKnowledgeImport(
    "/api/forense/knowledge/import/osha",
    {
      keywords: ["FORKLIFT", "PALLET", "WAREHOUSE"],
      default_industry: "bodega",
      limit_per_keyword: 8,
      skip_existing: true,
    },
    "OSHA bodega"
  )
);

$("#btnImportOshaAll")?.addEventListener("click", () =>
  runKnowledgeImport(
    "/api/forense/knowledge/import/osha",
    {
      keywords: ["CRANE", "FORKLIFT", "FALL", "SCAFFOLD", "HELMET", "MARITIME"],
      default_industry: "general",
      limit_per_keyword: 6,
      skip_existing: true,
    },
    "OSHA completo"
  )
);

$("#knowledgeForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  $("#knowledgeHint").textContent = "Guardando…";
  const fd = new FormData();
  fd.append("title", $("#knTitle").value);
  fd.append("situation_type", $("#knSituationType").value);
  fd.append("industry", $("#knIndustry").value);
  fd.append("description", $("#knDescription").value);
  const media = $("#knMedia").files?.[0];
  if (media) fd.append("media", media);
  try {
    await api("/api/forense/knowledge", { method: "POST", body: fd });
    $("#knowledgeForm").reset();
    $("#knowledgeHint").textContent = "Situación agregada. Se usará en futuros análisis.";
    await loadKnowledge();
  } catch (err) {
    $("#knowledgeHint").textContent = err.message;
  }
});

async function refreshJobs() {
  const data = await api("/api/forense/jobs");
  refreshReferenceSelect(data.jobs);
  const ul = $("#jobList");
  ul.innerHTML = "";
  for (const j of data.jobs || []) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    const label = j.status === "error" ? "error" : statusLabel(j.status);
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
    legend.push(`#${s.track_id} ${kindLabel(s.kind)} (${s.max_kmh} km/h)`);
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

async function reviewTimelineEvent(jobId, eventId, verdict) {
  let note = "";
  if (verdict === "dismissed") {
    if (
      !confirm(
        "¿Marcar como falso positivo? No contará en el informe y el sistema aprenderá para futuros casos.",
      )
    ) {
      return;
    }
    note = prompt("Nota opcional (motivo del descarte):", "") || "";
  } else if (verdict === "confirmed") {
    note = prompt("Nota opcional (confirmación):", "") || "";
  }
  try {
    await api(`/api/forense/jobs/${jobId}/events/${eventId}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ verdict, note }),
    });
    const msg =
      verdict === "dismissed"
        ? "Evento descartado como falso positivo"
        : verdict === "restored"
          ? "Evento restaurado"
          : "Evento confirmado";
    showToast(msg, "ok");
    await loadJob(jobId, true);
    await loadSuppressionRules();
  } catch (err) {
    showToast(err.message || "Error al revisar evento", "error");
  }
}

async function loadSuppressionRules() {
  const stats = $("#suppressionStats");
  const list = $("#suppressionList");
  if (!stats || !list) return;
  try {
    const data = await api("/api/forense/suppression-rules");
    const rules = data.rules || [];
    stats.textContent = `${data.count || rules.length} regla(s) activa(s) en esta faena`;
    list.innerHTML = "";
    if (!rules.length) {
      list.innerHTML = "<li class='muted small'>Sin reglas — descartá un falso positivo para que el sistema aprenda.</li>";
      return;
    }
    for (const r of rules) {
      const li = document.createElement("li");
      const type = r.type || "—";
      const rid = r.rule_id || "";
      const msg = (r.last_message || "").slice(0, 80);
      li.innerHTML = `<div><strong>${type}</strong>${rid ? ` · ${rid}` : ""}<div class="supp-meta">×${r.dismissed_count || 1}${msg ? ` — ${msg}` : ""}</div></div>`;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn ghost small";
      btn.textContent = "Quitar";
      btn.onclick = async () => {
        if (!confirm("¿Eliminar esta regla de supresión? Volverán a detectarse eventos de este tipo.")) return;
        const q = new URLSearchParams({ type, rule_id: rid });
        await api(`/api/forense/suppression-rules?${q}`, { method: "DELETE" });
        showToast("Regla eliminada", "ok");
        await loadSuppressionRules();
      };
      li.appendChild(btn);
      list.appendChild(li);
    }
  } catch {
    stats.textContent = "No se pudieron cargar las reglas";
  }
}

function renderTimeline(job, id) {
  const tl = $("#timeline");
  const badge = $("#reviewPendingBadge");
  if (!tl) return;
  tl.innerHTML = "";
  const summary = job.review_summary || {};
  if (badge) {
    const pending = summary.pending || 0;
    badge.textContent = `${pending} sin revisar`;
    badge.classList.toggle("hidden", !pending);
  }
  const f0 = job.focus_from_sec;
  const f1 = job.focus_until_sec;
  const hasFocusWindow = f0 != null && f1 != null && Number(f1) > Number(f0);
  const events = (job.analysis?.timeline || []).filter(
    (ev) => showDismissedEvents || ev.review_status !== "dismissed",
  );
  for (const ev of events) {
    const li = document.createElement("li");
    const status = ev.review_status || "";
    if (status === "confirmed") li.classList.add("ev-confirmed");
    if (status === "dismissed") li.classList.add("ev-dismissed");
    const btn = document.createElement("button");
    btn.type = "button";
    const t = Number(ev.time_sec ?? 0);
    const inFocus = hasFocusWindow && t >= Number(f0) && t <= Number(f1);
    btn.className = `timeline-ev-btn sev-${ev.severity || "medium"}${ev.type === "knowledge_match" ? " knowledge-ev" : ""}${ev.type === "knowledge_conjecture" ? " knowledge-conj" : ""}${inFocus ? " focus-ev" : ""}`;
    const cam = ev.camera ? ` [${ev.camera}]` : "";
    const evImg = ev.evidence_image ? `<span class="ev-evidence">📷 evidencia: ${ev.evidence_image}</span>` : "";
    const reviewTag =
      status === "confirmed"
        ? '<span class="ev-review-tag ok">✓ confirmado</span>'
        : status === "dismissed"
          ? '<span class="ev-review-tag muted">✗ descartado</span>'
          : "";
    const noteTag = ev.review_note ? `<span class="ev-review-note">Nota: ${ev.review_note}</span>` : "";
    btn.innerHTML = `${ev.time_label}${cam} · ${eventTypeLabel(ev.type)}: ${ev.message}${reviewTag}${noteTag}${evImg}`;
    btn.onclick = () => {
      seekVideoTo(t, ev.camera);
      if (ev.evidence_image) highlightKeyframe(id, ev.evidence_image);
    };
    li.appendChild(btn);
    const eventId = ev.event_id;
    if (eventId) {
      const actions = document.createElement("div");
      actions.className = "timeline-ev-actions";
      if (status === "dismissed") {
        const restoreBtn = document.createElement("button");
        restoreBtn.type = "button";
        restoreBtn.className = "ev-act-restore";
        restoreBtn.textContent = "↩ Restaurar";
        restoreBtn.onclick = (e) => {
          e.stopPropagation();
          void reviewTimelineEvent(id, eventId, "restored");
        };
        actions.appendChild(restoreBtn);
      } else {
        const confirmBtn = document.createElement("button");
        confirmBtn.type = "button";
        confirmBtn.className = "ev-act-confirm";
        confirmBtn.textContent = status === "confirmed" ? "✓ Confirmado" : "✓ Confirmar";
        confirmBtn.disabled = status === "confirmed";
        confirmBtn.onclick = (e) => {
          e.stopPropagation();
          void reviewTimelineEvent(id, eventId, "confirmed");
        };
        const dismissBtn = document.createElement("button");
        dismissBtn.type = "button";
        dismissBtn.className = "ev-act-dismiss";
        dismissBtn.textContent = "✗ Falso positivo";
        dismissBtn.onclick = (e) => {
          e.stopPropagation();
          void reviewTimelineEvent(id, eventId, "dismissed");
        };
        actions.appendChild(confirmBtn);
        actions.appendChild(dismissBtn);
      }
      li.appendChild(actions);
    }
    tl.appendChild(li);
  }
  if (!tl.children.length) {
    tl.innerHTML = "<li class='muted'>Sin eventos detectados en el muestreo.</li>";
  }
}

async function promoteKeyframe(jobId, keyframeName, timeLabel) {
  const title = prompt("Título de la situación:", `Incidente en ${timeLabel}`);
  if (!title) return;
  const description = prompt("¿Qué ocurrió acá?", "") || "";
  const situationType = $("#knSituationType")?.value || "other";
  try {
    await api(`/api/forense/jobs/${jobId}/knowledge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        keyframe_name: keyframeName,
        title,
        situation_type: situationType,
        description,
      }),
    });
    await loadKnowledge();
    alert("Captura guardada en la biblioteca de aprendizaje.");
  } catch (err) {
    alert(err.message);
  }
}

function renderVideoAi(job) {
  const sec = $("#videoAiSection");
  const body = $("#videoAiBody");
  const meta = $("#videoAiMeta");
  if (!sec || !body) return;
  const va = job.video_ai;
  if (!va) {
    sec.classList.add("hidden");
    body.textContent = "";
    return;
  }
  sec.classList.remove("hidden");
  const fw = va.focus_window || {};
  const fwTxt =
    fw.from_sec != null && fw.until_sec != null
      ? `Ventana ${fw.from_sec}s–${fw.until_sec}s · `
      : "";
  if (meta) {
    meta.textContent = `${fwTxt}${va.frames_used || 0} capturas · modelo ${va.model || "—"}`;
  }
  const p = va.parsed;
  if (p) {
    const lines = [];
    if (p.resumen) lines.push(String(p.resumen));
    const seq = p.secuencia || [];
    if (seq.length) {
      lines.push("\nSecuencia observada:");
      for (const item of seq) {
        if (item && typeof item === "object") {
          lines.push(`• ${item.hora || "—"}: ${item.observacion || ""}`);
        } else {
          lines.push(`• ${item}`);
        }
      }
    }
    const fp = p.posibles_falsos_positivos || [];
    if (fp.length) {
      lines.push("\nPosibles falsos positivos del detector:");
      for (const f of fp) lines.push(`• ${f}`);
    }
    const rec = p.recomendaciones || [];
    if (rec.length) {
      lines.push("\nRecomendaciones:");
      for (const r of rec) lines.push(`• ${r}`);
    }
    body.textContent = lines.join("\n");
  } else {
    body.textContent = va.raw || "—";
  }
}

async function loadJob(id, quiet = false) {
  const data = await api(`/api/forense/jobs/${id}`);
  const j = data.job;
  $("#jobTitle").textContent = j.title || id;
  const srcCount = j.sources?.length || j.analysis?.sources_count || 1;
  $("#jobMeta").textContent =
    `${j.site || ""} · ${j.template_name || j.template_id || ""} · ${statusLabel(j.status)} · ` +
    `${j.analysis?.event_count || 0} eventos · ${j.frames_analyzed || 0} fotogramas · ${srcCount} cámara(s)`;

  setupVideoViewer(j, id, { isPoll: quiet });
  renderVideoAi(j);
  renderCriticalAlerts(j, id);
  const refSec = $("#refocusSection");
  if (refSec) {
    const canRefocus = Boolean(j.has_video) && (j.sources?.length || 1) === 1;
    refSec.classList.toggle("hidden", !canRefocus);
    if (canRefocus) {
      const desc = $("#refocusDescription");
      const rf = $("#refocusFrom");
      const ru = $("#refocusUntil");
      const rs = $("#refocusStrict");
      if (desc && !desc.dataset.touched) {
        desc.value = j.focus_description || "";
      }
      if (rf && !rf.dataset.touched && j.focus_from_sec != null) rf.value = String(j.focus_from_sec);
      if (ru && !ru.dataset.touched && j.focus_until_sec != null) ru.value = String(j.focus_until_sec);
      if (rs) rs.checked = Boolean(j.strict_detection);
    }
  }
  if (j.status === "processing" || j.status === "queued") {
    await fetchIncrementalFrames(id);
  }

  const pw = $("#progressWrap");
  if (j.status === "processing" || j.status === "queued") {
    pw.classList.remove("hidden");
    $("#progressBar").style.width = `${j.progress || 0}%`;
    $("#progressText").textContent = j.progress_message || "";
    $("#progressText").style.color = "";
  } else if (j.status === "error") {
    pw.classList.remove("hidden");
    $("#progressBar").style.width = `${j.progress || 0}%`;
    $("#progressText").textContent = `Error: ${j.error || j.progress_message || "Falló el análisis"}`;
    $("#progressText").style.color = "#f07178";
  } else {
    pw.classList.add("hidden");
    $("#progressText").style.color = "";
    if (j.status === "done" && pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  const knSec = $("#knowledgeSection");
  const knMatches = j.knowledge?.matches || [];
  const knUl = $("#knowledgeMatches");
  knUl.innerHTML = "";
  if (knMatches.length) {
    knSec.classList.remove("hidden");
    const strong = knMatches.filter((m) => !m.conjecture);
    if (!strong.length && knMatches.length) {
      const warn = document.createElement("p");
      warn.className = "hint";
      warn.textContent =
        "Solo conjeturas débiles — no hay coincidencia confiable. Describí el caso en el título o enseñá esta situación a la biblioteca.";
      knUl.appendChild(warn);
    }
    for (const m of knMatches) {
      const li = document.createElement("li");
      const tag = m.conjecture ? "Conjetura" : "Coincidencia";
      li.innerHTML = `<strong>${tag}: ${m.title}</strong> (${m.situation_label}) — ${m.confidence_pct}% · ${(m.reasons || []).join(", ")}`;
      if (m.description) {
        const p = document.createElement("p");
        p.className = "muted small";
        p.textContent = m.description;
        li.appendChild(p);
      }
      knUl.appendChild(li);
    }
  } else {
    knSec.classList.add("hidden");
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
    tr.innerHTML = `<td>#${row.track_id}</td><td>${kindLabel(row.kind)}</td><td>${row.max_kmh}</td><td>${row.avg_kmh}</td>`;
    tbody.appendChild(tr);
  }
  if (!tbody.children.length) {
    tbody.innerHTML = "<tr><td colspan='4' class='muted'>Sin seguimientos suficientes</td></tr>";
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
    const hmImg = $("#heatmapImg");
    if (hmImg) void loadAuthedImage(hmImg, `/api/forense/jobs/${id}/heatmap.jpg`, `hm:${id}`);
  } else {
    hmSec.classList.add("hidden");
    revokeImageBlobs(`hm:${id}`);
  }

  renderTimeline(j, id);

  const kf = $("#keyframes");
  revokeImageBlobs(`kf:${id}:`);
  kf.innerHTML = "";
  selectedKeyframeName = null;
  $("#btnKeyframeTeach")?.setAttribute("disabled", "disabled");
  for (const frame of j.analysis?.keyframes || []) {
    if (!frame.image) continue;
    const wrap = document.createElement("button");
    wrap.type = "button";
    wrap.className = "keyframe-btn";
    wrap.dataset.image = frame.image;
    wrap.title = "Clic: seleccionar · doble clic: guardar en biblioteca";
    const img = document.createElement("img");
    img.alt = frame.time_label;
    wrap.appendChild(img);
    void loadAuthedImage(
      img,
      `/api/forense/jobs/${id}/keyframes/${frame.image}`,
      `kf:${id}:${frame.image}`,
    );
    const cap = document.createElement("span");
    cap.className = "small muted";
    cap.textContent = frame.time_label;
    wrap.appendChild(cap);
    wrap.onclick = () => {
      kf.querySelectorAll(".keyframe-btn").forEach((b) => b.classList.remove("selected"));
      wrap.classList.add("selected");
      selectedKeyframeName = frame.image;
      $("#btnKeyframeTeach")?.removeAttribute("disabled");
    };
    wrap.ondblclick = () => promoteKeyframe(id, frame.image, frame.time_label);
    kf.appendChild(wrap);
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
      ? `Último envío a EHS: ${ehs.map((r) => (r.ok ? "listo" : r.error || "error")).join(", ")}`
      : "";
  } else {
    if (!quiet) $("#reportMd").textContent = "Informe disponible al completar el análisis…";
    pdf.classList.add("hidden");
    committee.classList.add("hidden");
    bundle.classList.add("hidden");
    ehsBtn.classList.add("hidden");
  }
}

$("#btnReanalyze")?.addEventListener("click", async () => {
  if (!currentJobId) return;
  if (!confirm("¿Re-analizar el caso completo con el motor actual? Puede tardar 1–3 min.")) return;
  const btn = $("#btnReanalyze");
  if (btn) btn.disabled = true;
  try {
    await api(`/api/forense/jobs/${currentJobId}/reanalyze`, { method: "POST" });
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => loadJob(currentJobId, true), 2000);
    await loadJob(currentJobId);
    showToast("Re-análisis iniciado", "info");
  } catch (err) {
    alert(err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
});

$("#btnDeleteJob")?.addEventListener("click", async () => {
  if (!currentJobId) return;
  if (!confirm("¿Eliminar este trabajo y todos sus archivos?")) return;
  try {
    await api(`/api/forense/jobs/${currentJobId}`, { method: "DELETE" });
    resetNewCaseForm();
  } catch (err) {
    alert(err.message);
  }
});

for (const id of ["refocusDescription", "refocusFrom", "refocusUntil"]) {
  const el = document.getElementById(id);
  el?.addEventListener("input", () => {
    el.dataset.touched = "1";
  });
}

$("#btnRefocus")?.addEventListener("click", async () => {
  if (!currentJobId) return;
  const fromSec = parseFloat($("#refocusFrom")?.value || "");
  const untilSec = parseFloat($("#refocusUntil")?.value || "");
  if (!Number.isFinite(fromSec) || !Number.isFinite(untilSec) || untilSec <= fromSec) {
    alert("Indicá una ventana válida (hasta > desde).");
    return;
  }
  const btn = $("#btnRefocus");
  if (btn) btn.disabled = true;
  try {
    await api(`/api/forense/jobs/${currentJobId}/refocus`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        focus_description: $("#refocusDescription")?.value || "",
        focus_from_sec: fromSec,
        focus_until_sec: untilSec,
        strict_detection: Boolean($("#refocusStrict")?.checked),
      }),
    });
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => loadJob(currentJobId, true), 2000);
    await loadJob(currentJobId);
  } catch (err) {
    alert(err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
});

$("#incidentPresets")?.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-preset]");
  if (!btn) return;
  applyIncidentPreset(btn.dataset.preset);
});

const toggleDismissed = $("#toggleDismissedEvents");
if (toggleDismissed) {
  toggleDismissed.checked = showDismissedEvents;
  toggleDismissed.addEventListener("change", () => {
    showDismissedEvents = toggleDismissed.checked;
    localStorage.setItem("forenseShowDismissed", showDismissedEvents ? "1" : "0");
    if (currentJobId) void loadJob(currentJobId, true);
  });
}

$("#exportEhs")?.addEventListener("click", async () => {
  if (!currentJobId) return;
  $("#ehsStatus").textContent = "Exportando…";
  try {
    const res = await api(`/api/forense/jobs/${currentJobId}/export-ehs`, { method: "POST" });
    const msg = (res.results || []).map((r) => (r.ok ? "listo" : r.error || "error")).join(", ");
    $("#ehsStatus").textContent = `EHS: ${msg || "sin respuesta"}`;
  } catch (err) {
    $("#ehsStatus").textContent = err.message;
  }
});

$("#uploadForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = $("#caseVideo").files?.[0];
  if (!file) {
    alert("Seleccioná un video principal antes de iniciar el análisis.");
    return;
  }
  if (!isSupportedVideoFile(file)) {
    alert("Formato no soportado. Usá AVI, MP4, MOV, MKV, WMV, TS, MPG, FLV, 3GP, DAV u otro contenedor de video.");
    return;
  }
  for (const extra of [$("#caseVideo2").files?.[0], $("#caseVideo3").files?.[0]]) {
    if (extra && !isSupportedVideoFile(extra)) {
      alert(`Formato no soportado en cámara adicional: ${extra.name}`);
      return;
    }
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
  fd.append("case_notes", $("#caseNotes")?.value || "");
  fd.append("focus_description", $("#caseFocus")?.value || "");
  const ff = $("#caseFocusFrom")?.value;
  const fu = $("#caseFocusUntil")?.value;
  if (ff) fd.append("focus_from_sec", ff);
  if (fu) fd.append("focus_until_sec", fu);
  if ($("#caseStrict")?.checked) fd.append("strict_detection", "1");
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