(() => {
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => [...document.querySelectorAll(sel)];

  const els = {
    profileSelect: $("#profileSelect"),
    profileDesc: $("#profileDesc"),
    requiredChips: $("#requiredChips"),
    modelStatus: $("#modelStatus"),
    modelStatusText: $("#modelStatusText"),
    liveVideo: $("#liveVideo"),
    overlayCanvas: $("#overlayCanvas"),
    annotatedImg: $("#annotatedImg"),
    overlayHint: $("#overlayHint"),
    liveBadge: $("#liveBadge"),
    silhouetteGuide: $("#silhouetteGuide"),
    silHint: $("#silHint"),
    alignBadge: $("#alignBadge"),
    personChip: $("#personChip"),
    personChipName: $("#personChipName"),
    personChipRut: $("#personChipRut"),
    btnStartCam: $("#btnStartCam"),
    btnStopCam: $("#btnStopCam"),
    btnFlipCam: $("#btnFlipCam"),
    btnFullscreen: $("#btnFullscreen"),
    chkFullscreen: $("#chkFullscreen"),
    lblFullscreen: $("#lblFullscreen"),
    btnStartRtsp: $("#btnStartRtsp"),
    btnStopRtsp: $("#btnStopRtsp"),
    rtspUrl: $("#rtspUrl"),
    fileInput: $("#fileInput"),
    cameraControls: $("#cameraControls"),
    rtspControls: $("#rtspControls"),
    uploadControls: $("#uploadControls"),
    identityControls: $("#identityControls"),
    teachControls: $("#teachControls"),
    monitorToolbar: $("#monitorToolbar"),
    chkIdentify: $("#chkIdentify"),
    complianceBox: $("#complianceBox"),
    complianceValue: $("#complianceValue"),
    complianceSummary: $("#complianceSummary"),
    statusPill: $("#statusPill"),
    detList: $("#detList"),
    alertList: $("#alertList"),
    scanList: $("#scanList"),
    speedHint: $("#speedHint"),
    fpsLabel: $("#fpsLabel"),
    workerName: $("#workerName"),
    workerRut: $("#workerRut"),
    btnEnroll: $("#btnEnroll"),
    btnCancelEnroll: $("#btnCancelEnroll"),
    btnIdentify: $("#btnIdentify"),
    identityName: $("#identityName"),
    identityRut: $("#identityRut"),
    identityMethod: $("#identityMethod"),
    workerList: $("#workerList"),
    workerSearch: $("#workerSearch"),
    workerListHint: $("#workerListHint"),
    enrollOverlay: $("#enrollOverlay"),
    enrollPoseTitle: $("#enrollPoseTitle"),
    enrollPoseHint: $("#enrollPoseHint"),
    enrollCount: $("#enrollCount"),
    enrollCoach: $("#enrollCoach"),
    poseProgress: $("#poseProgress"),
    poseBarFill: $("#poseBarFill"),
    poseStepLabel: $("#poseStepLabel"),
    teachClass: $("#teachClass"),
    btnTeachSample: $("#btnTeachSample"),
    btnTeachTrain: $("#btnTeachTrain"),
    btnTeachActivate: $("#btnTeachActivate"),
    teachHint: $("#teachHint"),
    teachStats: $("#teachStats"),
    teachPhotos: $("#teachPhotos"),
    teachVideo: $("#teachVideo"),
    teachNewClass: $("#teachNewClass"),
    btnTeachAddClass: $("#btnTeachAddClass"),
    teachExtraControls: $("#teachExtraControls"),
    teachClassList: $("#teachClassList"),
    faceTrainPhotos: $("#faceTrainPhotos"),
    btnCapturePose: $("#btnCapturePose"),
    btnCapturePoseId: $("#btnCapturePoseId"),
    silZoom: $("#silZoom"),
    silZoomRange: $("#silZoomRange"),
    silZoomLabel: $("#silZoomLabel"),
    btnSilZoomIn: $("#btnSilZoomIn"),
    btnSilZoomOut: $("#btnSilZoomOut"),
    configControls: $("#configControls"),
    cfgSilhouette: $("#cfgSilhouette"),
    cfgSilhouetteGate: $("#cfgSilhouetteGate"),
    cfgFaceGuide: $("#cfgFaceGuide"),
    cfgBodyScale: $("#cfgBodyScale"),
    cfgFaceScale: $("#cfgFaceScale"),
    cfgGuideY: $("#cfgGuideY"),
    cfgBodyScaleVal: $("#cfgBodyScaleVal"),
    cfgFaceScaleVal: $("#cfgFaceScaleVal"),
    cfgGuideYVal: $("#cfgGuideYVal"),
    cfgAutoAdvance: $("#cfgAutoAdvance"),
    cfgPoseAttempts: $("#cfgPoseAttempts"),
    cfgIdentifyDefault: $("#cfgIdentifyDefault"),
    cfgIdThresh: $("#cfgIdThresh"),
    cfgIdThreshVal: $("#cfgIdThreshVal"),
    cfgShowBoxes: $("#cfgShowBoxes"),
    cfgFullscreenDefault: $("#cfgFullscreenDefault"),
    cfgAudioAlerts: $("#cfgAudioAlerts"),
    cfgAudioRepeats: $("#cfgAudioRepeats"),
    cfgAudioRepeatsVal: $("#cfgAudioRepeatsVal"),
    cfgAnonymize: $("#cfgAnonymize"),
    cfgShowZones: $("#cfgShowZones"),
    zonesList: $("#zonesList"),
    zonesHint: $("#zonesHint"),
    btnZoneAdd: $("#btnZoneAdd"),
    btnZoneSave: $("#btnZoneSave"),
    safetyScoreLive: $("#safetyScoreLive"),
    exposureLive: $("#exposureLive"),
    cfgSavedHint: $("#cfgSavedHint"),
    reportsDesk: $("#reportsDesk"),
    reportsContent: $("#reportsContent"),
    repDays: $("#repDays"),
    repProfile: $("#repProfile"),
    btnRepRefresh: $("#btnRepRefresh"),
    repSideSummary: $("#repSideSummary"),
    repSideList: $("#repSideList"),
  };

  let profiles = [];
  let mediaStream = null;
  let camTimer = null;
  let rtspTimer = null;
  let busy = false;
  let sourceMode = "camera";
  let appMode = "monitor";
  let enrollAbort = false;
  let enrolling = false;
  let capturePoseResolver = null;
  let identifyingNow = false;
  let lastIdentifyAt = 0;
  let lastFrameSize = { w: 640, h: 480 };
  let lastIdentity = null;
  let lastFaceBox = null;
  let lastStats = null;
  let currentRep = "overview";
  let notifConfig = null;
  let preferredFacing = "user";

  const isIOS = () =>
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const isAndroid = () => /Android/i.test(navigator.userAgent);
  const isMobile = () =>
    isIOS() ||
    isAndroid() ||
    (/Mobile|Opera Mini|IEMobile/i.test(navigator.userAgent) && window.innerWidth < 980) ||
    (navigator.maxTouchPoints > 1 && window.innerWidth < 980);

  function applyMobileChrome() {
    const mobile = isMobile();
    document.body.classList.toggle("is-mobile", mobile);
    document.body.classList.toggle("is-ios", isIOS());
    document.body.classList.toggle("is-android", isAndroid());
    const hint = $("#speedHint");
    if (mobile) {
      if (els.chkFullscreen) {
        els.chkFullscreen.checked = false;
        settings.fullscreenDefault = false;
      }
      if (hint) {
        hint.textContent = isIOS()
          ? "iPhone/iPad · Safari o “Agregar a inicio”"
          : "Android · podés instalar como app";
      }
    }
    syncViewportHeight();
  }

  function syncViewportHeight() {
    const h = window.visualViewport?.height || window.innerHeight;
    document.documentElement.style.setProperty("--app-vh", `${Math.round(h)}px`);
  }

  const SETTINGS_KEY = "vigiepp.settings.v4";
  const defaultSettings = () => ({
    silhouetteEnabled: true,
    silhouetteGate: true,
    faceGuide: true,
    bodyScale: 100,
    faceScale: 100,
    guideOffsetY: 0,
    autoAdvanceEnroll: true,
    poseAttempts: 8,
    identifyDefault: true,
    showPpeBoxes: false,
    fullscreenDefault: true,
    identifyThreshold: 0.42,
    audioAlerts: true,
    audioAlertRepeats: 0,
    anonymizeFaces: true,
    showZones: true,
    kioskMode: false,
  });
  let settings = defaultSettings();

  function loadSettings() {
    try {
      const raw = localStorage.getItem(SETTINGS_KEY);
      if (!raw) return;
      settings = { ...defaultSettings(), ...JSON.parse(raw) };
      settings.bodyScale = Math.max(55, Math.min(130, Number(settings.bodyScale) || 100));
      settings.faceScale = Math.max(55, Math.min(140, Number(settings.faceScale) || 100));
      settings.guideOffsetY = Math.max(-20, Math.min(20, Number(settings.guideOffsetY) || 0));
      settings.audioAlertRepeats = Math.max(0, Math.min(10, Number(settings.audioAlertRepeats) || 0));
      settings.identifyThreshold = Math.max(
        0.3,
        Math.min(0.65, Number(settings.identifyThreshold) || 0.42)
      );
      // Migrar umbral demo antiguo a modo precisión
      if (settings.identifyThreshold < 0.38) settings.identifyThreshold = 0.42;
    } catch (_) {
      settings = defaultSettings();
    }
  }

  function saveSettings(silent = false) {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    if (silent || !els.cfgSavedHint) return;
    els.cfgSavedHint.textContent = "Guardado · se aplica al instante";
    setTimeout(() => {
      if (els.cfgSavedHint) els.cfgSavedHint.textContent = "Los cambios se guardan en este navegador.";
    }, 1600);
  }

  function syncSettingsForm() {
    if (els.cfgSilhouette) els.cfgSilhouette.checked = !!settings.silhouetteEnabled;
    if (els.cfgSilhouetteGate) els.cfgSilhouetteGate.checked = !!settings.silhouetteGate;
    if (els.cfgFaceGuide) els.cfgFaceGuide.checked = !!settings.faceGuide;
    if (els.cfgBodyScale) els.cfgBodyScale.value = String(settings.bodyScale);
    if (els.cfgFaceScale) els.cfgFaceScale.value = String(settings.faceScale);
    if (els.cfgGuideY) els.cfgGuideY.value = String(settings.guideOffsetY);
    if (els.cfgBodyScaleVal) els.cfgBodyScaleVal.textContent = `${settings.bodyScale}%`;
    if (els.cfgFaceScaleVal) els.cfgFaceScaleVal.textContent = `${settings.faceScale}%`;
    if (els.cfgGuideYVal) els.cfgGuideYVal.textContent = `${settings.guideOffsetY > 0 ? "+" : ""}${settings.guideOffsetY}`;
    if (els.cfgAutoAdvance) els.cfgAutoAdvance.checked = !!settings.autoAdvanceEnroll;
    if (els.cfgPoseAttempts) els.cfgPoseAttempts.value = String(settings.poseAttempts || 8);
    if (els.cfgIdentifyDefault) els.cfgIdentifyDefault.checked = !!settings.identifyDefault;
    if (els.cfgIdThresh) {
      const pct = Math.round((settings.identifyThreshold || 0.42) * 100);
      els.cfgIdThresh.value = String(pct);
      if (els.cfgIdThreshVal) els.cfgIdThreshVal.textContent = `${pct}%`;
    }
    if (els.cfgShowBoxes) els.cfgShowBoxes.checked = !!settings.showPpeBoxes;
    if (els.cfgFullscreenDefault) els.cfgFullscreenDefault.checked = !!settings.fullscreenDefault;
    if (els.cfgAudioAlerts) els.cfgAudioAlerts.checked = !!settings.audioAlerts;
    if (els.cfgAudioRepeats) {
      els.cfgAudioRepeats.value = String(settings.audioAlertRepeats ?? 0);
      if (els.cfgAudioRepeatsVal) {
        const n = Number(settings.audioAlertRepeats) || 0;
        els.cfgAudioRepeatsVal.textContent = n <= 0 ? "sin límite" : String(n);
      }
    }
    if (els.cfgAnonymize) els.cfgAnonymize.checked = !!settings.anonymizeFaces;
    if (els.cfgShowZones) els.cfgShowZones.checked = !!settings.showZones;
    if (els.chkIdentify) els.chkIdentify.checked = !!settings.identifyDefault;
    if (els.chkFullscreen) els.chkFullscreen.checked = !!settings.fullscreenDefault;
  }

  function readSettingsFromForm() {
    settings.silhouetteEnabled = !!els.cfgSilhouette?.checked;
    settings.silhouetteGate = !!els.cfgSilhouetteGate?.checked;
    settings.faceGuide = !!els.cfgFaceGuide?.checked;
    settings.bodyScale = Math.max(55, Math.min(130, Number(els.cfgBodyScale?.value) || 100));
    settings.faceScale = Math.max(55, Math.min(140, Number(els.cfgFaceScale?.value) || 100));
    settings.guideOffsetY = Math.max(-20, Math.min(20, Number(els.cfgGuideY?.value) || 0));
    settings.autoAdvanceEnroll = !!els.cfgAutoAdvance?.checked;
    settings.poseAttempts = Math.max(1, Math.min(20, Number(els.cfgPoseAttempts?.value) || 8));
    settings.identifyDefault = !!els.cfgIdentifyDefault?.checked;
    if (els.cfgIdThresh) {
      settings.identifyThreshold = Math.max(0.3, Math.min(0.65, (Number(els.cfgIdThresh.value) || 42) / 100));
      if (els.cfgIdThreshVal) els.cfgIdThreshVal.textContent = `${Math.round(settings.identifyThreshold * 100)}%`;
    }
    settings.showPpeBoxes = !!els.cfgShowBoxes?.checked;
    settings.fullscreenDefault = !!els.cfgFullscreenDefault?.checked;
    settings.audioAlerts = !!els.cfgAudioAlerts?.checked;
    settings.audioAlertRepeats = Math.max(0, Math.min(10, Number(els.cfgAudioRepeats?.value) || 0));
    if (els.cfgAudioRepeatsVal) {
      els.cfgAudioRepeatsVal.textContent =
        settings.audioAlertRepeats <= 0 ? "sin límite" : String(settings.audioAlertRepeats);
    }
    settings.anonymizeFaces = !!els.cfgAnonymize?.checked;
    settings.showZones = !!els.cfgShowZones?.checked;
    if (els.cfgBodyScaleVal) els.cfgBodyScaleVal.textContent = `${settings.bodyScale}%`;
    if (els.cfgFaceScaleVal) els.cfgFaceScaleVal.textContent = `${settings.faceScale}%`;
    if (els.cfgGuideYVal)
      els.cfgGuideYVal.textContent = `${settings.guideOffsetY > 0 ? "+" : ""}${settings.guideOffsetY}`;
    if (els.chkIdentify) els.chkIdentify.checked = settings.identifyDefault;
    if (els.chkFullscreen) els.chkFullscreen.checked = settings.fullscreenDefault;
    saveSettings();
    applyGuideMode();
  }

  /** body | face según modo y settings */
  function applyGuideMode() {
    const guide = els.silhouetteGuide;
    if (!guide) return;
    // Óvalo facial SOLO en Personas / enrolar — nunca en Monitoreo
    const wantFace = enrolling || appMode === "identity";
    const scanning = document.body.classList.contains("is-scanning") && appMode === "monitor";
    const enabled = !scanning && (!!settings.silhouetteEnabled || wantFace);
    guide.classList.toggle("is-off", !enabled);
    if (els.alignBadge) els.alignBadge.classList.toggle("is-off", !enabled || enrolling || scanning);
    guide.dataset.guide = wantFace ? "face" : "body";
    guide.classList.toggle("enroll-soft", !!enrolling || wantFace);
    guide.style.setProperty("--body-scale", String((settings.bodyScale || 100) / 100));
    guide.style.setProperty("--face-scale", String((settings.faceScale || 100) / 100));
    guide.style.setProperty("--guide-y", `${settings.guideOffsetY || 0}%`);
    if (els.silZoom) els.silZoom.classList.toggle("hidden", scanning || !enabled);
    syncSilZoomUI();
    if (els.silHint) {
      els.silHint.textContent = wantFace
        ? "Encajá tu rostro en el óvalo"
        : "Encajá el cuerpo en la silueta vertical";
    }
  }

  function setCaptureButtonsVisible(show) {
    for (const btn of [els.btnCapturePose, els.btnCapturePoseId]) {
      if (!btn) continue;
      btn.classList.toggle("hidden", !show);
      btn.disabled = !show;
    }
  }

  function waitForCaptureClick() {
    return new Promise((resolve, reject) => {
      if (capturePoseResolver) {
        capturePoseResolver.reject(new Error("Cancelado"));
        capturePoseResolver = null;
      }
      setCaptureButtonsVisible(true);
      capturePoseResolver = {
        resolve: (v) => {
          capturePoseResolver = null;
          setCaptureButtonsVisible(false);
          resolve(v);
        },
        reject: (e) => {
          capturePoseResolver = null;
          setCaptureButtonsVisible(false);
          reject(e);
        },
      };
    });
  }

  function triggerCapturePose() {
    if (capturePoseResolver) capturePoseResolver.resolve(true);
  }

  function cancelWaitingCapture() {
    if (capturePoseResolver) capturePoseResolver.reject(new Error("Cancelado"));
  }

  function syncSilZoomUI() {
    const face = els.silhouetteGuide?.dataset.guide === "face";
    const val = face ? settings.faceScale || 100 : settings.bodyScale || 100;
    if (els.silZoomRange) {
      els.silZoomRange.min = face ? "55" : "55";
      els.silZoomRange.max = face ? "140" : "130";
      els.silZoomRange.value = String(val);
    }
    if (els.silZoomLabel) els.silZoomLabel.textContent = `${val}%`;
    if (els.cfgBodyScale && !face) els.cfgBodyScale.value = String(settings.bodyScale);
    if (els.cfgFaceScale && face) els.cfgFaceScale.value = String(settings.faceScale);
    if (els.cfgBodyScaleVal) els.cfgBodyScaleVal.textContent = `${settings.bodyScale}%`;
    if (els.cfgFaceScaleVal) els.cfgFaceScaleVal.textContent = `${settings.faceScale}%`;
  }

  function setSilhouetteZoom(next) {
    const face = els.silhouetteGuide?.dataset.guide === "face";
    if (face) {
      settings.faceScale = Math.max(55, Math.min(140, Math.round(next / 5) * 5));
    } else {
      settings.bodyScale = Math.max(55, Math.min(130, Math.round(next / 5) * 5));
    }
    saveSettings(true);
    applyGuideMode();
  }

  const POSES = [
    { title: "1/4 Frente", hint: "Mirá de frente a la cámara" },
    { title: "2/4 Izquierda", hint: "Girá la cabeza un poco a tu IZQUIERDA" },
    { title: "3/4 Derecha", hint: "Girá la cabeza un poco a tu DERECHA" },
    { title: "4/4 Mentón", hint: "Levantá un poco el mentón" },
  ];

  const PPE_LABEL = {
    casco: "Casco",
    chaleco: "Chaleco / flúor",
    lentes: "Lentes",
    guantes: "Guantes",
    arnes: "Arnés",
  };

  async function api(path, options = {}, timeoutMs = 20000) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const headers = { ...(options.headers || {}) };
      const token = sessionStorage.getItem("vigiepp.token");
      if (token && !headers["X-VigiEPP-Key"] && !headers.Authorization) {
        headers["X-VigiEPP-Key"] = token;
      }
      const res = await fetch(path, {
        ...options,
        headers,
        credentials: "include",
        signal: ctrl.signal,
      });
      if (res.status === 401 && !path.startsWith("/api/auth/")) {
        sessionStorage.removeItem("vigiepp.token");
        await ensureAuth(true);
        throw new Error("Sesión expirada. Volvé a entrar.");
      }
      const data = await res.json().catch(() => ({}));
      if (!res.ok && res.status !== 202) {
        const detail = data.detail || data.error || `HTTP ${res.status}`;
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      return data;
    } catch (err) {
      if (err.name === "AbortError") throw new Error("Tiempo agotado. Reintentá.");
      throw err;
    } finally {
      clearTimeout(timer);
    }
  }

  function showAuthGate(show, hint = "") {
    const gate = $("#authGate");
    if (!gate) return;
    gate.classList.toggle("hidden", !show);
    document.body.classList.toggle("auth-locked", !!show);
    const h = $("#authHint");
    if (h) h.textContent = hint || "";
    if (show) $("#authPin")?.focus();
  }

  let userRole = "admin";

  function applyRoleUI(role) {
    userRole = role || "admin";
    sessionStorage.setItem("vigiepp.role", userRole);
    document.body.dataset.role = userRole;
    const isOp = userRole === "operator";
    $$(".mode-btn").forEach((b) => {
      const mode = b.dataset.mode;
      const allow = !isOp || mode === "monitor";
      b.classList.toggle("hidden", !allow);
      b.disabled = !allow;
    });
    if (isOp) {
      setAppMode("monitor");
      setKioskMode(true);
    }
    const tag = $(".brand-tag");
    if (tag) tag.textContent = isOp ? "Portería · operador" : "EPP + identidad · Chile";
  }

  async function ensureAuth(force = false) {
    try {
      const st = await fetch("/api/auth/status", { credentials: "include" }).then((r) => r.json());
      if (!st.auth_enabled) {
        showAuthGate(false);
        $("#btnLogout")?.classList.add("hidden");
        applyRoleUI("admin");
        return true;
      }
      if (!force) {
        const me = await fetch("/api/auth/me", {
          credentials: "include",
          headers: sessionStorage.getItem("vigiepp.token")
            ? { "X-VigiEPP-Key": sessionStorage.getItem("vigiepp.token") }
            : {},
        });
        if (me.ok) {
          const data = await me.json().catch(() => ({}));
          showAuthGate(false);
          $("#btnLogout")?.classList.remove("hidden");
          applyRoleUI(data.role || sessionStorage.getItem("vigiepp.role") || "admin");
          return true;
        }
      }
    } catch (_) {
      /* show gate */
    }

    return new Promise((resolve) => {
      showAuthGate(true, "PIN admin o portería (operador)");
      const form = $("#authForm");
      const onSubmit = async (e) => {
        e.preventDefault();
        const pin = $("#authPin")?.value || "";
        const hint = $("#authHint");
        try {
          const res = await fetch("/api/auth/login", {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pin }),
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            if (hint) hint.textContent = data.detail || "PIN incorrecto";
            return;
          }
          if (data.token) sessionStorage.setItem("vigiepp.token", data.token);
          applyRoleUI(data.role || "admin");
          showAuthGate(false);
          $("#btnLogout")?.classList.remove("hidden");
          form?.removeEventListener("submit", onSubmit);
          resolve(true);
        } catch (err) {
          if (hint) hint.textContent = err.message || "Error de red";
        }
      };
      form?.addEventListener("submit", onSubmit);
    });
  }

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  function showLive() {
    els.overlayHint.hidden = true;
    els.annotatedImg.hidden = true;
    els.liveVideo.hidden = false;
    els.overlayCanvas.hidden = false;
    if (mediaStream) els.liveBadge.hidden = false;
  }

  function clearOverlay() {
    const c = els.overlayCanvas;
    const ctx = c.getContext("2d");
    ctx.clearRect(0, 0, c.width, c.height);
  }

  function syncCanvasSize() {
    const canvas = els.overlayCanvas;
    const frame = canvas.parentElement; // .scan-frame
    const rect = frame.getBoundingClientRect();
    canvas.width = Math.max(1, Math.round(rect.width));
    canvas.height = Math.max(1, Math.round(rect.height));
  }

  /** Zona de la silueta en coords del frame vertical (3:4), según porte configurado. */
  function guideRect(frameW, frameH) {
    const face = els.silhouetteGuide?.dataset.guide === "face";
    const scale = ((face ? settings.faceScale : settings.bodyScale) || 100) / 100;
    const yOff = ((settings.guideOffsetY || 0) / 100) * frameH;
    const cx = frameW * 0.5;
    const cy = (face ? frameH * 0.36 : frameH * 0.5) + yOff;
    const halfW = frameW * (face ? 0.26 : 0.3) * scale;
    const halfH = frameH * (face ? 0.26 : 0.455) * scale;
    return {
      x1: Math.max(0, cx - halfW),
      y1: Math.max(0, cy - halfH),
      x2: Math.min(frameW, cx + halfW),
      y2: Math.min(frameH, cy + halfH),
    };
  }

  function overlapRatio(box, guide) {
    const [x1, y1, x2, y2] = box;
    const ix1 = Math.max(x1, guide.x1);
    const iy1 = Math.max(y1, guide.y1);
    const ix2 = Math.min(x2, guide.x2);
    const iy2 = Math.min(y2, guide.y2);
    const inter = Math.max(0, ix2 - ix1) * Math.max(0, iy2 - iy1);
    const area = Math.max(1, (x2 - x1) * (y2 - y1));
    return inter / area;
  }

  function faceGuideActive() {
    return enrolling || identifyingNow || appMode === "identity";
  }

  function setAlignment(state, text) {
    if (!settings.silhouetteEnabled && !faceGuideActive() && !(settings.faceGuide && appMode === "monitor")) {
      if (els.alignBadge) {
        els.alignBadge.dataset.state = "idle";
        els.alignBadge.textContent = "Guía off";
      }
      return;
    }
    if (enrolling) return; // overlay de poses maneja el coaching
    if (els.alignBadge) {
      els.alignBadge.dataset.state = state;
      els.alignBadge.textContent = text;
    }
    if (els.silhouetteGuide) {
      els.silhouetteGuide.classList.toggle("aligned", state === "ok");
      els.silhouetteGuide.classList.toggle("bad", state === "bad");
    }
    if (els.silHint) {
      const face = els.silhouetteGuide?.dataset.guide === "face";
      els.silHint.textContent =
        state === "ok"
          ? face
            ? "Rostro encajado · listo"
            : "Perfecto — cuerpo encajado · escaneando EPP"
          : state === "bad"
            ? face
              ? "Centrá la cara en el óvalo"
              : "Acercate / centrate en la silueta vertical"
            : face
              ? "Encajá tu rostro en el óvalo"
              : "Encajá tu cuerpo en la silueta (lectura vertical)";
    }
  }

  function evaluateAlignment(detections, frameW, frameH) {
    const guideActive =
      settings.silhouetteEnabled || faceGuideActive() || (!!settings.faceGuide && appMode === "monitor");
    if (!guideActive) {
      setAlignment("idle", "Guía off");
      return true; // no bloquea
    }
    if (enrolling) return true;
    const guide = guideRect(frameW, frameH);
    const boxes = (detections || []).map((d) => d.box);
    if (!boxes.length) {
      setAlignment("idle", els.silhouetteGuide?.dataset.guide === "face" ? "Mirá a la cámara" : "Posicionate en la silueta");
      return false;
    }
    // Usa la caja más grande (persona o torso/EPP)
    const biggest = boxes.reduce((a, b) => {
      const aa = (a[2] - a[0]) * (a[3] - a[1]);
      const bb = (b[2] - b[0]) * (b[3] - b[1]);
      return bb > aa ? b : a;
    });
    const ratio = overlapRatio(biggest, guide);
    const faceMode = els.silhouetteGuide?.dataset.guide === "face";
    const boxH = (biggest[3] - biggest[1]) / frameH;
    // Cuerpo: exige persona alta en el frame. Rostro: basta con caja facial.
    const tallEnough = faceMode ? boxH >= 0.12 : boxH >= 0.48;
    const needRatio = faceMode ? 0.4 : 0.55;
    if (ratio >= needRatio && tallEnough) {
      setAlignment("ok", "Encaje correcto");
      return true;
    }
    if (ratio >= (faceMode ? 0.18 : 0.25)) {
      setAlignment("bad", "Ajusta la posición");
      return false;
    }
    setAlignment("bad", faceMode ? "Centrá el rostro" : "Entra en la silueta");
    return false;
  }

  function drawFaceBox(ctx, faceBox, frameW, frameH, cover) {
    if (!faceBox || faceBox.length < 4) return;
    const [x1, y1, x2, y2] = faceBox;
    const sx = cover.w / frameW;
    const sy = cover.h / frameH;
    const cx = cover.ox + ((x1 + x2) / 2) * sx;
    const cy = cover.oy + ((y1 + y2) / 2) * sy;
    const rx = Math.max(12, ((x2 - x1) * sx) / 2);
    const ry = Math.max(16, ((y2 - y1) * sy) / 2);
    ctx.save();
    ctx.strokeStyle = "rgba(238, 243, 239, 0.45)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx * 1.05, ry * 1.15, 0, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }


  let lastSpeakAt = 0;
  let speakKey = "";
  let speakCount = 0;
  const SPEAK_GAP_MS = 5500;
  let zonesCache = [];
  let lastAccessAllow = null;

  function resetSpeakIncident() {
    speakKey = "";
    speakCount = 0;
  }

  function speakAlert(text) {
    if (!settings.audioAlerts) return;
    if (!window.speechSynthesis) return;
    const key = String(text || "").slice(0, 140).trim();
    if (!key) return;
    const now = Date.now();
    if (key !== speakKey) {
      speakKey = key;
      speakCount = 0;
    }
    const maxRepeats = Math.max(0, Math.min(10, Number(settings.audioAlertRepeats) || 0));
    // 0 = sin límite (se repite mientras dure el incumplimiento, con pausa entre avisos)
    if (maxRepeats > 0 && speakCount >= maxRepeats) return;
    if (speakCount > 0 && now - lastSpeakAt < SPEAK_GAP_MS) return;
    speakCount += 1;
    lastSpeakAt = now;
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(key);
      u.lang = "es-CL";
      u.rate = 1.05;
      window.speechSynthesis.speak(u);
    } catch (_) {}
  }

  function blurFaceOnCanvas(ctx, faceBox, frameW, frameH, cover) {
    if (!faceBox || !settings.anonymizeFaces) return;
    const [x1, y1, x2, y2] = faceBox;
    const sx = cover.w / frameW;
    const sy = cover.h / frameH;
    const rx = cover.ox + x1 * sx;
    const ry = cover.oy + y1 * sy;
    const rw = Math.max(8, (x2 - x1) * sx);
    const rh = Math.max(8, (y2 - y1) * sy);
    ctx.fillStyle = "rgba(12, 16, 14, 0.72)";
    ctx.fillRect(rx, ry, rw, rh);
    ctx.strokeStyle = "rgba(255,255,255,0.18)";
    ctx.strokeRect(rx + 0.5, ry + 0.5, rw, rh);
    ctx.font = "600 10px Source Sans 3, sans-serif";
    ctx.fillStyle = "rgba(238,243,239,0.75)";
    ctx.fillText("Privado", rx + 6, ry + Math.min(14, rh - 4));
  }

  function drawZonesOverlay(ctx, frameW, frameH, cover, hits) {
    if (!settings.showZones || !zonesCache.length) return;
    const sx = cover.w / frameW;
    const sy = cover.h / frameH;
    for (const z of zonesCache) {
      if (!z.enabled) continue;
      const rx = cover.ox + z.x * frameW * sx;
      const ry = cover.oy + z.y * frameH * sy;
      const rw = z.w * frameW * sx;
      const rh = z.h * frameH * sy;
      const hit = (hits || []).some((h) => h.zone_id === z.id);
      ctx.fillStyle = hit ? "rgba(214,40,40,0.18)" : "rgba(232,93,4,0.08)";
      ctx.strokeStyle = hit ? "rgba(214,40,40,0.85)" : (z.color || "rgba(232,93,4,0.7)");
      ctx.lineWidth = hit ? 2 : 1.25;
      ctx.setLineDash(z.type === "vehicle_lane" ? [6, 4] : []);
      ctx.fillRect(rx, ry, rw, rh);
      ctx.strokeRect(rx, ry, rw, rh);
      ctx.setLineDash([]);
      ctx.font = "600 11px Source Sans 3, sans-serif";
      ctx.fillStyle = "rgba(238,243,239,0.9)";
      const label = z.type === "vehicle_lane" ? `Vía · ${z.name}` : `Zona · ${z.name}`;
      ctx.fillText(label, rx + 6, ry + 14);
    }
  }

  async function loadZones() {
    try {
      const data = await api("/api/zones");
      zonesCache = data.zones || [];
      renderZonesEditor();
    } catch (err) {
      if (els.zonesHint) els.zonesHint.textContent = err.message;
    }
  }

  function renderZonesEditor() {
    if (!els.zonesList) return;
    els.zonesList.innerHTML = (zonesCache || [])
      .map(
        (z, i) => `<div class="zone-row" data-zi="${i}">
          <label class="check"><input type="checkbox" data-z="en" ${z.enabled ? "checked" : ""}/> On</label>
          <input data-z="name" value="${String(z.name || "").replace(/"/g, "&quot;")}" placeholder="Nombre"/>
          <select data-z="type">
            <option value="restricted" ${z.type !== "vehicle_lane" ? "selected" : ""}>Restringida</option>
            <option value="vehicle_lane" ${z.type === "vehicle_lane" ? "selected" : ""}>Vía vehículos</option>
          </select>
          <span class="zone-sliders">
            x<input data-z="x" type="range" min="0" max="90" value="${Math.round((z.x || 0) * 100)}"/>
            y<input data-z="y" type="range" min="0" max="90" value="${Math.round((z.y || 0) * 100)}"/>
            w<input data-z="w" type="range" min="10" max="90" value="${Math.round((z.w || 0.2) * 100)}"/>
            h<input data-z="h" type="range" min="10" max="90" value="${Math.round((z.h || 0.2) * 100)}"/>
          </span>
          <button type="button" class="btn-mini danger" data-z-del="${i}">X</button>
        </div>`
      )
      .join("") || "<p class='muted'>Sin zonas</p>";
  }

  function readZonesFromEditor() {
    if (!els.zonesList) return zonesCache;
    return [...els.zonesList.querySelectorAll(".zone-row")].map((row, i) => {
      const prev = zonesCache[i] || {};
      return {
        id: prev.id || `zona-${Date.now()}-${i}`,
        name: row.querySelector('[data-z="name"]')?.value || "Zona",
        type: row.querySelector('[data-z="type"]')?.value || "restricted",
        enabled: !!row.querySelector('[data-z="en"]')?.checked,
        x: (Number(row.querySelector('[data-z="x"]')?.value) || 0) / 100,
        y: (Number(row.querySelector('[data-z="y"]')?.value) || 0) / 100,
        w: (Number(row.querySelector('[data-z="w"]')?.value) || 20) / 100,
        h: (Number(row.querySelector('[data-z="h"]')?.value) || 20) / 100,
        color: prev.color || "#e85d04",
      };
    });
  }

  function drawDetections(detections, frameW, frameH, identity, zoneHits) {
    syncCanvasSize();
    const canvas = els.overlayCanvas;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const cover = videoCoverSize(frameW, frameH, canvas.width, canvas.height);
    const sx = cover.w / frameW;
    const sy = cover.h / frameH;

    evaluateAlignment(detections, frameW, frameH);
    drawZonesOverlay(ctx, frameW, frameH, cover, zoneHits || []);

    // Monitoreo limpio: las faltas van al panel — no cajas rojas sobre la cara
    const drawBoxes = settings.showPpeBoxes && appMode === "monitor";
    if (drawBoxes) {
      const badOnly = (detections || [])
        .filter((d) => {
          const l = String(d.label_es || d.label).toLowerCase();
          return l.startsWith("sin") || l.startsWith("no") || l.includes("fall");
        })
        .sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
        .slice(0, 1);

      for (const d of badOnly) {
        const [x1, y1, x2, y2] = d.box;
        const rx = cover.ox + x1 * sx;
        const ry = cover.oy + y1 * sy;
        const rw = (x2 - x1) * sx;
        const rh = (y2 - y1) * sy;
        ctx.strokeStyle = "rgba(214, 90, 70, 0.45)";
        ctx.lineWidth = 1.25;
        ctx.strokeRect(rx + 0.5, ry + 0.5, rw, rh);
        let label = String(d.label_es || d.label).replace(/\s+/g, " ").trim();
        if (label.length > 18) label = `${label.slice(0, 16)}…`;
        ctx.font = "600 11px Source Sans 3, sans-serif";
        const tw = ctx.measureText(label).width + 10;
        ctx.fillStyle = "rgba(10, 14, 12, 0.65)";
        ctx.fillRect(rx, Math.max(0, ry - 16), tw, 16);
        ctx.fillStyle = "rgba(240, 210, 200, 0.9)";
        ctx.fillText(label, rx + 5, Math.max(11, ry - 4));
      }
    }

    const faceBox = identity?.face_box || lastFaceBox;
    // Anonimizar: difuminar rostros desconocidos en monitoreo
    if (
      faceBox &&
      settings.anonymizeFaces &&
      appMode === "monitor" &&
      !(identity && identity.known)
    ) {
      blurFaceOnCanvas(ctx, faceBox, frameW, frameH, cover);
    }
    // Óvalo facial solo en enrolar / Personas
    if (faceBox && (enrolling || appMode === "identity")) {
      drawFaceBox(ctx, faceBox, frameW, frameH, cover);
    }
  }

  function videoCoverSize(srcW, srcH, dstW, dstH) {
    const scale = Math.max(dstW / srcW, dstH / srcH);
    const w = srcW * scale;
    const h = srcH * scale;
    return { w, h, ox: (dstW - w) / 2, oy: (dstH - h) / 2 };
  }

  function videoContainSize(srcW, srcH, dstW, dstH) {
    const scale = Math.min(dstW / srcW, dstH / srcH);
    return { w: srcW * scale, h: srcH * scale };
  }

  async function boot() {
    await ensureAuth();
    try {
      const health = await api("/api/health");
      els.modelStatus.classList.toggle("ready", !!health.model_ready);
      els.modelStatus.classList.toggle("error", !health.model_ready);
      els.modelStatusText.textContent = health.model_ready
        ? `IA lista · ${health.model || "EPP"}`
        : health.warning || "Cargando";
      showPersistBanner(health);
    } catch {
      els.modelStatus.classList.add("error");
      els.modelStatusText.textContent = "Backend no disponible";
    }

    try {
      profiles = await api("/api/profiles");
      els.profileSelect.innerHTML = profiles
        .map((p) => `<option value="${p.id}">${p.name}</option>`)
        .join("");
      els.profileSelect.value = "portuario";
      renderProfile();
    } catch (err) {
      console.error(err);
    }

    await refreshWorkers();
    await refreshTeach();
    await refreshScans();
    await loadZones();
    loadSettings();
    if (isMobile()) {
      settings.fullscreenDefault = false;
    }
    syncSettingsForm();
    applyMobileChrome();
    applyGuideMode();
    setAppMode("monitor");
    if (settings.kioskMode) setKioskMode(true);
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/assets/sw.js").catch(() => {});
    }
    const offlineBadge = $("#offlineBadge");
    const syncOffline = () => {
      if (!offlineBadge) return;
      offlineBadge.classList.toggle("hidden", navigator.onLine);
      offlineBadge.textContent = navigator.onLine ? "" : "Sin red · modo local";
    };
    syncOffline();
    window.addEventListener("online", syncOffline);
    window.addEventListener("offline", syncOffline);
    window.addEventListener("orientationchange", () => {
      setTimeout(() => {
        syncViewportHeight();
        syncCanvasSize();
        applyGuideMode();
      }, 250);
    });
    window.visualViewport?.addEventListener("resize", () => {
      syncViewportHeight();
      syncCanvasSize();
    });
    window.addEventListener("resize", syncViewportHeight);
  }

  function renderProfile() {
    const p = profiles.find((x) => x.id === els.profileSelect.value);
    if (!p) return;
    els.profileDesc.textContent = p.name;
    const req = (p.required || []).map((k) => `<span class="chip">${PPE_LABEL[k] || k}</span>`);
    const opt = (p.optional || []).map(
      (k) => `<span class="chip optional">${PPE_LABEL[k] || k}</span>`
    );
    els.requiredChips.innerHTML = [...req, ...opt].join("") || "—";
  }

  function setAppMode(mode) {
    appMode = mode;
    document.body.classList.remove(
      "mode-monitor",
      "mode-identity",
      "mode-teach",
      "mode-config",
      "mode-reports"
    );
    document.body.classList.add(`mode-${mode}`);
    $$(".mode-btn").forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
    els.monitorToolbar.classList.toggle("hidden", mode !== "monitor");
    const stage = $(".stage");
    if (stage) stage.classList.toggle("is-reports", mode === "reports");
    if (els.reportsDesk) els.reportsDesk.classList.toggle("hidden", mode !== "reports");
    const panel = $("#sidePanel");
    if (panel) panel.dataset.mode = mode;
    const ctx = $("#panelContext");
    if (ctx) {
      ctx.textContent =
        mode === "monitor"
          ? "Resultado del escaneo en vivo"
          : mode === "identity"
            ? "Enrolar e identificar personas"
            : mode === "teach"
              ? "Entrenar ropa y EPP del modelo"
              : mode === "reports"
                ? "Estadísticas, informes y notificaciones"
                : "Ajustes de silueta, rostro y monitoreo";
    }
    if (mode === "monitor")
      setSource(
        sourceMode === "identity" || sourceMode === "teach" || sourceMode === "config" || sourceMode === "reports"
          ? "camera"
          : sourceMode
      );
    else if (mode === "identity") setSource("identity");
    else if (mode === "teach") setSource("teach");
    else if (mode === "reports") setSource("reports");
    else setSource("config");
    applyGuideMode();
    if (mode === "identity") refreshWorkers();
    if (mode === "teach") refreshTeach();
    if (mode === "config") loadZones();
    if (mode === "reports") {
      fillRepProfiles();
      openReport(currentRep || "overview");
    }
    requestAnimationFrame(() => syncCanvasSize());
  }

  function setSource(mode) {
    sourceMode = mode;
    $$(".tab").forEach((t) => {
      if (t.dataset.source) t.classList.toggle("active", t.dataset.source === mode);
    });
    const showCamBar = mode === "camera" || mode === "identity" || mode === "teach";
    els.cameraControls.classList.toggle("hidden", !showCamBar);
    els.rtspControls.classList.toggle("hidden", mode !== "rtsp");
    els.uploadControls.classList.toggle("hidden", mode !== "upload");
    els.identityControls.classList.toggle("hidden", mode !== "identity");
    if (els.teachControls) els.teachControls.classList.toggle("hidden", mode !== "teach");
    if (els.teachExtraControls) els.teachExtraControls.classList.toggle("hidden", mode !== "teach");
    if (els.configControls) els.configControls.classList.toggle("hidden", mode !== "config");

    // En Personas: ocultar toggles de monitoreo (identificar / fullscreen)
    if (els.chkIdentify?.closest?.("label")) {
      const idLabel = els.chkIdentify.closest("label");
      idLabel.classList.toggle("hidden", mode === "identity" || mode === "teach");
    }
    if (els.chkFullscreen?.closest?.("label")) {
      const fsLabel = els.chkFullscreen.closest("label") || $("#lblFullscreen");
      if (fsLabel) fsLabel.classList.toggle("hidden", mode === "identity" || mode === "teach");
    }
    if (els.speedHint) {
      els.speedHint.classList.toggle("hidden", mode === "identity" || mode === "teach");
      if (mode === "camera") els.speedHint.textContent = "Lectura vertical · cuerpo completo";
      else if (mode === "identity") els.speedHint.textContent = "Guía facial · 4 poses";
      else if (mode === "teach") els.speedHint.textContent = "Foto o video de la prenda";
    }

    if (mode === "identity" || mode === "teach") {
      stopDetectLoop();
      if (!mediaStream) startCamera({ silentDetect: true });
      else showLive();
      // Limpiar resultado EPP residual del monitoreo
      if (els.complianceBox) els.complianceBox.dataset.state = "idle";
      if (els.complianceValue) els.complianceValue.textContent = mode === "identity" ? "Enrolamiento" : "Entrenamiento";
      if (els.complianceSummary) {
        els.complianceSummary.textContent =
          mode === "identity"
            ? "Registrá el rostro acá. El EPP se evalúa en Monitoreo."
            : "Enseñá prendas acá. El cumplimiento se ve en Monitoreo.";
      }
      if (els.statusPill) els.statusPill.textContent = "Modo entrenamiento";
      if (els.detList) els.detList.innerHTML = `<li class="muted">Sin escaneo EPP en este modo</li>`;
      if (els.alertList) els.alertList.innerHTML = `<li class="muted">Sin alertas de faena</li>`;
    } else if (mode === "config") {
      stopDetectLoop();
      showLive();
    } else if (mode === "reports") {
      stopDetectLoop();
    } else if (mode === "camera") {
      stopRtsp();
    } else if (mode === "rtsp") {
      stopCamera();
    } else {
      stopDetectLoop();
    }

    if (mode === "identity" && els.enrollCoach) {
      els.enrollCoach.textContent = "4 poses de calidad obligatorias · luz frontal · una persona";
    }
    applyGuideMode();
  }

  function updateUi(payload) {
    if (!payload || !payload.ok) return;
    const t0 = performance.now();

    if (payload.frame_width && payload.frame_height) {
      lastFrameSize = { w: payload.frame_width, h: payload.frame_height };
    }

    if (payload.identity?.face_box) lastFaceBox = payload.identity.face_box;

    // Preferir video vivo + canvas (rápido). Solo usar imagen si viene y no hay video.
    if (payload.image_b64 && !mediaStream) {
      els.overlayHint.hidden = true;
      els.liveVideo.hidden = true;
      els.overlayCanvas.hidden = true;
      els.annotatedImg.hidden = false;
      els.annotatedImg.src = `data:image/jpeg;base64,${payload.image_b64}`;
    } else {
      showLive();
      drawDetections(
        payload.detections,
        lastFrameSize.w,
        lastFrameSize.h,
        payload.identity || lastIdentity,
        payload.zones?.hits || []
      );
    }

    if (payload.zones?.defs) zonesCache = payload.zones.defs;

    const gateOn = !!settings.silhouetteGate && !!settings.silhouetteEnabled && appMode === "monitor";
    const aligned = gateOn
      ? evaluateAlignment(payload.detections || [], lastFrameSize.w, lastFrameSize.h)
      : true;

    const c = payload.compliance || {};
    const ok = !!c.overall_compliant;
    const hasPeople = (c.persons || []).length > 0 || (payload.detections || []).length > 0;
    if (gateOn && !aligned && hasPeople) {
      els.complianceBox.dataset.state = "bad";
      els.complianceValue.textContent = "Fuera de silueta";
      els.complianceSummary.textContent =
        "Encajá el cuerpo completo en la guía vertical para validar EPP e identidad.";
    } else {
      els.complianceBox.dataset.state = hasPeople ? (ok ? "ok" : "bad") : "idle";
      els.complianceValue.textContent = !hasPeople ? "Sin persona" : ok ? "Cumple" : "No cumple";
      els.complianceSummary.textContent = c.summary || "—";
    }
    const pill = $("#statusPill");
    if (pill) {
      if (gateOn && !aligned && hasPeople) pill.textContent = "Fuera";
      else if (!hasPeople) pill.textContent = "Standby";
      else pill.textContent = ok ? "OK" : "Alerta";
    }
    updateKioskBanner(payload);

    if (els.safetyScoreLive) {
      els.safetyScoreLive.textContent =
        payload.safety_score != null ? `Safety Score · ${payload.safety_score}/100` : "";
    }
    if (els.exposureLive) {
      const ex = payload.exposure;
      if (ex && (ex.active || ex.seconds > 0)) {
        els.exposureLive.textContent = ex.active
          ? `Sin EPP · ${ex.label}`
          : `Exposición acumulada · ${ex.label}`;
      } else {
        els.exposureLive.textContent = "";
      }
    }

    // Audio en piso — máx. 2 veces por incumplimiento; se reinicia al cumplir / sin persona
    if (appMode === "monitor" && hasPeople && !ok) {
      const zoneAlert = (payload.zones?.alerts || [])[0];
      const miss = (c.persons?.[0]?.missing || []).slice(0, 2).join(" y ");
      if (zoneAlert) speakAlert(zoneAlert.replace("Near-miss:", "Cuidado.").replace("Zona restringida:", "Zona restringida."));
      else if (miss) speakAlert(`Falta ${miss}. Ponete el equipo de protección.`);
      else speakAlert("No cumple. Revisá tu EPP.");
    } else if (ok || !hasPeople) {
      resetSpeakIncident();
      try {
        if (window.speechSynthesis?.speaking) window.speechSynthesis.cancel();
      } catch (_) {}
    }
    if (payload.access && payload.access.allow !== lastAccessAllow) {
      lastAccessAllow = payload.access.allow;
      speakAlert(payload.access.allow ? "Acceso permitido" : "Acceso denegado");
    }

    const dets = payload.detections || [];
    els.detList.innerHTML = dets.length
      ? dets
          .map(
            (d) =>
              `<li><span>${d.label_es || d.label}</span><span class="conf">${Math.round(
                d.confidence * 100
              )}%</span></li>`
          )
          .join("")
      : `<li class="muted">Sin detecciones en este frame</li>`;

    const alerts = c.alerts || [];
    // Si hay identidad conocida, personalizar alerta
    const id = payload.identity || lastIdentity;
    els.alertList.innerHTML = alerts.length
      ? alerts
          .map((a) => {
            const who = id?.known && id?.name ? `${id.name}: ` : "";
            return `<li class="warn">${who}${a}</li>`;
          })
          .join("")
      : `<li class="muted">Sin alertas</li>`;

    if (payload.identity) {
      lastIdentity = payload.identity;
      setIdentityCard(payload.identity);
      if (payload.identity.faces_detected > 0 && settings.faceGuide && appMode === "monitor") {
        identifyingNow = true;
        applyGuideMode();
        clearTimeout(window.__vigieppFaceGuideTimer);
        window.__vigieppFaceGuideTimer = setTimeout(() => {
          if (!enrolling) {
            identifyingNow = false;
            applyGuideMode();
          }
        }, 2800);
      }
    }

    const ms = Math.round(performance.now() - t0);
    els.fpsLabel.textContent = `${ms} ms UI`;
  }

  function setIdentityCard(identity) {
    if (!identity) {
      els.identityName.textContent = "Sin identificar";
      els.identityRut.textContent = "Enrola personas en Enrolar personas";
      els.identityMethod.textContent = "";
      els.personChip.classList.add("hidden");
      return;
    }
    const known = !!identity.known;
    els.identityName.textContent = identity.name || (known ? "—" : "Desconocido");
    els.identityRut.textContent =
      identity.rut && !String(identity.rut).startsWith("SIN-RUT")
        ? `RUT ${identity.rut}`
        : known
          ? "Sin RUT"
          : "No está en el registro";
    const score =
      identity.score != null ? `${Math.round(Number(identity.score) * 100)}%` : null;
    const confMap = {
      high: "confianza alta",
      medium: "confianza media",
      low: "confianza baja",
      ambiguous: "ambigüedad",
      none: "",
    };
    const confTxt = confMap[identity.confidence] || "";
    if (known) {
      els.identityMethod.textContent = [
        "Rostro reconocido",
        score,
        confTxt,
      ]
        .filter(Boolean)
        .join(" · ");
    } else if (identity.faces_detected) {
      const why = identity.reject_reason || "sin match estricto";
      els.identityMethod.textContent = [
        "No identificado",
        score,
        why,
      ]
        .filter(Boolean)
        .join(" · ");
    } else {
      els.identityMethod.textContent = "Sin rostro detectado";
    }

    els.personChip.classList.remove("hidden");
    els.personChip.classList.toggle("unknown", !known);
    els.personChipName.textContent = els.identityName.textContent;
    els.personChipRut.textContent = els.identityRut.textContent;
  }

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
      fd.append("imgsz", "416");
      fd.append("threshold", String(settings.identifyThreshold || 0.42));
      const data = await api("/api/detect", { method: "POST", body: fd }, 15000);
      updateUi(data);
      if (identify && data.identity?.known) refreshScans();
      els.fpsLabel.textContent = `${Math.round(performance.now() - t0)} ms IA`;
    } catch (err) {
      console.error(err);
      els.fpsLabel.textContent = "error";
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

  async function tickDetect() {
    if (appMode !== "monitor" || sourceMode !== "camera") return;
    const blob = await captureBlob(isMobile() ? 0.58 : 0.65, isMobile() ? 480 : 640);
    if (!blob) return;
    const wantId = !!els.chkIdentify?.checked;
    const now = Date.now();
    // Identificar cada ~2.2s para no frenar el EPP (móvil un poco más lento)
    const idGap = isMobile() ? 2800 : 2200;
    const identify = wantId && now - lastIdentifyAt > idGap;
    if (identify) lastIdentifyAt = now;
    await detectBlob(blob, { identify, returnImage: false });
  }

  function stopDetectLoop() {
    if (camTimer) {
      clearInterval(camTimer);
      camTimer = null;
    }
  }

  function enterFullscreen() {
    const root = document.documentElement;
    const req =
      root.requestFullscreen ||
      root.webkitRequestFullscreen ||
      root.msRequestFullscreen;
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

  async function startCamera(opts = {}) {
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("Este navegador no permite cámara. Usá Chrome/Safari actualizado por HTTPS.");
      }
      if (!mediaStream) {
        mediaStream = await openCameraStream(preferredFacing);
        els.liveVideo.setAttribute("playsinline", "");
        els.liveVideo.setAttribute("webkit-playsinline", "");
        els.liveVideo.muted = true;
        els.liveVideo.srcObject = mediaStream;
        try {
          await els.liveVideo.play();
        } catch (_) {}
      }
      showLive();
      els.btnStartCam.disabled = true;
      els.btnStopCam.disabled = false;
      if (els.btnFlipCam) els.btnFlipCam.disabled = false;
      stopDetectLoop();
      if (!opts.silentDetect && appMode === "monitor" && sourceMode === "camera") {
        const canFs = !isIOS() && !!els.chkFullscreen?.checked;
        if (canFs && !isFullscreen()) {
          await enterFullscreen();
        }
        document.body.classList.add("is-scanning");
        applyGuideMode();
        camTimer = setInterval(tickDetect, isMobile() ? 1100 : 900);
        tickDetect();
      }
    } catch (err) {
      console.error(err);
      els.overlayHint.hidden = false;
      const msg = String(err?.message || err || "");
      let tip = "No se pudo acceder a la cámara. Revisá permisos del navegador.";
      if (/NotAllowed|Permission|denied/i.test(msg)) {
        tip = isIOS()
          ? "Permiso denegado. En Ajustes → Safari → Cámara, permití acceso y recargá."
          : "Permiso denegado. Tocá el candado de la URL y permití la cámara.";
      } else if (/NotFound|DevicesNotFound/i.test(msg)) {
        tip = "No hay cámara disponible en este dispositivo.";
      } else if (/secure|HTTPS|getUserMedia/i.test(msg)) {
        tip = msg;
      }
      els.overlayHint.querySelector("p").textContent = tip;
    }
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

  async function flipCamera() {
    preferredFacing = preferredFacing === "user" ? "environment" : "user";
    if (mediaStream) {
      mediaStream.getTracks().forEach((t) => t.stop());
      mediaStream = null;
      els.liveVideo.srcObject = null;
    }
    const wasScanning = !!camTimer;
    stopDetectLoop();
    try {
      mediaStream = await openCameraStream(preferredFacing);
      els.liveVideo.srcObject = mediaStream;
      await els.liveVideo.play().catch(() => {});
      showLive();
      els.btnStartCam.disabled = true;
      els.btnStopCam.disabled = false;
      if (wasScanning && appMode === "monitor" && sourceMode === "camera") {
        document.body.classList.add("is-scanning");
        applyGuideMode();
        camTimer = setInterval(tickDetect, isMobile() ? 1100 : 900);
        tickDetect();
      }
      const hint = $("#speedHint");
      if (hint) {
        hint.textContent = preferredFacing === "user" ? "Cámara frontal" : "Cámara trasera";
      }
    } catch (err) {
      preferredFacing = preferredFacing === "user" ? "environment" : "user";
      els.overlayHint.hidden = false;
      els.overlayHint.querySelector("p").textContent =
        "No se pudo cambiar de cámara en este dispositivo.";
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
    els.liveVideo.srcObject = null;
    els.btnStartCam.disabled = false;
    els.btnStopCam.disabled = true;
    els.liveBadge.hidden = true;
    clearOverlay();
    els.personChip.classList.add("hidden");
    els.overlayHint.hidden = false;
    els.overlayHint.querySelector("p").textContent =
      "Activa la cámara y encajá en la silueta vertical";
    setAlignment("idle", "Posicionate");
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
    if (els.chkFullscreen?.checked && !isIOS() && !isFullscreen()) {
      await enterFullscreen();
    }
    document.body.classList.add("is-scanning");
    applyGuideMode();
    const poll = async () => {
      const wantId = !!els.chkIdentify?.checked && Date.now() - lastIdentifyAt > 2200;
      if (wantId) lastIdentifyAt = Date.now();
      const q = new URLSearchParams({
        url,
        profile: els.profileSelect.value,
        conf: "0.35",
        identify: String(wantId),
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

  let workersCache = [];
  let workerFilter = "active"; // active | all | inactive

  function formatLastSeen(iso) {
    if (!iso) return "Nunca visto";
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return "Nunca visto";
      const diff = (Date.now() - d.getTime()) / 1000;
      if (diff < 90) return "Ahora";
      if (diff < 3600) return `Hace ${Math.round(diff / 60)} min`;
      if (diff < 86400) return `Hace ${Math.round(diff / 3600)} h`;
      return d.toLocaleString("es-CL", { dateStyle: "short", timeStyle: "short" });
    } catch (_) {
      return "Nunca visto";
    }
  }

  function qualityLabel(q, ready) {
    if (ready === false) return "NO LISTO";
    const n = Number(q) || 0;
    if (n >= 85) return "Alta";
    if (n >= 60) return "Media";
    if (n > 0) return "Baja";
    return "Sin fotos";
  }

  async function refreshWorkers() {
    try {
      workersCache = await api("/api/identity/workers");
      if (!workersCache.length) {
        const restored = await restoreBrowserBackupIfServerEmpty();
        if (restored) {
          workersCache = await api("/api/identity/workers");
          if (els.enrollCoach) {
            els.enrollCoach.textContent =
              "Se restauró el respaldo de este navegador (Render Free borra el disco al dormir).";
          }
        }
      } else {
        scheduleBrowserBackup();
      }
      renderWorkerList();
    } catch (err) {
      console.error(err);
      if (els.workerListHint) els.workerListHint.textContent = "No se pudo cargar la lista";
    }
  }

  const IDB_NAME = "vigiepp-persist";
  const IDB_STORE = "backups";
  const IDB_KEY = "identity-latest";
  let browserBackupTimer = null;

  function idbOpen() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(IDB_NAME, 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(IDB_STORE)) db.createObjectStore(IDB_STORE);
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function saveBrowserBackupBlob(blob) {
    const db = await idbOpen();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(IDB_STORE, "readwrite");
      tx.objectStore(IDB_STORE).put({ blob, savedAt: Date.now(), bytes: blob.size }, IDB_KEY);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  }

  async function loadBrowserBackupBlob() {
    const db = await idbOpen();
    const row = await new Promise((resolve, reject) => {
      const tx = db.transaction(IDB_STORE, "readonly");
      const req = tx.objectStore(IDB_STORE).get(IDB_KEY);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error);
    });
    db.close();
    return row;
  }

  function scheduleBrowserBackup() {
    if (browserBackupTimer) clearTimeout(browserBackupTimer);
    browserBackupTimer = setTimeout(() => {
      syncBrowserBackupFromServer().catch(() => {});
    }, 1500);
  }

  async function syncBrowserBackupFromServer() {
    const res = await fetch("/api/identity/backup", { credentials: "same-origin" });
    if (!res.ok) return;
    const blob = await res.blob();
    if (!blob || blob.size < 80) return;
    await saveBrowserBackupBlob(blob);
  }

  async function restoreBrowserBackupIfServerEmpty() {
    const stored = await loadBrowserBackupBlob();
    if (!stored?.blob) return false;
    const fd = new FormData();
    fd.append("file", stored.blob, "identity-browser-backup.zip");
    fd.append("mode", "replace");
    await api("/api/identity/backup/restore", { method: "POST", body: fd }, 90000);
    return true;
  }

  function showPersistBanner(health) {
    const el = $("#persistBanner");
    if (!el) return;
    const cloud = health?.cloud_backup || {};
    const risk = !!health?.data_ephemeral_risk;
    if (!risk && cloud.configured) {
      el.classList.add("hidden");
      el.textContent = "";
      return;
    }
    if (!risk) {
      el.classList.add("hidden");
      return;
    }
    el.classList.remove("hidden");
    if (cloud.configured) {
      el.innerHTML =
        "<strong>Render Free:</strong> el disco se borra al dormir, pero hay respaldo cloud activo. Tras despertar se restauran solas las personas.";
    } else {
      el.innerHTML =
        "<strong>Render Free:</strong> sin disco permanente. Este navegador guarda un respaldo automático de personas/fotos y lo restaura al volver. Para no depender del navegador: Starter+disco o cloud backup.";
    }
  }

  function renderWorkerList() {
    const q = (els.workerSearch?.value || "").trim().toLowerCase();
    let list = workersCache.filter((w) => {
      if (workerFilter === "active") return w.active !== false;
      if (workerFilter === "inactive") return w.active === false;
      return true;
    });
    if (q) {
      list = list.filter((w) => {
        const blob = `${w.name || ""} ${w.rut || ""} ${w.group || ""}`.toLowerCase();
        return blob.includes(q);
      });
    }
    const html = list.length
      ? list
          .map((w) => {
            const active = w.active !== false;
            const photo = w.photo_url
              ? `<img class="worker-photo" src="${w.photo_url}?t=${encodeURIComponent(w.last_seen || w.face_samples || 0)}" alt="" />`
              : `<div class="worker-photo placeholder" aria-hidden="true"></div>`;
            const qn = w.quality || 0;
            const ready =
              w.ready === true ||
              ((w.face_samples || 0) >= (w.min_samples_ready || 4) && (w.embedding_count || w.face_samples || 0) >= 3);
            const qLabel = qualityLabel(qn, ready);
            return `<li data-worker-id="${w.id}" class="${active ? "" : "is-inactive"}">
              ${photo}
              <div class="worker-meta">
                <strong>${escapeHtml(w.name || "Sin nombre")}${active ? "" : " · inactivo"}${ready ? "" : " · incompleto"}</strong>
                <span class="conf">${escapeHtml(w.rut || "—")}${w.group ? " · " + escapeHtml(w.group) : ""}</span>
                <span class="conf">${w.face_samples || 0}/4 muestras · calidad ${qn}% (${qLabel}) · ${formatLastSeen(w.last_seen)}</span>
              </div>
              <div class="worker-actions">
                <button type="button" class="btn-mini" data-toggle-active="${w.id}">${active ? "Desactivar" : "Activar"}</button>
                <button type="button" class="btn-mini" data-edit="${w.id}">Editar</button>
                <button type="button" class="btn-mini" data-reset="${w.id}">Rehacer</button>
                <button type="button" class="btn-mini danger" data-del="${w.id}">Eliminar</button>
              </div>
            </li>`;
          })
          .join("")
      : `<li class="muted">${workersCache.length ? "Sin coincidencias" : "Nadie enrolado"}</li>`;
    if (els.workerList) els.workerList.innerHTML = html;
    const actives = workersCache.filter((w) => w.active !== false).length;
    if (els.workerListHint) {
      els.workerListHint.textContent = workersCache.length
        ? `${actives} activas / ${workersCache.length} total · Inactivo = no se identifica`
        : "";
    }
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function deleteWorker(id) {
    const w = workersCache.find((x) => x.id === id);
    const label = w ? `${w.name} (${w.rut || "sin RUT"})` : id;
    if (!confirm(`¿Eliminar a ${label}?\n\nSe borran ficha, fotos y reconocimiento. No se puede deshacer.`)) {
      return;
    }
    if (els.workerListHint) els.workerListHint.textContent = "Eliminando…";
    try {
      await api(`/api/identity/workers/${id}`, { method: "DELETE" });
      if (lastIdentity?.name && w && lastIdentity.name === w.name) {
        setIdentityCard(null);
        lastIdentity = null;
        lastFaceBox = null;
      }
      if (els.enrollCoach) els.enrollCoach.textContent = `Eliminado: ${w?.name || id}`;
      await refreshWorkers();
    } catch (err) {
      if (els.workerListHint) els.workerListHint.textContent = err.message || "No se pudo eliminar";
      if (els.enrollCoach) els.enrollCoach.textContent = err.message || "Error al eliminar";
      alert(err.message || "No se pudo eliminar");
    }
  }

  async function toggleWorkerActive(id) {
    const w = workersCache.find((x) => x.id === id);
    if (!w) return;
    const next = !(w.active !== false);
    try {
      await api(`/api/identity/workers/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: next }),
      });
      if (els.enrollCoach) {
        els.enrollCoach.textContent = next ? `Activado: ${w.name}` : `Desactivado: ${w.name} (no se identificará)`;
      }
      await refreshWorkers();
    } catch (err) {
      alert(err.message || "No se pudo cambiar estado");
    }
  }

  async function editWorker(id) {
    const w = workersCache.find((x) => x.id === id);
    if (!w) return;
    const name = prompt("Nombre", w.name || "");
    if (name === null) return;
    const rutDefault = w.rut?.startsWith("SIN-RUT") ? "" : w.rut || "";
    const rut = prompt("RUT", rutDefault);
    if (rut === null) return;
    const group = prompt("Grupo / contratista / cuadrilla", w.group || "");
    if (group === null) return;
    try {
      const data = await api(`/api/identity/workers/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), rut: rut.trim(), group: group.trim() }),
      });
      if (els.enrollCoach) els.enrollCoach.textContent = `Actualizado: ${data.worker?.name || name}`;
      if (data.worker) {
        els.workerName.value = data.worker.name || "";
        els.workerRut.value = data.worker.rut?.startsWith("SIN-RUT") ? "" : data.worker.rut || "";
      }
      await refreshWorkers();
    } catch (err) {
      alert(err.message || "No se pudo editar");
    }
  }

  async function resetWorkerFaces(id) {
    const w = workersCache.find((x) => x.id === id);
    const label = w?.name || id;
    if (!confirm(`¿Borrar solo las fotos de ${label} y volver a enrolar?\n\nSe mantiene nombre, RUT y grupo.`)) return;
    try {
      const data = await api(`/api/identity/workers/${id}/reset-faces`, { method: "POST" });
      await refreshWorkers();
      if (data.worker) {
        els.workerName.value = data.worker.name || "";
        els.workerRut.value = data.worker.rut?.startsWith("SIN-RUT") ? "" : data.worker.rut || "";
      }
      if (els.enrollCoach) els.enrollCoach.textContent = "Rostros borrados. Enrolá 4 poses o adjuntá fotos.";
    } catch (err) {
      alert(err.message || "No se pudo rehacer");
    }
  }

  async function refreshScans() {
    try {
      const scans = await api("/api/scans/recent?limit=8");
      els.scanList.innerHTML = scans.length
        ? scans
            .map((s) => {
              const who = s.worker_name || "Sin nombre";
              const st = s.compliant ? "OK" : "Falta EPP";
              const ev = s.evidence_id
                ? ` <a class="evidence-link" href="/api/evidence/${encodeURIComponent(s.evidence_id)}" target="_blank" rel="noopener">foto</a>`
                : "";
              return `<li><span>${who}${ev}</span><span class="conf">${st}</span></li>`;
            })
            .join("")
        : `<li class="muted">Aún no hay escaneos con identidad</li>`;
    } catch (_) {}
  }

  function setKioskMode(on) {
    settings.kioskMode = !!on;
    saveSettings(true);
    document.body.classList.toggle("kiosk-mode", settings.kioskMode);
    $("#kioskOverlay")?.classList.toggle("hidden", !settings.kioskMode);
    const btn = $("#btnKiosk");
    if (btn) btn.classList.toggle("active", settings.kioskMode);
    if (settings.kioskMode) {
      setAppMode("monitor");
      if (els.chkIdentify) {
        els.chkIdentify.checked = true;
        settings.identifyDefault = true;
      }
    }
  }

  function updateKioskBanner(payload) {
    if (!settings.kioskMode) return;
    const c = payload?.compliance || {};
    const ok = !!c.overall_compliant;
    const hasPeople = (c.persons || []).length > 0 || (payload?.detections || []).length > 0;
    const id = payload?.identity || lastIdentity;
    const res = $("#kioskResult");
    const name = $("#kioskName");
    const detail = $("#kioskDetail");
    const overlay = $("#kioskOverlay");
    if (!res || !overlay) return;
    overlay.dataset.state = !hasPeople ? "idle" : ok ? "ok" : "bad";
    res.textContent = !hasPeople ? "En espera" : ok ? "CUMPLE" : "NO CUMPLE";
    if (name) {
      name.textContent = id?.known && id?.name ? id.name : hasPeople ? "Sin identificar" : "Acercá a la cámara";
    }
    if (detail) {
      const miss = (c.persons?.[0]?.missing || []).slice(0, 3).join(", ");
      detail.textContent = !hasPeople ? "" : ok ? id?.rut || "EPP OK" : miss || c.summary || "Revisá EPP";
    }
  }

  function setPoseUI(stepIndex, countdownText, okCount = 0) {
    const pose = POSES[stepIndex];
    const progressed = Math.max(okCount, stepIndex);
    const width = `${Math.round((progressed / POSES.length) * 100)}%`;
    const label = pose
      ? `${pose.title} · OK ${okCount}/${POSES.length}`
      : `Completado · ${okCount}/${POSES.length}`;
    if (els.poseProgress) {
      els.poseProgress.classList.remove("hidden");
      if (els.poseBarFill) els.poseBarFill.style.width = width;
      if (els.poseStepLabel) els.poseStepLabel.textContent = label;
    }
    els.enrollOverlay.classList.remove("hidden");
    if (pose) {
      els.enrollPoseTitle.textContent = pose.title;
      els.enrollPoseHint.textContent = pose.hint;
    }
    els.enrollCount.textContent = countdownText || "";
    if (els.enrollCoach && pose) els.enrollCoach.textContent = pose.hint;
  }

  function endPoseUI() {
    cancelWaitingCapture();
    setCaptureButtonsVisible(false);
    els.enrollOverlay.classList.add("hidden");
    els.enrollCount.textContent = "";
    if (els.poseBarFill) els.poseBarFill.style.width = "100%";
    if (els.poseStepLabel) els.poseStepLabel.textContent = "4/4 completo";
    enrolling = false;
    document.body.classList.remove("is-enrolling");
    applyGuideMode();
  }

  async function enrollWorker() {
    if (enrolling) return;
    if (!els.workerName.value.trim() && !els.workerRut.value.trim()) {
      if (els.enrollCoach) els.enrollCoach.textContent = "Escribí al menos el nombre";
      return;
    }
    enrolling = true;
    enrollAbort = false;
    document.body.classList.add("is-enrolling");
    stopDetectLoop();
    applyGuideMode();
    els.btnEnroll.disabled = true;
    if (els.btnIdentify) els.btnIdentify.disabled = true;
    els.btnCancelEnroll.classList.remove("hidden");
    try {
      if (!mediaStream) await startCamera({ silentDetect: true });
      else stopDetectLoop();
      showLive();
      const name = els.workerName.value.trim();
      const rut = els.workerRut.value.trim();
      let okCount = 0;

      for (let i = 0; i < POSES.length; i++) {
        if (enrollAbort) throw new Error("Cancelado");
        let captured = false;
        while (!captured) {
          if (enrollAbort) throw new Error("Cancelado");
          setPoseUI(i, "Pulsá «Tomar foto»", okCount);
          if (els.enrollCoach) els.enrollCoach.textContent = `${POSES[i].hint} · después pulsá Tomar foto`;
          try {
            await waitForCaptureClick();
          } catch (waitErr) {
            throw waitErr.message === "Cancelado" ? waitErr : new Error("Cancelado");
          }
          if (enrollAbort) throw new Error("Cancelado");
          setPoseUI(i, "Capturando…", okCount);
          const blob = await captureBlob(0.92, 960);
          if (!blob) {
            els.enrollCount.textContent = "Sin cámara — reintentá";
            if (els.enrollCoach) els.enrollCoach.textContent = "No hay imagen de cámara. Revisá permisos y reintentá.";
            continue;
          }
          const fd = new FormData();
          fd.append("file", blob, `pose_${i}.jpg`);
          fd.append("name", name);
          fd.append("rut", rut);
          try {
            const last = await api("/api/identity/enroll", { method: "POST", body: fd }, 20000);
            if (last.face_box) {
              lastFaceBox = last.face_box;
              drawDetections([], lastFrameSize.w, lastFrameSize.h, {
                face_box: last.face_box,
                known: true,
                name: last.worker?.name,
              });
            }
            if (last.face_enrolled) {
              okCount += 1;
              captured = true;
              setPoseUI(i, "OK · siguiente pose", okCount);
              if (last.worker?.name) els.workerName.value = last.worker.name;
              await sleep(450);
              break;
            }
            const why = last.error || last.message || "Sin rostro válido";
            els.enrollCount.textContent = "Calidad baja — reintentá";
            if (els.enrollCoach) {
              els.enrollCoach.textContent = why;
            }
          } catch (e) {
            els.enrollCount.textContent = "Rechazado — reintentá";
            if (els.enrollCoach) els.enrollCoach.textContent = e.message;
          }
        }
      }
      endPoseUI();
      await refreshWorkers();
      const done =
        okCount >= 4
          ? `Listo ${okCount}/4. Identificación estricta activa en Monitoreo.`
          : `Incompleto ${okCount}/4. Rehacé poses con luz frontal (calidad obligatoria).`;
      if (els.enrollCoach) els.enrollCoach.textContent = done;
    } catch (err) {
      if (els.enrollCoach) els.enrollCoach.textContent = err.message;
      endPoseUI();
    } finally {
      enrolling = false;
      document.body.classList.remove("is-enrolling");
      setCaptureButtonsVisible(false);
      applyGuideMode();
      els.btnEnroll.disabled = false;
      if (els.btnIdentify) els.btnIdentify.disabled = false;
      els.btnCancelEnroll.classList.add("hidden");
      showLive();
    }
  }

  async function uploadFacePhotos(fileList) {
    const name = els.workerName.value.trim();
    const rut = els.workerRut.value.trim();
    if (!name && !rut) {
      if (els.enrollCoach) els.enrollCoach.textContent = "Escribí nombre o RUT antes de adjuntar fotos";
      return;
    }
    const files = [...(fileList || [])].slice(0, 40);
    if (!files.length) return;
    if (els.enrollCoach) els.enrollCoach.textContent = `Cargando ${files.length} fotos de rostro…`;
    const fd = new FormData();
    fd.append("name", name);
    fd.append("rut", rut);
    for (const f of files) fd.append("files", f, f.name);
    try {
      const data = await api("/api/identity/enroll-photos", { method: "POST", body: fd }, 120000);
      if (els.enrollCoach) els.enrollCoach.textContent = data.message;
      if (data.worker?.name) els.workerName.value = data.worker.name;
      await refreshWorkers();
    } catch (err) {
      if (els.enrollCoach) els.enrollCoach.textContent = err.message;
    }
  }

  async function identifyWorker() {
    identifyingNow = true;
    applyGuideMode();
    if (!mediaStream) await startCamera({ silentDetect: true });
    showLive();
    const blob = await captureBlob(0.92, 960);
    const fd = new FormData();
    fd.append("file", blob, "id.jpg");
    fd.append("threshold", String(settings.identifyThreshold || 0.42));
    try {
      const data = await api("/api/identity/identify", { method: "POST", body: fd });
      const faceBox = data.matches?.[0]?.box || null;
      const m0 = data.matches?.[0] || {};
      if (faceBox) lastFaceBox = faceBox;
      if (data.identified) {
        setIdentityCard({
          known: !!data.identified.id,
          name: data.identified.name,
          rut: data.identified.rut,
          score: m0.score,
          confidence: m0.confidence,
          reject_reason: m0.reject_reason,
          faces_detected: data.faces_detected,
          face_box: faceBox,
        });
      } else {
        setIdentityCard({
          known: false,
          name: null,
          faces_detected: data.faces_detected || 0,
          score: m0.score,
          confidence: m0.confidence,
          reject_reason: m0.reject_reason,
        });
      }
      drawDetections([], lastFrameSize.w, lastFrameSize.h, {
        known: !!data.identified?.id,
        name: data.identified?.name,
        rut: data.identified?.rut,
        face_box: faceBox,
      });
      if (data.image_b64) {
        // flash result briefly
        els.annotatedImg.hidden = false;
        els.annotatedImg.src = `data:image/jpeg;base64,${data.image_b64}`;
        await sleep(1200);
        showLive();
      }
    } catch (err) {
      els.identityMethod.textContent = err.message;
    } finally {
      identifyingNow = false;
      applyGuideMode();
    }
  }

  async function refreshTeach() {
    try {
      const guide = await api("/api/teach/guide");
      const classes = guide.classes || [];
      els.teachClass.innerHTML = classes
        .map((c) => `<option value="${c.id}">${c.name} (${c.count})</option>`)
        .join("");
      els.teachStats.textContent = `${guide.stats?.total_samples || 0} ejemplos · ${guide.stats?.class_count || classes.length} clases`;
      const sel = classes.find((c) => c.id === els.teachClass.value);
      if (sel) els.teachHint.textContent = sel.hint;
      if (els.teachClassList) {
        const top = [...classes].sort((a, b) => (b.count || 0) - (a.count || 0)).slice(0, 12);
        els.teachClassList.innerHTML = top.length
          ? top
              .map(
                (c) =>
                  `<li><span>${c.custom ? "★ " : ""}${c.name}</span><span class="conf">${c.count}</span></li>`
              )
              .join("")
          : `<li class="muted">Sin ejemplos aún</li>`;
      }
    } catch (_) {}
  }

  async function saveTeachSample() {
    if (!mediaStream) await startCamera({ silentDetect: true });
    const blob = await captureBlob(0.8, 720);
    const fd = new FormData();
    fd.append("file", blob, "sample.jpg");
    fd.append("class_id", els.teachClass.value);
    const data = await api("/api/teach/sample", { method: "POST", body: fd });
    els.teachHint.textContent = data.message;
    await refreshTeach();
  }

  async function uploadTeachPhotos(fileList) {
    const files = [...(fileList || [])].slice(0, 80);
    if (!files.length) return;
    const classId = els.teachClass.value;
    if (!classId) {
      els.teachHint.textContent = "Elegí o creá una clase primero";
      return;
    }
    els.teachHint.textContent = `Subiendo ${files.length} fotos…`;
    const fd = new FormData();
    fd.append("class_id", classId);
    for (const f of files) fd.append("files", f, f.name);
    try {
      const data = await api("/api/teach/samples", { method: "POST", body: fd }, 120000);
      els.teachHint.textContent = data.message;
      await refreshTeach();
    } catch (err) {
      els.teachHint.textContent = err.message;
    }
  }

  async function uploadTeachVideo(file) {
    if (!file) return;
    const classId = els.teachClass.value;
    if (!classId) {
      els.teachHint.textContent = "Elegí o creá una clase primero";
      return;
    }
    els.teachHint.textContent = "Procesando video (extrayendo frames)…";
    const fd = new FormData();
    fd.append("file", file, file.name);
    fd.append("class_id", classId);
    fd.append("max_frames", "40");
    fd.append("stride", "12");
    try {
      const data = await api("/api/teach/video", { method: "POST", body: fd }, 300000);
      els.teachHint.textContent = data.message;
      await refreshTeach();
    } catch (err) {
      els.teachHint.textContent = err.message;
    }
  }

  async function createTeachClass() {
    const name = els.teachNewClass?.value?.trim();
    if (!name) {
      els.teachHint.textContent = "Escribí el nombre de la prenda nueva";
      return;
    }
    const fd = new FormData();
    fd.append("name", name);
    fd.append("hint", "Prenda personalizada — subí fotos y videos variados");
    try {
      const data = await api("/api/teach/class", { method: "POST", body: fd });
      els.teachNewClass.value = "";
      await refreshTeach();
      if (data.class?.id) els.teachClass.value = data.class.id;
      els.teachHint.textContent = `Clase creada: ${data.class?.name || name}. Ahora cargá fotos/video.`;
    } catch (err) {
      els.teachHint.textContent = err.message;
    }
  }

  function fillRepProfiles() {
    if (!els.repProfile || !profiles.length) return;
    const cur = els.repProfile.value;
    els.repProfile.innerHTML =
      `<option value="">Todos</option>` +
      profiles.map((p) => `<option value="${p.id}">${p.name}</option>`).join("");
    if (cur) els.repProfile.value = cur;
  }

  function repQuery() {
    const days = els.repDays?.value || "7";
    const profile = els.repProfile?.value || "";
    const q = new URLSearchParams({ days });
    if (profile) q.set("profile", profile);
    return q;
  }

  async function fetchStats() {
    lastStats = await api(`/api/reports/stats?${repQuery()}`);
    const t = lastStats.totals || {};
    if (els.repSideSummary) {
      els.repSideSummary.textContent = `${t.scans || 0} escaneos · ${t.compliance_rate || 0}% cumple`;
    }
    if (els.repSideList) {
      els.repSideList.innerHTML = `
        <li><span>Cumple</span><span class="conf">${t.compliant || 0}</span></li>
        <li><span>No cumple</span><span class="conf">${t.non_compliant || 0}</span></li>
        <li><span>Enrolados</span><span class="conf">${t.workers_enrolled || 0}</span></li>`;
    }
    return lastStats;
  }

  function metricHtml(stats) {
    const t = stats.totals || {};
    return `<div class="rep-hero">
      <div class="rep-metric"><b>${t.scans || 0}</b><span>Escaneos</span></div>
      <div class="rep-metric"><b>${t.compliance_rate || 0}%</b><span>Cumplimiento</span></div>
      <div class="rep-metric"><b>${t.safety_score ?? t.compliance_rate ?? 0}</b><span>Safety Score</span></div>
      <div class="rep-metric"><b>${t.non_compliant || 0}</b><span>Incumplimientos</span></div>
      <div class="rep-metric"><b>${t.workers_enrolled || 0}</b><span>Personas</span></div>
    </div>`;
  }

  function barsHtml(rows, labelKey, countKey) {
    const max = Math.max(1, ...rows.map((r) => r[countKey] || 0));
    return rows
      .map((r) => {
        const pct = Math.round(((r[countKey] || 0) / max) * 100);
        return `<div class="bar-row"><span>${r[labelKey]}</span><div class="bar-track"><i style="width:${pct}%"></i></div><span>${r[countKey]}</span></div>`;
      })
      .join("");
  }

  function tableWorkers(rows) {
    if (!rows.length) return `<p class="muted">Sin datos en este rango</p>`;
    return `<table class="rep-table"><thead><tr><th>Trabajador</th><th>RUT</th><th>OK</th><th>Falla</th><th>Score</th><th>Total</th></tr></thead><tbody>
      ${rows
        .map(
          (w) =>
            `<tr><td>${w.name || "—"}</td><td>${w.rut || "—"}</td><td>${w.ok}</td><td>${w.bad}</td><td>${w.safety_score ?? "—"}</td><td>${w.total}</td></tr>`
        )
        .join("")}
    </tbody></table>`;
  }

  function downloadUrl(path) {
    const a = document.createElement("a");
    a.href = path;
    a.download = "";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  async function openReport(key) {
    currentRep = key;
    $$(".rep-item").forEach((b) => b.classList.toggle("active", b.dataset.rep === key));
    if (!els.reportsContent) return;
    els.reportsContent.innerHTML = `<p class="muted">Cargando…</p>`;

    try {
      if (key.startsWith("notif_")) {
        await renderNotifView(key);
        return;
      }

      if (key === "csv_all") {
        downloadUrl(`/api/reports/export.csv?${repQuery()}`);
        els.reportsContent.innerHTML = `<h3 class="rep-section-title">Exportar CSV</h3><p>Descarga iniciada (todos los escaneos del rango).</p>`;
        return;
      }
      if (key === "csv_bad") {
        const q = repQuery();
        q.set("only_bad", "true");
        downloadUrl(`/api/reports/export.csv?${q}`);
        els.reportsContent.innerHTML = `<h3 class="rep-section-title">Incumplimientos CSV</h3><p>Descarga iniciada.</p>`;
        return;
      }
      if (key === "txt") {
        downloadUrl(`/api/reports/summary.txt?${repQuery()}`);
        els.reportsContent.innerHTML = `<h3 class="rep-section-title">Resumen TXT</h3><p>Descarga iniciada.</p>`;
        return;
      }

      const stats = await fetchStats();
      const days = Number(els.repDays?.value || 7);

      if (key === "safety_score") {
        const score = stats.totals?.safety_score ?? stats.totals?.compliance_rate ?? 0;
        const br = stats.totals?.safety_breakdown || {};
        const ranked = [...(stats.worker_ranking || [])].sort(
          (a, b) => (b.safety_score || 0) - (a.safety_score || 0)
        );
        els.reportsContent.innerHTML = `
          <h3 class="rep-section-title">Safety Score</h3>
          <div class="rep-hero">
            <div class="rep-metric"><b>${score}</b><span>Nota global /100</span></div>
            <div class="rep-metric"><b>${stats.totals?.compliance_rate || 0}%</b><span>Cumplimiento</span></div>
            <div class="rep-metric"><b>${stats.totals?.scans || 0}</b><span>Escaneos</span></div>
          </div>
          <p class="card-meta">Últimos ${days} días · pondera cumplimiento, faltas críticas y desconocidos.</p>
          <ul class="item-list">
            <li><span>Penalización desconocidos</span><span class="conf">-${br.penalty_unknown ?? 0}</span></li>
            <li><span>Penalización EPP crítico</span><span class="conf">-${br.penalty_critical_missing ?? 0}</span></li>
            <li><span>Eventos EPP crítico</span><span class="conf">${br.critical_missing_events ?? 0}</span></li>
          </ul>
          <h4>Por trabajador</h4>
          ${tableWorkers(ranked)}`;
      } else if (key === "overview") {
        els.reportsContent.innerHTML = `
          <h3 class="rep-section-title">Resumen general</h3>
          ${metricHtml(stats)}
          <p class="card-meta">Últimos ${days} días${stats.profile ? ` · perfil ${stats.profile}` : ""}.</p>
          <h4>EPP faltante</h4>
          ${barsHtml(stats.missing_epp || [], "item", "count") || `<p class="muted">Sin faltantes</p>`}`;
      } else if (key === "byday") {
        els.reportsContent.innerHTML = `
          <h3 class="rep-section-title">Cumplimiento por día</h3>
          ${metricHtml(stats)}
          <table class="rep-table"><thead><tr><th>Día</th><th>Total</th><th>OK</th><th>Falla</th></tr></thead>
          <tbody>${(stats.by_day || [])
            .map((d) => `<tr><td>${d.day}</td><td>${d.total}</td><td>${d.ok}</td><td>${d.bad}</td></tr>`)
            .join("") || `<tr><td colspan="4">Sin datos</td></tr>`}</tbody></table>`;
      } else if (key === "ranking") {
        els.reportsContent.innerHTML = `
          <h3 class="rep-section-title">Ranking trabajadores</h3>
          <p class="card-meta">Ordenado por incumplimientos.</p>
          ${tableWorkers(stats.worker_ranking || [])}`;
      } else if (key === "missing") {
        els.reportsContent.innerHTML = `
          <h3 class="rep-section-title">EPP faltante frecuente</h3>
          ${barsHtml(stats.missing_epp || [], "item", "count") || `<p class="muted">Sin datos</p>`}`;
      } else if (key === "profiles") {
        els.reportsContent.innerHTML = `
          <h3 class="rep-section-title">Por perfil de faena</h3>
          ${barsHtml(stats.by_profile || [], "profile", "count") || `<p class="muted">Sin datos</p>`}`;
      } else if (key === "unknown") {
        els.reportsContent.innerHTML = `
          <h3 class="rep-section-title">Sin identidad</h3>
          ${metricHtml(stats)}
          <p>Escaneos sin trabajador asociado: <strong>${stats.totals?.unknown_scans || 0}</strong></p>
          <p class="card-meta">Enrolá en Personas para reducir desconocidos.</p>`;
      } else if (key === "daily" || key === "weekly" || key === "monthly" || key === "print") {
        const map = { daily: 1, weekly: 7, monthly: 30, print: days };
        if (key !== "print") els.repDays.value = String(map[key]);
        const report = await api(`/api/reports/print?${repQuery()}`);
        els.reportsContent.innerHTML = `
          <h3 class="rep-section-title">${report.title || "Informe"}</h3>
          ${metricHtml(report.stats || stats)}
          <div class="rep-actions">
            <button type="button" class="btn primary" id="btnPrintRep">Imprimir / PDF</button>
            <button type="button" class="btn secondary" id="btnCopyRep">Copiar texto</button>
            <button type="button" class="btn ghost" id="btnDlTxt">Descargar TXT</button>
          </div>
          <pre class="rep-pre" id="repPrintText">${(report.text || "").replace(/</g, "&lt;")}</pre>`;
        $("#btnPrintRep")?.addEventListener("click", () => {
          const q = repQuery().toString();
          const w = window.open(`/api/reports/print.html?${q}`, "_blank");
          if (w) {
            w.addEventListener("load", () => {
              try {
                w.focus();
                w.print();
              } catch (_) {}
            });
          }
        });
        $("#btnCopyRep")?.addEventListener("click", async () => {
          await navigator.clipboard.writeText(report.text || "");
          els.repSideSummary.textContent = "Informe copiado al portapapeles";
        });
        $("#btnDlTxt")?.addEventListener("click", () => downloadUrl(`/api/reports/summary.txt?${repQuery()}`));
      } else {
        els.reportsContent.innerHTML = `<p class="muted">Opción no implementada</p>`;
      }
    } catch (err) {
      els.reportsContent.innerHTML = `<p class="muted">${err.message}</p>`;
    }
  }

  async function renderNotifView(key) {
    notifConfig = await api("/api/notifications/config");
    const ch = notifConfig.channels || {};
    const tpl = notifConfig.template || {};

    if (key === "notif_setup") {
      const ac = notifConfig.access_control || {};
      const et = notifConfig.email_transport || {};
      const emailHint =
        et.mode === "resend"
          ? "Email real vía Resend"
          : et.mode === "smtp"
            ? `Email real vía SMTP (${et.smtp_host || "host"})`
            : "Sin SMTP/Resend → solo abre mailto en el navegador";
      els.reportsContent.innerHTML = `
        <h3 class="rep-section-title">Canales de notificación</h3>
        <p class="card-meta">${emailHint}</p>
        <form class="rep-form" id="notifChannelsForm">
          <label><span>Webhook (Slack / Teams / Discord / genérico)</span>
            <input type="checkbox" id="nWhEn" ${ch.webhook?.enabled ? "checked" : ""}/> Activar
            <input type="url" id="nWhUrl" placeholder="https://hooks.slack.com/..." value="${ch.webhook?.url || ""}"/>
          </label>
          <label><span>WhatsApp / API webhook</span>
            <input type="checkbox" id="nWaEn" ${ch.whatsapp_webhook?.enabled ? "checked" : ""}/> Activar
            <input type="url" id="nWaUrl" placeholder="https://..." value="${ch.whatsapp_webhook?.url || ""}"/>
          </label>
          <label><span>Email</span>
            <input type="checkbox" id="nEmEn" ${ch.email?.enabled ? "checked" : ""}/> Activar
            <input type="email" id="nEmTo" placeholder="seguridad@empresa.cl" value="${ch.email?.to || ""}"/>
            <input type="email" id="nEmCc" placeholder="cc opcional" value="${ch.email?.cc || ""}"/>
          </label>
          <p class="card-kicker">Alarma ESP32 (baliza + sirena)</p>
          <label><span>Hardware VigiEPP Alarm</span>
            <input type="checkbox" id="nHwEn" ${ac.hardware?.enabled ? "checked" : ""}/> Activar
            <small class="card-meta">Llama a http://IP_ESP32/alarma (deny) y /ok (allow). El servidor VigiEPP debe estar en la misma red que el ESP32.</small>
            <input type="url" id="nHwUrl" placeholder="http://192.168.1.50" value="${ac.hardware?.base_url || ""}"/>
            <label class="check"><input type="checkbox" id="nHwBad" ${ac.hardware?.on_non_compliant !== false ? "checked" : ""}/> Alarma en incumplimiento EPP</label>
            <label class="check"><input type="checkbox" id="nHwUnk" ${ac.hardware?.on_unknown_face !== false ? "checked" : ""}/> Alarma en rostro desconocido</label>
            <label class="check"><input type="checkbox" id="nHwOk" ${ac.hardware?.auto_ok !== false ? "checked" : ""}/> /ok automático si EPP cumple</label>
          </label>
          <div class="rep-actions" style="margin:0.5rem 0 1rem">
            <button type="button" class="btn secondary" id="btnHwAlarma">Probar /alarma</button>
            <button type="button" class="btn secondary" id="btnHwOk">Probar /ok</button>
          </div>
          <pre class="rep-pre" id="hwTestOut" style="display:none">—</pre>
          <p class="card-kicker">Abrir acceso (torniquete / gate)</p>
          <label><span>Control de acceso</span>
            <input type="checkbox" id="nAcEn" ${ac.enabled ? "checked" : ""}/> Activar gate
            <small class="card-meta">Allow solo si identidad conocida + EPP OK. Con hardware activo: allow→/ok, deny→/alarma.</small>
            <label class="check"><input type="checkbox" id="nAcId" ${ac.require_identity !== false ? "checked" : ""}/> Exigir identidad</label>
            <label class="check"><input type="checkbox" id="nAcNf" ${ac.notify !== false ? "checked" : ""}/> Notificar decisión</label>
          </label>
          <button class="btn primary" type="submit">Guardar canales</button>
        </form>`;
      const hwTest = async (action) => {
        const out = $("#hwTestOut");
        if (out) out.style.display = "block";
        try {
          const res = await api("/api/notifications/hardware/test", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action }),
          });
          if (out) out.textContent = JSON.stringify(res, null, 2);
          els.repSideSummary.textContent = res.ok ? `Hardware ${action} OK` : `Hardware error: ${res.detail || ""}`;
        } catch (err) {
          if (out) out.textContent = String(err.message || err);
        }
      };
      $("#btnHwAlarma")?.addEventListener("click", () => hwTest("alarma"));
      $("#btnHwOk")?.addEventListener("click", () => hwTest("ok"));
      $("#notifChannelsForm")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const body = {
          channels: {
            webhook: { enabled: $("#nWhEn").checked, url: $("#nWhUrl").value.trim() },
            whatsapp_webhook: { enabled: $("#nWaEn").checked, url: $("#nWaUrl").value.trim() },
            email: {
              enabled: $("#nEmEn").checked,
              to: $("#nEmTo").value.trim(),
              cc: $("#nEmCc")?.value.trim() || "",
            },
          },
          access_control: {
            enabled: $("#nAcEn").checked,
            require_identity: $("#nAcId").checked,
            notify: $("#nAcNf").checked,
            hardware: {
              enabled: $("#nHwEn").checked,
              base_url: $("#nHwUrl").value.trim(),
              alarma_path: "/alarma",
              ok_path: "/ok",
              method: "GET",
              on_non_compliant: $("#nHwBad").checked,
              on_unknown_face: $("#nHwUnk").checked,
              auto_ok: $("#nHwOk").checked,
            },
          },
        };
        const res = await api("/api/notifications/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        notifConfig = res.config;
        els.repSideSummary.textContent = "Canales guardados";
      });
      return;
    }

    if (key === "notif_rules") {
      els.reportsContent.innerHTML = `
        <h3 class="rep-section-title">Reglas de alerta</h3>
        <p class="card-meta">La coolora es por persona + tipo de alerta (no bloquea a otros).</p>
        <form class="rep-form" id="notifRulesForm">
          <label><input type="checkbox" id="nEnabled" ${notifConfig.enabled ? "checked" : ""}/> Activar notificaciones</label>
          <label><input type="checkbox" id="nOnBad" ${notifConfig.on_non_compliant ? "checked" : ""}/> Avisar en incumplimiento EPP</label>
          <label><input type="checkbox" id="nOnUnknown" ${notifConfig.on_unknown_face ? "checked" : ""}/> Avisar rostro desconocido</label>
          <label><input type="checkbox" id="nOnZone" ${notifConfig.on_zone_alert !== false ? "checked" : ""}/> Avisar zonas / near-miss</label>
          <label><input type="checkbox" id="nOnlyKnown" ${notifConfig.only_known_workers ? "checked" : ""}/> Solo trabajadores conocidos (EPP)</label>
          <label><span>Cooldownora entre avisos (segundos)</span>
            <input type="number" id="nCooldown" min="0" max="3600" value="${notifConfig.cooldown_seconds ?? 120}"/>
          </label>
          <button class="btn primary" type="submit">Guardar reglas</button>
        </form>`;
      $("#notifRulesForm")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const res = await api("/api/notifications/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            enabled: $("#nEnabled").checked,
            on_non_compliant: $("#nOnBad").checked,
            on_unknown_face: $("#nOnUnknown").checked,
            on_zone_alert: $("#nOnZone").checked,
            only_known_workers: $("#nOnlyKnown").checked,
            cooldown_seconds: Number($("#nCooldown").value) || 0,
          }),
        });
        notifConfig = res.config;
        els.repSideSummary.textContent = "Reglas guardadas";
      });
      return;
    }

    if (key === "notif_template") {
      els.reportsContent.innerHTML = `
        <h3 class="rep-section-title">Plantilla de mensaje</h3>
        <p class="card-meta">Variables: {name} {rut} {profile} {summary} {missing} {ts}</p>
        <form class="rep-form" id="notifTplForm">
          <label><span>Asunto</span><input type="text" id="nSub" value="${(tpl.subject || "").replace(/"/g, "&quot;")}"/></label>
          <label><span>Cuerpo</span><textarea id="nBody">${tpl.body || ""}</textarea></label>
          <button class="btn primary" type="submit">Guardar plantilla</button>
        </form>`;
      $("#notifTplForm")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const res = await api("/api/notifications/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ template: { subject: $("#nSub").value, body: $("#nBody").value } }),
        });
        notifConfig = res.config;
        els.repSideSummary.textContent = "Plantilla guardada";
      });
      return;
    }

    if (key === "notif_test") {
      els.reportsContent.innerHTML = `
        <h3 class="rep-section-title">Probar / enviar ahora</h3>
        <p>Envía una alerta de prueba por los canales activos o dispara el ESP32.</p>
        <div class="rep-actions">
          <button type="button" class="btn primary" id="btnNotifTest">Enviar prueba</button>
          <button type="button" class="btn secondary" id="btnNotifManual">Enviar alerta manual</button>
          <button type="button" class="btn secondary" id="btnHwAlarma2">ESP32 /alarma</button>
          <button type="button" class="btn secondary" id="btnHwOk2">ESP32 /ok</button>
        </div>
        <pre class="rep-pre" id="notifTestOut">—</pre>`;
      $("#btnNotifTest")?.addEventListener("click", async () => {
        const res = await api("/api/notifications/test", { method: "POST" });
        $("#notifTestOut").textContent = JSON.stringify(res, null, 2);
        if (res.mailto) window.location.href = res.mailto;
      });
      $("#btnNotifManual")?.addEventListener("click", async () => {
        const res = await api("/api/notifications/send", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: "Alerta manual",
            summary: "Envío manual desde Informes",
            missing: ["casco"],
            force: true,
          }),
        });
        $("#notifTestOut").textContent = JSON.stringify(res, null, 2);
        if (res.mailto) window.location.href = res.mailto;
      });
      $("#btnHwAlarma2")?.addEventListener("click", async () => {
        const res = await api("/api/notifications/hardware/test", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "alarma" }),
        });
        $("#notifTestOut").textContent = JSON.stringify(res, null, 2);
      });
      $("#btnHwOk2")?.addEventListener("click", async () => {
        const res = await api("/api/notifications/hardware/test", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "ok" }),
        });
        $("#notifTestOut").textContent = JSON.stringify(res, null, 2);
      });
      return;
    }

    if (key === "notif_log") {
      const log = await api("/api/notifications/log?limit=40");
      els.reportsContent.innerHTML = `
        <h3 class="rep-section-title">Historial de envíos</h3>
        <table class="rep-table"><thead><tr><th>Fecha</th><th>Tipo</th><th>Estado</th><th>Asunto</th></tr></thead>
        <tbody>${
          log.length
            ? log
                .map(
                  (r) =>
                    `<tr><td>${(r.ts || "").slice(0, 19)}</td><td>${r.kind || "—"}</td><td>${r.ok ? "OK" : "Falló"}</td><td>${r.subject || "—"}</td></tr>`
                )
                .join("")
            : `<tr><td colspan="4">Sin envíos aún</td></tr>`
        }</tbody></table>`;
    }
  }

  // Events
  $$(".mode-btn").forEach((b) => b.addEventListener("click", () => setAppMode(b.dataset.mode)));
  $$(".rep-item").forEach((b) => b.addEventListener("click", () => openReport(b.dataset.rep)));
  if (els.btnRepRefresh) els.btnRepRefresh.addEventListener("click", () => openReport(currentRep || "overview"));
  if (els.repDays) els.repDays.addEventListener("change", () => openReport(currentRep || "overview"));
  if (els.repProfile) els.repProfile.addEventListener("change", () => openReport(currentRep || "overview"));
  $$(".tab").forEach((t) => {
    if (t.dataset.source) t.addEventListener("click", () => setSource(t.dataset.source));
  });
  els.profileSelect.addEventListener("change", renderProfile);
  els.btnStartCam.addEventListener("click", () => startCamera());
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
  });
  els.btnStartRtsp.addEventListener("click", startRtsp);
  els.btnStopRtsp.addEventListener("click", stopRtsp);
  els.fileInput.addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await detectBlob(file, { identify: true, returnImage: true });
  });
  els.btnEnroll.addEventListener("click", enrollWorker);
  els.btnCancelEnroll.addEventListener("click", () => {
    enrollAbort = true;
    cancelWaitingCapture();
  });
  for (const btn of [els.btnCapturePose, els.btnCapturePoseId]) {
    if (btn) btn.addEventListener("click", triggerCapturePose);
  }
  if (els.faceTrainPhotos) {
    els.faceTrainPhotos.addEventListener("change", async (e) => {
      await uploadFacePhotos(e.target.files);
      e.target.value = "";
    });
  }
  els.btnIdentify.addEventListener("click", identifyWorker);
  const onWorkerListClick = (e) => {
    const del = e.target.closest("[data-del]");
    const reset = e.target.closest("[data-reset]");
    const edit = e.target.closest("[data-edit]");
    const tog = e.target.closest("[data-toggle-active]");
    if (del) deleteWorker(del.getAttribute("data-del"));
    if (reset) resetWorkerFaces(reset.getAttribute("data-reset"));
    if (edit) editWorker(edit.getAttribute("data-edit"));
    if (tog) toggleWorkerActive(tog.getAttribute("data-toggle-active"));
  };
  if (els.workerList) els.workerList.addEventListener("click", onWorkerListClick);
  if (els.workerSearch) {
    els.workerSearch.addEventListener("input", () => renderWorkerList());
  }
  $$("[data-worker-filter]").forEach((b) => {
    b.addEventListener("click", () => {
      workerFilter = b.dataset.workerFilter || "active";
      $$("[data-worker-filter]").forEach((x) => x.classList.toggle("active", x === b));
      renderWorkerList();
    });
  });
  els.btnTeachSample.addEventListener("click", saveTeachSample);
  if (els.teachPhotos) {
    els.teachPhotos.addEventListener("change", async (e) => {
      await uploadTeachPhotos(e.target.files);
      e.target.value = "";
    });
  }
  if (els.teachVideo) {
    els.teachVideo.addEventListener("change", async (e) => {
      await uploadTeachVideo(e.target.files?.[0]);
      e.target.value = "";
    });
  }
  if (els.btnTeachAddClass) els.btnTeachAddClass.addEventListener("click", createTeachClass);
  if (els.silZoomRange) {
    els.silZoomRange.addEventListener("input", () => setSilhouetteZoom(Number(els.silZoomRange.value)));
  }
  if (els.btnSilZoomIn) {
    els.btnSilZoomIn.addEventListener("click", () => {
      const face = els.silhouetteGuide?.dataset.guide === "face";
      const cur = face ? settings.faceScale : settings.bodyScale;
      setSilhouetteZoom(cur + 5);
    });
  }
  if (els.btnSilZoomOut) {
    els.btnSilZoomOut.addEventListener("click", () => {
      const face = els.silhouetteGuide?.dataset.guide === "face";
      const cur = face ? settings.faceScale : settings.bodyScale;
      setSilhouetteZoom(cur - 5);
    });
  }
  els.btnTeachTrain.addEventListener("click", async () => {
    els.teachHint.textContent = "Entrenando modelo (puede tardar)…";
    try {
      const data = await api("/api/teach/train", { method: "POST" }, 60000);
      els.teachHint.textContent = data.message;
    } catch (err) {
      els.teachHint.textContent = err.message;
    }
  });
  els.btnTeachActivate.addEventListener("click", async () => {
    const data = await api("/api/teach/activate", { method: "POST" });
    els.modelStatusText.textContent = `IA lista · ${data.model}`;
    els.teachHint.textContent = "Modelo personalizado activado";
  });
  window.addEventListener("resize", () => {
    if (mediaStream) syncCanvasSize();
  });

  [
    els.cfgSilhouette,
    els.cfgSilhouetteGate,
    els.cfgFaceGuide,
    els.cfgAutoAdvance,
    els.cfgIdentifyDefault,
    els.cfgShowBoxes,
    els.cfgFullscreenDefault,
    els.cfgAudioAlerts,
    els.cfgAnonymize,
    els.cfgShowZones,
  ].forEach((el) => {
    if (el) el.addEventListener("change", readSettingsFromForm);
  });
  [els.cfgBodyScale, els.cfgFaceScale, els.cfgGuideY, els.cfgIdThresh, els.cfgAudioRepeats].forEach((el) => {
    if (!el) return;
    el.addEventListener("input", () => {
      readSettingsFromForm();
      if (el === els.cfgAudioRepeats) resetSpeakIncident();
    });
    el.addEventListener("change", () => {
      readSettingsFromForm();
      if (el === els.cfgAudioRepeats) resetSpeakIncident();
    });
  });
  if (els.cfgPoseAttempts) {
    els.cfgPoseAttempts.addEventListener("change", readSettingsFromForm);
  }
  if (els.chkIdentify) {
    els.chkIdentify.addEventListener("change", () => {
      settings.identifyDefault = !!els.chkIdentify.checked;
      if (els.cfgIdentifyDefault) els.cfgIdentifyDefault.checked = settings.identifyDefault;
      saveSettings();
    });
  }
  if (els.chkFullscreen) {
    els.chkFullscreen.addEventListener("change", () => {
      settings.fullscreenDefault = !!els.chkFullscreen.checked;
      if (els.cfgFullscreenDefault) els.cfgFullscreenDefault.checked = settings.fullscreenDefault;
      saveSettings();
    });
  }

  els.btnZoneAdd?.addEventListener("click", () => {
    zonesCache = readZonesFromEditor();
    zonesCache.push({
      id: `zona-${Date.now()}`,
      name: `Zona ${zonesCache.length + 1}`,
      type: "restricted",
      enabled: true,
      x: 0.05,
      y: 0.1,
      w: 0.25,
      h: 0.35,
      color: "#e85d04",
    });
    renderZonesEditor();
  });
  els.btnZoneSave?.addEventListener("click", async () => {
    zonesCache = readZonesFromEditor();
    try {
      const res = await api("/api/zones", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ zones: zonesCache }),
      });
      zonesCache = res.zones || zonesCache;
      renderZonesEditor();
      if (els.zonesHint) els.zonesHint.textContent = "Zonas guardadas";
    } catch (err) {
      if (els.zonesHint) els.zonesHint.textContent = err.message;
    }
  });
  $$("[data-zone-preset]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-zone-preset");
      if (!id) return;
      if (!confirm(`¿Reemplazar zonas actuales por el preset «${id}»?`)) return;
      try {
        const res = await api(`/api/zones/presets/${id}`, { method: "POST" });
        zonesCache = res.zones || [];
        renderZonesEditor();
        if (els.zonesHint) els.zonesHint.textContent = `Preset «${id}» aplicado · ${zonesCache.length} zonas`;
      } catch (err) {
        if (els.zonesHint) els.zonesHint.textContent = err.message;
      }
    });
  });
  els.zonesList?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-z-del]");
    if (!btn) return;
    const i = Number(btn.getAttribute("data-z-del"));
    zonesCache = readZonesFromEditor().filter((_, idx) => idx !== i);
    renderZonesEditor();
  });

  $("#btnKiosk")?.addEventListener("click", () => setKioskMode(!settings.kioskMode));
  $("#btnKioskExit")?.addEventListener("click", () => setKioskMode(false));
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && settings.kioskMode) setKioskMode(false);
  });

  $("#btnLogout")?.addEventListener("click", async () => {
    try {
      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    } catch (_) {}
    sessionStorage.removeItem("vigiepp.token");
    sessionStorage.removeItem("vigiepp.role");
    await ensureAuth(true);
  });

  async function authHeaders() {
    const headers = {};
    const token = sessionStorage.getItem("vigiepp.token");
    if (token) headers["X-VigiEPP-Key"] = token;
    return headers;
  }

  $("#btnBackupExport")?.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/identity/backup", {
        credentials: "include",
        headers: await authHeaders(),
      });
      if (res.status === 401) {
        await ensureAuth(true);
        throw new Error("Sesión expirada");
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `vigiepp-personas-${new Date().toISOString().slice(0, 10)}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(a.href);
      if (els.workerListHint) els.workerListHint.textContent = "Backup descargado";
    } catch (err) {
      if (els.workerListHint) els.workerListHint.textContent = err.message || "No se pudo exportar";
    }
  });

  $("#backupImportFile")?.addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    const mode = $("#backupImportMode")?.value || "merge";
    if (mode === "replace" && !confirm("¿Reemplazar TODAS las personas por el backup?")) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("mode", mode);
    try {
      if (els.workerListHint) els.workerListHint.textContent = "Restaurando…";
      const res = await fetch("/api/identity/backup/restore", {
        method: "POST",
        credentials: "include",
        headers: await authHeaders(),
        body: fd,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      await refreshWorkers();
      if (els.workerListHint) {
        els.workerListHint.textContent =
          mode === "replace"
            ? `Restaurado · ${data.workers || 0} personas`
            : `Fusionado · +${data.added || 0} / ~${data.updated || 0} · total ${data.workers || 0}`;
      }
    } catch (err) {
      if (els.workerListHint) els.workerListHint.textContent = err.message || "Restore falló";
    }
  });

  boot();
})();
