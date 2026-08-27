/** Bucle de detección en vivo (HTTP /api/detect). */
export function createDetectLiveController({
  api,
  els,
  settings,
  requiredQueryValue,
  applyHealth,
  updateUi,
  applyGuideMode,
  isLiveMode,
  getSourceMode,
  getCombinedInference,
  getEppStreak,
  setEppStreak,
  getLastIdentifyAt,
  setLastIdentifyAt,
  getLastScanRefreshAt,
  setLastScanRefreshAt,
  refreshScans,
  setIdentityCard,
  drawDetections,
  getLastFrameSize,
  setLastFaceBox,
  setLastIdentity,
}) {
  let busy = false;
  let detectBackoffMs = 0;
  let detectLoopOn = false;
  let camTimer = null;

async function detectBlob(blob, { identify = false, returnImage = false } = {}) {
  if (busy) return;
  busy = true;
  const t0 = performance.now();
  try {
    const fd = new FormData();
    fd.append("file", blob, "frame.jpg");
    fd.append("profile", els.profileSelect.value);
    fd.append("conf", "0.35");
    fd.append("identify", identify ? "true" : "false");
    fd.append("return_image", returnImage ? "true" : "false");
    fd.append("imgsz", "256");
    fd.append("threshold", String(settings.identifyThreshold || 0.33));
    fd.append("required", requiredQueryValue());
    const data = await api("/api/detect", { method: "POST", body: fd }, 18000);
    if (data?.down || data?._http === 502) {
      detectBackoffMs = Math.min(10000, Math.max(3500, (detectBackoffMs || 2000) * 1.35));
      els.fpsLabel.textContent = "reintentando…";
      if (els.complianceSummary) els.complianceSummary.textContent = "Servidor ocupado. Reintentando…";
      return;
    }
    if (data?.booting || data?._http === 503) {
      let ready = false;
      try {
        const h = await fetch("/api/health", { credentials: "include" }).then((r) => r.json());
        ready = !!applyHealth(h);
      } catch (_) {}
      if (ready) {
        detectBackoffMs = 900;
        els.fpsLabel.textContent = "EPP cargando…";
        if (els.complianceSummary) {
          els.complianceSummary.textContent =
            "YOLO cargando (~15 s tras arranque). El escaneo EPP sigue en cola…";
        }
      } else {
        detectBackoffMs = 2200;
        els.fpsLabel.textContent = "cargando IA…";
        if (els.complianceSummary) {
          els.complianceSummary.textContent = data.error || "Modelo cargando…";
        }
      }
      return;
    }
    if (data?._http === 429 || data?.busy) {
      detectBackoffMs = 700;
      els.fpsLabel.textContent = "IA ocupada";
      return;
    }
    if (!data?.ok) {
      els.fpsLabel.textContent = "sin frame";
      return;
    }
    updateUi(data);
    if (identify && data.identity?.known) maybeRefreshScans();
    if (identify && data.identity?.booting) {
      els.identityName.textContent = "ID cargando…";
      els.identityRut.textContent = "El reconocimiento facial aún inicia";
    }
    detectBackoffMs = 0;
    els.fpsLabel.textContent = `${Math.round(performance.now() - t0)} ms IA`;
  } catch (err) {
    console.error(err);
    const msg = String(err?.message || err || "");
    const down = /502|503|caído|agotado|timeout|HTTP2|protocol|ocupado/i.test(msg);
    if (down) detectBackoffMs = Math.min(10000, Math.max(3500, (detectBackoffMs || 2000) * 1.35));
    els.fpsLabel.textContent = down ? "reintentando…" : /401|sesión|PIN/i.test(msg) ? "sesión" : "error IA";
    if (els.complianceSummary) {
      els.complianceSummary.textContent = down
        ? "Servidor ocupado. Reintentando…"
        : msg;
    }
  } finally {
    busy = false;
  }
}

function captureBlob(quality = 0.7, maxW = 480) {
  return new Promise((resolve) => {
    const video = els.liveVideo;
    if (!video.videoWidth) return resolve(null);
    const vw = video.videoWidth;
    const vh = video.videoHeight;

    // Recorte vertical 3:4 (cuerpo completo) — no horizontal
    let cropW;
    let cropH;
    let sx;
    let sy;
    const targetRatio = 3 / 4;
    if (vw / vh > targetRatio) {
      cropH = vh;
      cropW = Math.round(vh * targetRatio);
      sx = Math.round((vw - cropW) / 2);
      sy = 0;
    } else {
      cropW = vw;
      cropH = Math.round(vw / targetRatio);
      sx = 0;
      sy = Math.max(0, Math.round((vh - cropH) * 0.12));
    }

    const scale = Math.min(1, maxW / cropW);
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(cropW * scale);
    canvas.height = Math.round(cropH * scale);
    canvas
      .getContext("2d")
      .drawImage(video, sx, sy, cropW, cropH, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => resolve(blob), "image/jpeg", quality);
  });
}

function captureFaceBlob(quality = 0.88, maxW = 560) {
  return new Promise((resolve) => {
    const video = els.liveVideo;
    let tries = 0;
    const attempt = () => {
      if (!video?.videoWidth) {
        if (++tries < 80) return setTimeout(attempt, 50);
        return resolve(null);
      }
      const vw = video.videoWidth;
      const vh = video.videoHeight;
      const side = Math.min(vw, Math.round(vh * 0.62));
      const sx = Math.max(0, Math.round((vw - side) / 2));
      const sy = Math.max(0, Math.round(vh * 0.05));
      const sw = Math.min(side, vw - sx);
      const sh = Math.min(side, vh - sy);
      const scale = Math.min(1, maxW / sw);
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(sw * scale);
      canvas.height = Math.round(sh * scale);
      canvas
        .getContext("2d")
        .drawImage(video, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => resolve(blob), "image/jpeg", quality);
    };
    attempt();
  });
}

async function identifyLiveFrame({ flash = false } = {}) {
  const blob = await captureFaceBlob(flash ? 0.9 : 0.72, flash ? 560 : 400);
  if (!blob) return null;
  const fd = new FormData();
  fd.append("file", blob, "id.jpg");
  fd.append("threshold", String(settings.identifyThreshold || 0.33));
  fd.append("return_image", flash ? "true" : "false");
  const data = await api("/api/identity/identify", { method: "POST", body: fd }, 12000);
  if (data?.down || data?._http === 502 || data?.booting || data?._http === 503) {
    detectBackoffMs = Math.min(10000, Math.max(3500, (detectBackoffMs || 2000) * 1.35));
    if (els.identityMethod) els.identityMethod.textContent = "Identificando… (servidor ocupado)";
    return null;
  }
  if (data?._http === 429 || data?.busy) {
    detectBackoffMs = 700;
    return null;
  }
  const m0 = data.matches?.[0] || {};
  const faceBox = m0.box || null;
  if (faceBox) setLastFaceBox(faceBox);
  const identified = data.identified;
  const card = {
    known: !!identified?.id,
    name: identified?.name || null,
    rut: identified?.rut || null,
    score: m0.score,
    confidence: m0.confidence,
    reject_reason: m0.reject_reason,
    faces_detected: data.faces_detected || 0,
    face_box: faceBox,
    gallery_size: data.gallery_size,
  };
  setLastIdentity(card);
  setIdentityCard(card);
  drawDetections([], getLastFrameSize().w, getLastFrameSize().h, card);
  if (card.known) maybeRefreshScans();
  return data;
}

function maybeRefreshScans() {
  const now = Date.now();
  if (now - getLastScanRefreshAt() < 10000) return;
  setLastScanRefreshAt(now);
  refreshScans().catch(() => {});
}

async function tickDetect() {
  if (!isLiveMode() || getSourceMode() !== "camera") return;
  const wantId = !!els.chkIdentify?.checked;
  const now = Date.now();

  if (wantId && getCombinedInference()) {
    const blob = await captureBlob(0.42, 320);
    if (!blob) return;
    try {
      await detectBlob(blob, { identify: true, returnImage: false });
      detectBackoffMs = Math.min(detectBackoffMs || 0, 400);
    } catch (err) {
      const msg = String(err?.message || err || "");
      if (/502|503|caído|agotado|timeout|ocupado/i.test(msg)) {
        detectBackoffMs = Math.min(10000, Math.max(3500, (detectBackoffMs || 2000) * 1.35));
      }
    }
    return;
  }

  // 2 escaneos EPP + 1 ID: más fluido y sin cargar YOLO+SFace juntos (cloud)
  if (wantId) {
    const dueId = getEppStreak() >= 2 && now - getLastIdentifyAt() >= 2800;
    if (dueId) {
      setLastIdentifyAt(now);
      setEppStreak(0);
      try {
        await identifyLiveFrame();
        detectBackoffMs = Math.min(detectBackoffMs || 0, 400);
      } catch (err) {
        const msg = String(err?.message || err || "");
        if (/502|503|caído|agotado|timeout|ocupado/i.test(msg)) {
          detectBackoffMs = Math.min(10000, Math.max(3500, (detectBackoffMs || 2000) * 1.35));
        }
        if (els.identityMethod) els.identityMethod.textContent = "Identificando…";
      }
      return;
    }
    const blob = await captureBlob(0.42, 320);
    if (!blob) return;
    await detectBlob(blob, { identify: false, returnImage: false });
    setEppStreak(getEppStreak() + 1);
    return;
  }

  setEppStreak(0);
  const blob = await captureBlob(0.42, 320);
  if (!blob) return;
  await detectBlob(blob, { identify: false, returnImage: false });
}

function startDetectLoop() {
  if (detectLoopOn) return;
  detectLoopOn = true;
  document.body.classList.add("is-scanning");
  applyGuideMode();
  const loop = async () => {
    if (!detectLoopOn) return;
    await tickDetect();
    if (!detectLoopOn) return;
    // Ciclo corto: ~0.7–1.1 s entre frames cuando el servidor responde bien
    const delay = detectBackoffMs || (els.chkIdentify?.checked ? 900 : 700);
    camTimer = setTimeout(loop, delay);
  };
  loop();
}

function stopDetectLoop() {
  detectLoopOn = false;
  if (camTimer) {
    clearTimeout(camTimer);
    camTimer = null;
  }
}


  return {
    detectBlob,
    captureBlob,
    captureFaceBlob,
    identifyLiveFrame,
    tickDetect,
    startDetectLoop,
    stopDetectLoop,
    isDetectLoopOn: () => detectLoopOn,
  };
}
