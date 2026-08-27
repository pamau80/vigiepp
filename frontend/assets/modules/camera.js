import { $, escapeHtml } from "./dom.js";

/** Webcam, RTSP, overlay de video y pantalla completa. */
export function createCameraController({
  api,
  els,
  settings,
  requiredQueryValue,
  isMobile,
  isIOS,
  applyGuideMode,
  setAlignment,
  getAppMode,
  isDetectLoopOn,
  startDetectLoop,
  stopDetectLoop,
  updateUi,
  getLastIdentifyAt,
  setLastIdentifyAt,
}) {
  let mediaStream = null;
  let rtspTimer = null;
  let sourceMode = "camera";
  let preferredFacing = "user";

  function setOverlayHint(text, { showStart = true } = {}) {
    if (!els.overlayHint) return;
    els.overlayHint.hidden = false;
    const p = els.overlayHint.querySelector("p");
    if (p) p.textContent = text;
    const btn = $("#btnOverlayStart");
    if (btn) btn.classList.toggle("hidden", !showStart);
  }

  function hideLiveVideo() {
    if (els.liveVideo) {
      els.liveVideo.hidden = true;
      els.liveVideo.removeAttribute("src");
      try {
        els.liveVideo.srcObject = null;
      } catch (_) {}
    }
    if (els.liveBadge) els.liveBadge.hidden = true;
  }

  function showLive() {
    els.overlayHint.hidden = true;
    els.annotatedImg.hidden = true;
    const hasFrames = !!(els.liveVideo?.videoWidth && mediaStream);
    els.liveVideo.hidden = !hasFrames;
    els.overlayCanvas.hidden = false;
    if (els.liveBadge) els.liveBadge.hidden = !hasFrames;
  }

  async function cameraPermissionState() {
    try {
      if (!navigator.permissions?.query) return "unknown";
      const st = await navigator.permissions.query({ name: "camera" });
      return st.state || "unknown";
    } catch (_) {
      return "unknown";
    }
  }

  async function refreshCameraPermissionHint() {
    const state = await cameraPermissionState();
    if (state === "denied") {
      setOverlayHint(
        "Chrome bloqueó la cámara en este sitio (ícono con X roja en la barra). Tocá ese ícono → Cámara → Permitir → Recargar, y después Iniciar.",
        { showStart: true }
      );
      return "denied";
    }
    if (!mediaStream) {
      setOverlayHint("Tocá Iniciar y permití la cámara para evaluar EPP", { showStart: true });
    }
    return state;
  }

  async function waitForVideoFrames(timeoutMs = 4000) {
    const video = els.liveVideo;
    if (!video) return false;
    if (video.videoWidth > 0) return true;
    return new Promise((resolve) => {
      let done = false;
      const finish = (ok) => {
        if (done) return;
        done = true;
        video.removeEventListener("loadeddata", onReady);
        video.removeEventListener("playing", onReady);
        clearTimeout(timer);
        resolve(ok);
      };
      const onReady = () => finish(video.videoWidth > 0);
      video.addEventListener("loadeddata", onReady);
      video.addEventListener("playing", onReady);
      const timer = setTimeout(() => finish(video.videoWidth > 0), timeoutMs);
    });
  }

  function clearOverlay() {
    const c = els.overlayCanvas;
    const ctx = c.getContext("2d");
    ctx.clearRect(0, 0, c.width, c.height);
  }

  function syncCanvasSize() {
    const canvas = els.overlayCanvas;
    const frame = canvas.parentElement;
    const rect = frame.getBoundingClientRect();
    canvas.width = Math.max(1, Math.round(rect.width));
    canvas.height = Math.max(1, Math.round(rect.height));
  }

  function enterFullscreen() {
    const root = document.documentElement;
    const req = root.requestFullscreen || root.webkitRequestFullscreen || root.msRequestFullscreen;
    if (!req) return Promise.resolve();
    try {
      const p = req.call(root);
      return p && typeof p.then === "function" ? p.catch(() => {}) : Promise.resolve();
    } catch (_) {
      return Promise.resolve();
    }
  }

  function exitFullscreen() {
    if (!document.fullscreenElement && !document.webkitFullscreenElement) return;
    const exit = document.exitFullscreen || document.webkitExitFullscreen;
    if (exit) {
      try {
        exit.call(document);
      } catch (_) {}
    }
  }

  function isFullscreen() {
    return !!(document.fullscreenElement || document.webkitFullscreenElement);
  }

  async function openCameraStream(facing) {
    const mobile = isMobile();
    const attempts = mobile
      ? [
          { video: { facingMode: { ideal: facing }, width: { ideal: 720 }, height: { ideal: 960 } }, audio: false },
          { video: { facingMode: facing }, audio: false },
          { video: true, audio: false },
        ]
      : [
          {
            video: {
              facingMode: { ideal: facing },
              width: { ideal: 720 },
              height: { ideal: 960 },
              aspectRatio: { ideal: 0.75 },
            },
            audio: false,
          },
          { video: { facingMode: { ideal: facing } }, audio: false },
          { video: true, audio: false },
        ];
    let lastErr = null;
    for (const constraints of attempts) {
      try {
        return await navigator.mediaDevices.getUserMedia(constraints);
      } catch (err) {
        lastErr = err;
      }
    }
    throw lastErr || new Error("No se pudo abrir la cámara");
  }

  async function startCamera(opts = {}) {
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("Este navegador no permite cámara. Usá Chrome/Safari actualizado por HTTPS.");
      }
      if (!window.isSecureContext) {
        throw new Error("La cámara requiere HTTPS. Abrí vigiepp.onrender.com o localhost.");
      }
      setOverlayHint("Pedí permiso de cámara en el navegador…", { showStart: false });
      if (!mediaStream) {
        mediaStream = await openCameraStream(preferredFacing);
        els.liveVideo.setAttribute("playsinline", "");
        els.liveVideo.setAttribute("webkit-playsinline", "");
        els.liveVideo.muted = true;
        els.liveVideo.srcObject = mediaStream;
        els.liveVideo.hidden = false;
        try {
          await els.liveVideo.play();
        } catch (_) {}
      }
      const hasFrames = await waitForVideoFrames();
      if (!hasFrames) {
        throw new Error("NoImage");
      }
      showLive();
      els.btnStartCam.disabled = true;
      els.btnStopCam.disabled = false;
      if (els.btnFlipCam) els.btnFlipCam.disabled = false;
      stopDetectLoop();
      if (!opts.silentDetect && getAppMode() === "live" && sourceMode === "camera") {
        startDetectLoop();
      }
    } catch (err) {
      console.error(err);
      if (mediaStream) {
        mediaStream.getTracks().forEach((t) => t.stop());
        mediaStream = null;
      }
      hideLiveVideo();
      els.btnStartCam.disabled = false;
      els.btnStopCam.disabled = true;
      const msg = String(err?.name || err?.message || err || "");
      const perm = await cameraPermissionState();
      let tip = "No se pudo acceder a la cámara. Tocá Iniciar y permití el acceso.";
      if (perm === "denied" || /NotAllowed|Permission|denied/i.test(msg)) {
        tip = isIOS()
          ? "Cámara bloqueada. En Ajustes → Safari → Cámara, permití acceso y recargá."
          : "Chrome bloqueó la cámara (ícono con X roja junto a la URL). Tocá ese ícono → Cámara → Permitir → Recargar → Iniciar.";
      } else if (/NotReadable|TrackStart|AbortError/i.test(msg)) {
        tip = "La cámara está ocupada por otra app (Zoom, Teams, Meet…). Cerrala y tocá Iniciar.";
      } else if (/NoImage/i.test(msg)) {
        tip = "La cámara no entrega imagen. Cerrá otras apps que la usen y tocá Iniciar.";
      } else if (/NotFound|DevicesNotFound/i.test(msg)) {
        tip = "No hay cámara disponible en este dispositivo.";
      } else if (/secure|HTTPS/i.test(msg)) {
        tip = msg;
      }
      setOverlayHint(tip, { showStart: true });
    }
  }

  async function flipCamera() {
    preferredFacing = preferredFacing === "user" ? "environment" : "user";
    if (mediaStream) {
      mediaStream.getTracks().forEach((t) => t.stop());
      mediaStream = null;
      els.liveVideo.srcObject = null;
    }
    const wasScanning = isDetectLoopOn();
    stopDetectLoop();
    try {
      mediaStream = await openCameraStream(preferredFacing);
      els.liveVideo.srcObject = mediaStream;
      await els.liveVideo.play().catch(() => {});
      showLive();
      els.btnStartCam.disabled = true;
      els.btnStopCam.disabled = false;
      if (wasScanning && getAppMode() === "live" && sourceMode === "camera") {
        startDetectLoop();
      }
      const hint = $("#speedHint");
      if (hint) {
        hint.textContent = preferredFacing === "user" ? "Cámara frontal" : "Cámara trasera";
      }
    } catch (err) {
      preferredFacing = preferredFacing === "user" ? "environment" : "user";
      els.overlayHint.hidden = false;
      els.overlayHint.querySelector("p").textContent = "No se pudo cambiar de cámara en este dispositivo.";
    }
  }

  function stopCamera() {
    stopDetectLoop();
    document.body.classList.remove("is-scanning");
    applyGuideMode();
    if (mediaStream) {
      mediaStream.getTracks().forEach((t) => t.stop());
      mediaStream = null;
    }
    hideLiveVideo();
    els.btnStartCam.disabled = false;
    els.btnStopCam.disabled = true;
    clearOverlay();
    els.personChip.classList.add("hidden");
    setOverlayHint("Tocá Iniciar y permití la cámara para evaluar EPP", { showStart: true });
    setAlignment("idle", "Posicionate");
  }

  async function refreshCameras() {
    if (!els.cameraSelect) return;
    try {
      const data = await api("/api/cameras");
      const cams = data.cameras || [];
      const cur = els.cameraSelect.value;
      els.cameraSelect.innerHTML =
        `<option value="">— Elegí o pegá URL —</option>` +
        cams
          .map(
            (c) =>
              `<option value="${c.id}" data-url="${encodeURIComponent(c.url)}">${escapeHtml(c.name)}</option>`
          )
          .join("");
      if (cur && [...els.cameraSelect.options].some((o) => o.value === cur)) {
        els.cameraSelect.value = cur;
      }
    } catch (_) {}
  }

  async function saveCurrentCamera() {
    const url = els.rtspUrl?.value.trim();
    if (!url) {
      alert("Pegá una URL rtsp://");
      return;
    }
    const name = els.cameraName?.value.trim() || "";
    const id = els.cameraSelect?.value || undefined;
    await api("/api/cameras", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, url, id: id || null }),
    });
    await refreshCameras();
  }

  async function deleteSelectedCamera() {
    const id = els.cameraSelect?.value;
    if (!id) return;
    await api(`/api/cameras/${id}`, { method: "DELETE" });
    if (els.rtspUrl) els.rtspUrl.value = "";
    if (els.cameraName) els.cameraName.value = "";
    await refreshCameras();
  }

  async function startRtsp() {
    const url = els.rtspUrl.value.trim();
    if (!url) return;
    await api("/api/rtsp/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, profile: els.profileSelect.value }),
    });
    els.btnStartRtsp.disabled = true;
    els.btnStopRtsp.disabled = false;
    els.overlayHint.hidden = true;
    els.liveBadge.hidden = false;
    document.body.classList.add("is-scanning");
    applyGuideMode();
    const poll = async () => {
      const wantId = !!els.chkIdentify?.checked && Date.now() - getLastIdentifyAt() > 2200;
      if (wantId) setLastIdentifyAt(Date.now());
      const q = new URLSearchParams({
        url,
        profile: els.profileSelect.value,
        conf: "0.35",
        identify: String(wantId),
        required: requiredQueryValue(),
      });
      try {
        const data = await api(`/api/rtsp/frame?${q}`);
        if (data.ok) updateUi(data);
      } catch (err) {
        console.error(err);
      }
    };
    await poll();
    rtspTimer = setInterval(poll, 1000);
  }

  async function stopRtsp() {
    if (rtspTimer) {
      clearInterval(rtspTimer);
      rtspTimer = null;
    }
    const url = els.rtspUrl.value.trim();
    if (url) {
      try {
        await api("/api/rtsp/stop", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url, profile: els.profileSelect.value }),
        });
      } catch (_) {}
    }
    els.btnStartRtsp.disabled = false;
    els.btnStopRtsp.disabled = true;
    els.liveBadge.hidden = true;
    document.body.classList.remove("is-scanning");
    applyGuideMode();
  }

  function setSourceMode(mode) {
    sourceMode = mode;
  }

  function bindCameraEvents() {
    els.btnStartCam.addEventListener("click", () => startCamera());
    $("#btnOverlayStart")?.addEventListener("click", () => startCamera());
    els.btnStopCam.addEventListener("click", stopCamera);
    if (els.btnFlipCam) {
      els.btnFlipCam.addEventListener("click", () => flipCamera());
    }
    if (els.btnFullscreen) {
      els.btnFullscreen.addEventListener("click", async () => {
        if (isIOS()) {
          document.body.classList.toggle("is-scanning");
          return;
        }
        if (isFullscreen()) exitFullscreen();
        else await enterFullscreen();
      });
    }
    document.addEventListener("fullscreenchange", () => {
      if (els.btnFullscreen) {
        els.btnFullscreen.textContent = isFullscreen() ? "Salir pantalla completa" : "Pantalla completa";
      }
      document.body.classList.toggle("is-fullscreen", isFullscreen());
      if (mediaStream && els.liveVideo?.srcObject) {
        els.liveVideo.play().catch(() => {});
      }
    });
    els.btnStartRtsp.addEventListener("click", startRtsp);
    els.btnStopRtsp.addEventListener("click", stopRtsp);
    els.cameraSelect?.addEventListener("change", () => {
      const opt = els.cameraSelect.selectedOptions[0];
      if (!opt?.value) return;
      try {
        els.rtspUrl.value = decodeURIComponent(opt.dataset.url || "");
      } catch (_) {
        els.rtspUrl.value = "";
      }
      if (els.cameraName) els.cameraName.value = opt.textContent || "";
    });
    els.btnSaveCamera?.addEventListener("click", () => saveCurrentCamera().catch((e) => alert(e.message)));
    els.btnDelCamera?.addEventListener("click", () => deleteSelectedCamera().catch((e) => alert(e.message)));
  }

  return {
    getSourceMode: () => sourceMode,
    setSourceMode,
    hasMediaStream: () => mediaStream,
    setOverlayHint,
    hideLiveVideo,
    showLive,
    refreshCameraPermissionHint,
    syncCanvasSize,
    clearOverlay,
    startCamera,
    stopCamera,
    flipCamera,
    refreshCameras,
    saveCurrentCamera,
    deleteSelectedCamera,
    startRtsp,
    stopRtsp,
    enterFullscreen,
    exitFullscreen,
    isFullscreen,
    bindCameraEvents,
  };
}
