import { $, $$ } from "./modules/dom.js";
import { createApi } from "./modules/http.js";
import {
  defaultSettings,
  getSettings,
  loadSettings as loadSettingsFromModule,
  saveSettings as saveSettingsToModule,
} from "./modules/settings.js";
import {
  applyMobileChrome as applyMobileChromeModule,
  isMobile,
  isIOS,
  isAndroid,
  syncViewportHeight,
} from "./modules/mobile.js";
import { createAuthController } from "./modules/auth.js";
import { createEnterpriseController } from "./modules/enterprise.js";

let ensureAuth;
let applyRoleUI;
let userRole = "admin";

const api = createApi({
  onUnauthorized: async () => {
    sessionStorage.removeItem("vigiepp.token");
    sessionStorage.removeItem("vigiepp.role");
    await ensureAuth(true);
    throw new Error("Sesión expirada. Ingresá el PIN de nuevo.");
  },
});

const enterprise = createEnterpriseController(api);
const { refreshSitesUi, refreshEhsUi, saveEhsConfig } = enterprise;

function bindAuthController(onOperatorLogin) {
  const ctrl = createAuthController({ onOperatorLogin });
  ensureAuth = ctrl.ensureAuth;
  applyRoleUI = (role) => {
    userRole = role || "admin";
    ctrl.applyRoleUI(role);
  };
}

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
    cameraSelect: $("#cameraSelect"),
    cameraName: $("#cameraName"),
    btnSaveCamera: $("#btnSaveCamera"),
    btnDelCamera: $("#btnDelCamera"),
    fileInput: $("#fileInput"),
    cameraControls: $("#cameraControls"),
    rtspControls: $("#rtspControls"),
    uploadControls: $("#uploadControls"),
    identityControls: $("#identityControls"),
    teachControls: $("#teachControls"),
    monitorToolbar: $("#monitorToolbar"),
    chkIdentify: $("#chkIdentify"),
    chkBiometricConsent: $("#chkBiometricConsent"),
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
    zonesCanvas: $("#zonesCanvas"),
    zonesPreviewHint: $("#zonesPreviewHint"),
    btnZoneAdd: $("#btnZoneAdd"),
    btnZoneSave: $("#btnZoneSave"),
    safetyScoreLive: $("#safetyScoreLive"),
    exposureLive: $("#exposureLive"),
    cfgSavedHint: $("#cfgSavedHint"),
    cfgPpeChips: $("#cfgPpeChips"),
    btnResetPpe: $("#btnResetPpe"),
    btnCfgResetPpe: $("#btnCfgResetPpe"),
    reportsDesk: $("#reportsDesk"),
    reportsContent: $("#reportsContent"),
    repDays: $("#repDays"),
    repProfile: $("#repProfile"),
    btnRepRefresh: $("#btnRepRefresh"),
    repSideSummary: $("#repSideSummary"),
    repSideList: $("#repSideList"),
  };

  const APP_BUILD = globalThis.VIGIEPP_BUILD || "v42";

  function isLiveMode() {
    return appMode === "live" || appMode === "monitor";
  }

  function isViewportMode() {
    return isLiveMode() || appMode === "identity" || appMode === "teach";
  }

  let profiles = [];
  let ppeCatalog = [];
  let eppStreak = 0;
  let lastScanRefreshAt = 0;
  let mediaStream = null;
  let camTimer = null;
  let detectLoopOn = false;
  let detectBackoffMs = 0;
  let rtspTimer = null;
  let busy = false;
  let sourceMode = "camera";
  let appMode = "live";
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
  let combinedInference = false;
  let lastHealth = null;

  function applyMobileChrome() {
    applyMobileChromeModule(settings, els);
  }

  let settings = getSettings();

  function loadSettings() {
    loadSettingsFromModule();
    settings = getSettings();
  }

  function saveSettings(silent = false) {
    saveSettingsToModule(silent, els.cfgSavedHint);
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
      const pct = Math.round((settings.identifyThreshold || 0.33) * 100);
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
    const qrEl = $("#cfgQrOnlyMode");
    const retEl = $("#cfgRetentionDays");
    const retVal = $("#cfgRetentionVal");
    if (qrEl) qrEl.checked = !!settings.qrOnlyMode;
    if (retEl) {
      retEl.value = String(settings.retentionDays ?? 90);
      if (retVal) retVal.textContent = String(settings.retentionDays ?? 90);
    }
  }

  async function loadPrivacyServer() {
    try {
      const data = await api("/api/privacy/config");
      const cfg = data.config || {};
      settings.qrOnlyMode = !!cfg.qr_only_mode;
      settings.retentionDays = Number(cfg.retention_days) || 90;
      applyCfgToDom();
    } catch (_) {}
  }

  async function savePrivacyServer() {
    try {
      await api("/api/privacy/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          qr_only_mode: !!settings.qrOnlyMode,
          retention_days: Number(settings.retentionDays) || 90,
        }),
      });
    } catch (_) {}
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
      settings.identifyThreshold = Math.max(0.25, Math.min(0.65, (Number(els.cfgIdThresh.value) || 33) / 100));
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
    settings.qrOnlyMode = !!$("#cfgQrOnlyMode")?.checked;
    settings.retentionDays = Math.max(
      7,
      Math.min(365, Number($("#cfgRetentionDays")?.value) || settings.retentionDays || 90)
    );
    if ($("#cfgRetentionVal")) $("#cfgRetentionVal").textContent = String(settings.retentionDays);
    savePrivacyServer();
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
    const scanning = document.body.classList.contains("is-scanning") && appMode === "live";
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

  function ppeLabel(id) {
    return PPE_LABEL[id] || ppeCatalog.find((x) => x.id === id)?.label || id;
  }

  function catalogItems() {
    if (ppeCatalog.length) return ppeCatalog;
    return Object.entries(PPE_LABEL).map(([id, label]) => ({ id, label }));
  }

  function getProfileDefaults(profileId) {
    const p = profiles.find((x) => x.id === profileId);
    return p ? [...(p.required || [])] : [];
  }

  function getEffectiveRequired(profileId) {
    const pid = profileId || els.profileSelect?.value || "general";
    if (settings.ppeByProfile && Object.prototype.hasOwnProperty.call(settings.ppeByProfile, pid)) {
      return [...(settings.ppeByProfile[pid] || [])];
    }
    return getProfileDefaults(pid);
  }

  function setProfileRequired(profileId, list) {
    if (!settings.ppeByProfile) settings.ppeByProfile = {};
    settings.ppeByProfile[profileId] = [...list];
    saveSettings(true);
  }

  function resetProfileRequired(profileId) {
    if (!settings.ppeByProfile) return;
    delete settings.ppeByProfile[profileId];
    saveSettings(true);
  }

  function renderPpeSelector(container, profileId) {
    if (!container) return;
    const pid = profileId || els.profileSelect?.value || "general";
    const required = new Set(getEffectiveRequired(pid));
    container.innerHTML = catalogItems()
      .map((item) => {
        const on = required.has(item.id);
        return `<button type="button" class="chip ppe-toggle" data-ppe="${escapeHtml(item.id)}" aria-pressed="${on ? "true" : "false"}">${escapeHtml(item.label)}</button>`;
      })
      .join("");
  }

  function bindPpeChipContainer(container) {
    if (!container || container._ppeBound) return;
    container._ppeBound = true;
    container.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-ppe]");
      if (!btn) return;
      const key = btn.getAttribute("data-ppe");
      const pid = els.profileSelect?.value || "general";
      const req = new Set(getEffectiveRequired(pid));
      if (req.has(key)) req.delete(key);
      else req.add(key);
      setProfileRequired(pid, [...req]);
      renderProfile();
    });
  }

  function requiredQueryValue(profileId) {
    return JSON.stringify(getEffectiveRequired(profileId || els.profileSelect?.value || "general"));
  }

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

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
    // Nunca mostrar el <video> vacío: Chrome dibuja un teléfono con candado
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
    if (!settings.silhouetteEnabled && !faceGuideActive() && !(settings.faceGuide && appMode === "live")) {
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
      settings.silhouetteEnabled || faceGuideActive() || (!!settings.faceGuide && appMode === "live");
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
  let selectedZoneIndex = -1;
  let zonesCanvasRaf = 0;
  let zonesCanvasDrag = null;
  const ZONES_CANVAS_HANDLE = 10;
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
      const label =
        z.type === "vehicle_lane"
          ? `Vía · ${z.name}`
          : z.type === "machinery"
            ? `Máquina · ${z.name}`
            : `Zona · ${z.name}`;
      ctx.fillText(label, rx + 6, ry + 14);
    }
  }

  function syncZonesCanvasSize() {
    const canvas = els.zonesCanvas;
    if (!canvas) return;
    const frame = canvas.parentElement;
    if (!frame) return;
    const rect = frame.getBoundingClientRect();
    canvas.width = Math.max(1, Math.round(rect.width));
    canvas.height = Math.max(1, Math.round(rect.height));
  }

  function zoneCanvasRect(z, cw, ch) {
    return {
      x: (z.x || 0) * cw,
      y: (z.y || 0) * ch,
      w: (z.w || 0.2) * cw,
      h: (z.h || 0.2) * ch,
    };
  }

  function clampZoneNorm(z) {
    const min = 0.05;
    z.w = Math.max(min, Math.min(0.95, z.w || min));
    z.h = Math.max(min, Math.min(0.95, z.h || min));
    z.x = Math.max(0, Math.min(1 - z.w, z.x || 0));
    z.y = Math.max(0, Math.min(1 - z.h, z.y || 0));
  }

  function drawZonesEditorCanvas() {
    const canvas = els.zonesCanvas;
    if (!canvas) return;
    syncZonesCanvasSize();
    const ctx = canvas.getContext("2d");
    const cw = canvas.width;
    const ch = canvas.height;
    ctx.clearRect(0, 0, cw, ch);

    const video = els.liveVideo;
    if (video && video.videoWidth > 0 && !video.hidden) {
      const cover = videoCoverSize(video.videoWidth, video.videoHeight, cw, ch);
      ctx.drawImage(
        video,
        cover.ox,
        cover.oy,
        cover.w,
        cover.h
      );
    } else {
      ctx.fillStyle = "#0a0e0c";
      ctx.fillRect(0, 0, cw, ch);
      ctx.strokeStyle = "rgba(255,255,255,0.04)";
      ctx.lineWidth = 1;
      for (let x = 0; x <= cw; x += cw / 8) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, ch);
        ctx.stroke();
      }
      for (let y = 0; y <= ch; y += ch / 8) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(cw, y);
        ctx.stroke();
      }
      ctx.font = "500 11px Source Sans 3, sans-serif";
      ctx.fillStyle = "rgba(238,243,239,0.45)";
      ctx.textAlign = "center";
      ctx.fillText("Iniciá la cámara en Monitoreo para ver la vista previa", cw / 2, ch / 2);
      ctx.textAlign = "left";
    }

    const zones = zonesCache || [];
    for (let i = 0; i < zones.length; i++) {
      const z = zones[i];
      if (!z.enabled) continue;
      const { x, y, w, h } = zoneCanvasRect(z, cw, ch);
      const selected = i === selectedZoneIndex;
      ctx.fillStyle = selected ? "rgba(232,93,4,0.22)" : "rgba(232,93,4,0.1)";
      ctx.strokeStyle = selected ? "rgba(232,93,4,0.95)" : (z.color || "rgba(232,93,4,0.75)");
      ctx.lineWidth = selected ? 2 : 1.25;
      ctx.setLineDash(z.type === "vehicle_lane" ? [6, 4] : []);
      ctx.fillRect(x, y, w, h);
      ctx.strokeRect(x, y, w, h);
      ctx.setLineDash([]);
      ctx.font = "600 10px Source Sans 3, sans-serif";
      ctx.fillStyle = "rgba(238,243,239,0.92)";
      const label = z.name || `Zona ${i + 1}`;
      ctx.fillText(label, x + 5, y + 12);
      if (selected) {
        const hs = ZONES_CANVAS_HANDLE;
        ctx.fillStyle = "rgba(232,93,4,0.95)";
        for (const hx of [x, x + w]) {
          for (const hy of [y, y + h]) {
            ctx.fillRect(hx - hs / 2, hy - hs / 2, hs, hs);
          }
        }
      }
    }

    if (els.zonesPreviewHint) {
      const hasVideo = video && video.videoWidth > 0 && !video.hidden;
      els.zonesPreviewHint.textContent = hasVideo
        ? "Tocá una zona · arrastrá para mover · esquinas para tamaño"
        : "Sin cámara: ajustá con el lienzo o los deslizadores abajo";
    }
  }

  function zonesCanvasPoint(ev) {
    const canvas = els.zonesCanvas;
    const rect = canvas.getBoundingClientRect();
    const clientX = ev.touches?.[0]?.clientX ?? ev.clientX;
    const clientY = ev.touches?.[0]?.clientY ?? ev.clientY;
    const px = ((clientX - rect.left) / rect.width) * canvas.width;
    const py = ((clientY - rect.top) / rect.height) * canvas.height;
    return { px, py, nx: px / canvas.width, ny: py / canvas.height };
  }

  function zonesCanvasHit(px, py) {
    const canvas = els.zonesCanvas;
    const cw = canvas.width;
    const ch = canvas.height;
    const hs = ZONES_CANVAS_HANDLE;
    for (let i = zonesCache.length - 1; i >= 0; i--) {
      const z = zonesCache[i];
      if (!z.enabled) continue;
      const r = zoneCanvasRect(z, cw, ch);
      if (i === selectedZoneIndex) {
        const corners = [
          { edge: "nw", cx: r.x, cy: r.y },
          { edge: "ne", cx: r.x + r.w, cy: r.y },
          { edge: "sw", cx: r.x, cy: r.y + r.h },
          { edge: "se", cx: r.x + r.w, cy: r.y + r.h },
        ];
        for (const c of corners) {
          if (Math.abs(px - c.cx) <= hs && Math.abs(py - c.cy) <= hs) {
            return { index: i, mode: "resize", edge: c.edge };
          }
        }
      }
      if (px >= r.x && px <= r.x + r.w && py >= r.y && py <= r.y + r.h) {
        return { index: i, mode: "move" };
      }
    }
    return null;
  }

  function syncZoneSlidersFromCache(index) {
    const row = els.zonesList?.querySelector(`[data-zi="${index}"]`);
    if (!row) return;
    const z = zonesCache[index];
    if (!z) return;
    const set = (attr, val) => {
      const el = row.querySelector(`[data-z="${attr}"]`);
      if (el) el.value = String(Math.round(val * 100));
    };
    set("x", z.x || 0);
    set("y", z.y || 0);
    set("w", z.w || 0.2);
    set("h", z.h || 0.2);
  }

  function startZonesCanvasLoop() {
    stopZonesCanvasLoop();
    const tick = () => {
      if (appMode !== "config" || document.querySelector("[data-cfg-section='zones']:not(.hidden)") == null) {
        zonesCanvasRaf = 0;
        return;
      }
      drawZonesEditorCanvas();
      zonesCanvasRaf = requestAnimationFrame(tick);
    };
    zonesCanvasRaf = requestAnimationFrame(tick);
  }

  function stopZonesCanvasLoop() {
    if (zonesCanvasRaf) {
      cancelAnimationFrame(zonesCanvasRaf);
      zonesCanvasRaf = 0;
    }
  }

  function bindZonesCanvasEvents() {
    const canvas = els.zonesCanvas;
    if (!canvas || canvas.dataset.bound) return;
    canvas.dataset.bound = "1";

    const onDown = (ev) => {
      if (ev.button !== undefined && ev.button !== 0) return;
      ev.preventDefault();
      zonesCache = readZonesFromEditor();
      const { px, py } = zonesCanvasPoint(ev);
      const hit = zonesCanvasHit(px, py);
      if (!hit) {
        selectedZoneIndex = -1;
        drawZonesEditorCanvas();
        return;
      }
      selectedZoneIndex = hit.index;
      const z = zonesCache[hit.index];
      zonesCanvasDrag = {
        mode: hit.mode,
        edge: hit.edge,
        index: hit.index,
        startX: z.x,
        startY: z.y,
        startW: z.w,
        startH: z.h,
        originPx: px,
        originPy: py,
      };
      drawZonesEditorCanvas();
    };

    const onMove = (ev) => {
      if (!zonesCanvasDrag) return;
      ev.preventDefault();
      const { px, py } = zonesCanvasPoint(ev);
      const canvasEl = els.zonesCanvas;
      const cw = canvasEl.width;
      const ch = canvasEl.height;
      const dx = (px - zonesCanvasDrag.originPx) / cw;
      const dy = (py - zonesCanvasDrag.originPy) / ch;
      const z = zonesCache[zonesCanvasDrag.index];
      if (!z) return;

      if (zonesCanvasDrag.mode === "move") {
        z.x = zonesCanvasDrag.startX + dx;
        z.y = zonesCanvasDrag.startY + dy;
      } else {
        const edge = zonesCanvasDrag.edge;
        let x1 = zonesCanvasDrag.startX;
        let y1 = zonesCanvasDrag.startY;
        let x2 = zonesCanvasDrag.startX + zonesCanvasDrag.startW;
        let y2 = zonesCanvasDrag.startY + zonesCanvasDrag.startH;
        if (edge.includes("n")) y1 = zonesCanvasDrag.startY + dy;
        if (edge.includes("s")) y2 = zonesCanvasDrag.startY + zonesCanvasDrag.startH + dy;
        if (edge.includes("w")) x1 = zonesCanvasDrag.startX + dx;
        if (edge.includes("e")) x2 = zonesCanvasDrag.startX + zonesCanvasDrag.startW + dx;
        if (x2 - x1 < 0.05) {
          if (edge.includes("w")) x1 = x2 - 0.05;
          else x2 = x1 + 0.05;
        }
        if (y2 - y1 < 0.05) {
          if (edge.includes("n")) y1 = y2 - 0.05;
          else y2 = y1 + 0.05;
        }
        z.x = x1;
        z.y = y1;
        z.w = x2 - x1;
        z.h = y2 - y1;
      }
      clampZoneNorm(z);
      syncZoneSlidersFromCache(zonesCanvasDrag.index);
      drawZonesEditorCanvas();
    };

    const onUp = () => {
      zonesCanvasDrag = null;
    };

    canvas.addEventListener("mousedown", onDown);
    canvas.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    canvas.addEventListener("touchstart", onDown, { passive: false });
    canvas.addEventListener("touchmove", onMove, { passive: false });
    window.addEventListener("touchend", onUp);
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
            <option value="restricted" ${z.type === "restricted" || !z.type ? "selected" : ""}>Restringida</option>
            <option value="vehicle_lane" ${z.type === "vehicle_lane" ? "selected" : ""}>Vía vehículos</option>
            <option value="machinery" ${z.type === "machinery" ? "selected" : ""}>Maquinaria</option>
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
    bindZonesCanvasEvents();
    requestAnimationFrame(() => drawZonesEditorCanvas());
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
    const drawBoxes = settings.showPpeBoxes && appMode === "live";
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
      appMode === "live" &&
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

  function applyHealth(health) {
    if (!health) return false;
    lastHealth = health;
    combinedInference = !!health.combined_inference;
    const idOn = !!els.chkIdentify?.checked;
    const idReady = !!health.identity_ready;
    const eppReady = !!health.model_ready;
    const ready = idOn ? idReady && eppReady : eppReady || idReady;
    els.modelStatus.classList.toggle("ready", ready);
    els.modelStatus.classList.toggle("error", !ready && !!health.warning);
    if (idOn) {
      if (idReady && eppReady) {
        els.modelStatusText.textContent = `ID+EPP listos · ${health.workers_ready || 0} persona(s)`;
      } else if (idReady) {
        els.modelStatusText.textContent = "ID lista · EPP cargando (10–30 s)…";
      } else if (eppReady) {
        els.modelStatusText.textContent = "EPP lista · ID cargando…";
      } else {
        els.modelStatusText.textContent = health.warning || "Cargando ID+EPP…";
      }
    } else if (ready) {
      els.modelStatusText.textContent = `IA lista · ${health.model || "EPP"}`;
    } else {
      els.modelStatusText.textContent = health.warning || "Cargando IA…";
    }
    if (els.fpsLabel && health.build) {
      const mode =
        idOn && combinedInference ? "ID+EPP·1" : idOn ? "ID+EPP" : "EPP";
      els.fpsLabel.textContent = `${health.build} · ${mode}`;
    }
    enterprise.updateEnterpriseHints(health, { combinedInference, els });
    showPersistBanner(health);
    return ready;
  }

  async function boot() {
    await ensureAuth();
    try {
      const health = await api("/api/health");
      applyHealth(health);
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
    } catch (err) {
      console.error(err);
    }

    try {
      const cat = await api("/api/ppe/catalog");
      ppeCatalog = cat.items || [];
    } catch (_) {
      ppeCatalog = catalogItems();
    }

    bindPpeChipContainer(els.requiredChips);
    bindPpeChipContainer(els.cfgPpeChips);
    renderProfile();

    await refreshWorkers();
    await refreshTeach();
    await refreshScans();
    await refreshCameras();
    await loadZones();
    loadSettings();
    await loadPrivacyServer();
    settings.fullscreenDefault = false;
    if (els.chkFullscreen) els.chkFullscreen.checked = false;
    syncSettingsForm();
    applyMobileChrome();
    applyGuideMode();
    setAppMode("live");
    if (settings.kioskMode) setKioskMode(true);
    hideLiveVideo();
    await refreshCameraPermissionHint();
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.getRegistrations().then((regs) => {
        regs.forEach((r) => r.unregister().catch(() => {}));
      });
      setTimeout(() => {
        navigator.serviceWorker.register("/assets/sw.js?v=42").catch(() => {});
      }, 400);
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
    els.profileDesc.textContent = p.description || p.name;
    const req = getEffectiveRequired(p.id);
    const custom = settings.ppeByProfile && Object.prototype.hasOwnProperty.call(settings.ppeByProfile, p.id);
    const hint = $("#ppeSelectHint");
    if (hint) {
      hint.textContent = custom
        ? `Personalizado (${req.length} obligatorio${req.length === 1 ? "" : "s"}). Tocá para cambiar.`
        : "Tocá cada ítem para marcarlo obligatorio u opcional.";
    }
    renderPpeSelector(els.requiredChips, p.id);
    renderPpeSelector(els.cfgPpeChips, p.id);
  }

  function setConfigSection(sec) {
    const id = ["guides", "audio", "zones", "monitor", "privacy", "enterprise", "audit"].includes(sec)
      ? sec
      : "guides";
    try {
      localStorage.setItem("vigiepp-cfg-sec", id);
    } catch (_) {}
    $$("[data-cfg-section]").forEach((el) => {
      el.classList.toggle("hidden", el.getAttribute("data-cfg-section") !== id);
    });
    $$(".cfg-nav-btn").forEach((btn) => {
      const on = btn.getAttribute("data-cfg-sec") === id;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
    const panel = $("#sidePanel");
    if (panel && appMode === "config") panel.scrollTop = 0;
    const block = $("#configBlock");
    if (block) block.scrollTop = 0;
    if (id === "audit") refreshAudit();
    if (id === "enterprise") {
      refreshSitesUi();
      refreshEhsUi();
    }
    if (id === "zones") {
      bindZonesCanvasEvents();
      requestAnimationFrame(() => {
        syncZonesCanvasSize();
        drawZonesEditorCanvas();
        startZonesCanvasLoop();
      });
    } else {
      stopZonesCanvasLoop();
    }
  }

  function enableIdentifyForPorteria(reason = "") {
    if (els.chkIdentify) els.chkIdentify.checked = true;
    settings.identifyDefault = true;
    if (els.cfgIdentifyDefault) els.cfgIdentifyDefault.checked = true;
    saveSettings(true);
    if (els.speedHint && reason) els.speedHint.textContent = reason;
  }

  function hasReadyWorkers() {
    return (workersCache || []).some(
      (w) =>
        w.active !== false &&
        (w.ready === true || (w.face_samples || 0) >= (w.min_samples_ready || 4))
    );
  }

  function setAppMode(mode) {
    const prevMode = appMode;
    if (mode === "monitor") mode = "live";
    appMode = mode;

    if (mode !== "mass") stopMassLoop();
    if (mode !== "live" && mode !== "identity" && mode !== "teach") {
      stopDetectLoop();
      if (mode !== "live") stopRtsp();
    }

    document.body.classList.remove(
      "mode-live",
      "mode-monitor",
      "mode-mass",
      "mode-devices",
      "mode-identity",
      "mode-teach",
      "mode-config",
      "mode-reports"
    );
    document.body.classList.add(`mode-${mode}`);

    $$(".mode-btn").forEach((b) => {
      const on = b.dataset.mode === mode;
      b.classList.toggle("active", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });

    els.monitorToolbar?.classList.toggle("hidden", mode !== "live");
    $("#massToolbar")?.classList.toggle("hidden", mode !== "mass");

    $("#liveWorkspace")?.classList.toggle("hidden", !isViewportMode());
    $("#massWorkspace")?.classList.toggle("hidden", mode !== "mass");
    $("#devicesWorkspace")?.classList.toggle("hidden", mode !== "devices");

    const stage = $(".stage");
    if (stage) stage.classList.toggle("is-reports", mode === "reports");
    if (els.reportsDesk) els.reportsDesk.classList.toggle("hidden", mode !== "reports");

    const panel = $("#sidePanel");
    if (panel) panel.dataset.mode = mode;
    const ctx = $("#panelContext");
    if (ctx) {
      const labels = {
        live: "Vigilancia en vivo · un canal o webcam",
        mass: "Vigilancia masiva · NVR / multi-cámara",
        devices: "Equipos de video · NVR Dahua / Hikvision",
        identity: "Enrolar e identificar personas",
        teach: "Entrenar ropa y EPP del modelo",
        reports: "Estadísticas, informes y notificaciones",
        config: "Ajustes de silueta, audio, zonas y privacidad",
      };
      ctx.textContent = labels[mode] || labels.config;
    }

    $$(".panel-section").forEach((el) => {
      const show = el.getAttribute("data-show");
      if (!show) return;
      el.classList.toggle("hidden", show !== mode);
    });

    $$("[data-live-only]").forEach((el) => {
      el.classList.toggle("hidden", !isLiveMode());
    });

    if (mode === "live") {
      setSource(
        sourceMode === "identity" || sourceMode === "teach" || sourceMode === "config" || sourceMode === "reports"
          ? "camera"
          : sourceMode
      );
      if (prevMode === "identity" && hasReadyWorkers()) {
        enableIdentifyForPorteria("Identificación ON · volviste de Personas");
      }
    } else if (mode === "identity") setSource("identity");
    else if (mode === "teach") setSource("teach");
    else if (mode === "reports") setSource("reports");
    else if (mode === "config") setSource("config");
    else if (mode === "mass") setSource("mass");
    else if (mode === "devices") setSource("devices");

    applyGuideMode();
    if (mode === "identity") refreshWorkers();
    if (mode === "teach") refreshTeach();
    if (mode === "config") {
      loadZones();
      setConfigSection(localStorage.getItem("vigiepp-cfg-sec") || "guides");
    } else {
      stopZonesCanvasLoop();
    }
    if (mode === "mass") {
      fillMassProfiles();
      refreshWatchlistUi();
      renderMassGridPlaceholder();
    }
    if (mode === "devices") {
      refreshNvrDevices();
      refreshWatchlistUi();
    }
    if (mode === "reports") {
      fillRepProfiles();
      openReport(currentRep || "overview");
    }
    requestAnimationFrame(() => syncCanvasSize());
  }

  function setSource(mode) {
    sourceMode = mode;
    $$(".tab").forEach((t) => {
      if (!t.dataset.source) return;
      const on = t.dataset.source === mode;
      t.classList.toggle("active", on);
      t.setAttribute("aria-selected", on ? "true" : "false");
    });
    const showCamBar = mode === "camera" || mode === "identity" || mode === "teach";
    els.cameraControls.classList.toggle("hidden", !showCamBar);
    els.rtspControls.classList.toggle("hidden", mode !== "rtsp");
    els.uploadControls.classList.toggle("hidden", mode !== "upload");
    els.identityControls.classList.toggle("hidden", mode !== "identity");
    if (els.teachControls) els.teachControls.classList.toggle("hidden", mode !== "teach");
    if (els.teachExtraControls) els.teachExtraControls.classList.toggle("hidden", mode !== "teach");
    if (els.configControls) els.configControls.classList.toggle("hidden", mode !== "config");
    $("#massToolbar")?.classList.toggle("hidden", mode !== "mass");

    if (mode === "mass" || mode === "devices") {
      stopDetectLoop();
      stopRtsp();
    }

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
      // Volver de Personas/Teach: restaurar panel de monitoreo y reanudar EPP
      if (els.complianceBox) els.complianceBox.dataset.state = "idle";
      if (els.complianceValue) els.complianceValue.textContent = "En espera";
      if (els.complianceSummary) {
        els.complianceSummary.textContent = els.chkIdentify?.checked
          ? "Iniciá el monitoreo para evaluar EPP e identidad."
          : "Marcá «Identificar rostro» abajo para reconocer personas enroladas.";
      }
      if (els.statusPill) els.statusPill.textContent = "Standby";
      if (els.detList) els.detList.innerHTML = `<li class="muted">Sin detecciones</li>`;
      if (els.alertList) els.alertList.innerHTML = `<li class="muted">Sin alertas</li>`;
      if (appMode === "live" && mediaStream && !detectLoopOn) {
        startDetectLoop();
      }
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

    const gateOn = !!settings.silhouetteGate && !!settings.silhouetteEnabled && appMode === "live";
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
    if (appMode === "live" && hasPeople && !ok) {
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
            const who = id?.known && id?.name ? `${displayPersonName(id.name)}: ` : "";
            return `<li class="warn">${who}${a}</li>`;
          })
          .join("")
      : `<li class="muted">Sin alertas</li>`;

    if (payload.identity) {
      lastIdentity = payload.identity;
      setIdentityCard(payload.identity);
      if (payload.identity.faces_detected > 0 && settings.faceGuide && appMode === "live") {
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
    } else if (appMode === "live" && !els.chkIdentify?.checked) {
      els.identityName.textContent = "ID apagada";
      els.identityRut.textContent = "Marcá «Identificar rostro» abajo";
      if (els.identityMethod) els.identityMethod.textContent = "";
    }

    const ms = Math.round(performance.now() - t0);
    els.fpsLabel.textContent = `${ms} ms UI`;
  }

  /** Títulos médicos → término de faena (expertos SSO / EPP). */
  function displayPersonName(name) {
    let n = String(name || "").trim();
    if (!n) return n;
    n = n.replace(/^(dra\.?|dr\.?|doctora|doctor)\b\.?\s*/i, "Especialista ");
    n = n.replace(/\s{2,}/g, " ").trim();
    return n;
  }

  function normalizePersonNameForSave(name) {
    return displayPersonName(name);
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
    const displayName = displayPersonName(identity.name);
    els.identityName.textContent = displayName || (known ? "—" : "Desconocido");
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
      const why =
        identity.gallery_size === 0
          ? "Sin plantillas en servidor. Re-enrolá en Personas"
          : identity.reject_reason || "sin coincidencia";
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
      if (!video.videoWidth) return resolve(null);
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
    if (faceBox) lastFaceBox = faceBox;
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
    lastIdentity = card;
    setIdentityCard(card);
    drawDetections([], lastFrameSize.w, lastFrameSize.h, card);
    if (card.known) maybeRefreshScans();
    return data;
  }

  function maybeRefreshScans() {
    const now = Date.now();
    if (now - lastScanRefreshAt < 10000) return;
    lastScanRefreshAt = now;
    refreshScans().catch(() => {});
  }

  async function tickDetect() {
    if (!isLiveMode() || sourceMode !== "camera") return;
    const wantId = !!els.chkIdentify?.checked;
    const now = Date.now();

    if (wantId && combinedInference) {
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
      const dueId = eppStreak >= 2 && now - lastIdentifyAt >= 2800;
      if (dueId) {
        lastIdentifyAt = now;
        eppStreak = 0;
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
      eppStreak += 1;
      return;
    }

    eppStreak = 0;
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
      if (!opts.silentDetect && appMode === "live" && sourceMode === "camera") {
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
    const wasScanning = detectLoopOn;
    stopDetectLoop();
    try {
      mediaStream = await openCameraStream(preferredFacing);
      els.liveVideo.srcObject = mediaStream;
      await els.liveVideo.play().catch(() => {});
      showLive();
      els.btnStartCam.disabled = true;
      els.btnStopCam.disabled = false;
      if (wasScanning && appMode === "live" && sourceMode === "camera") {
        startDetectLoop();
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

  async function refreshAudit() {
    const list = $("#auditList");
    if (!list) return;
    try {
      const data = await api("/api/audit?limit=60");
      const ev = data.events || [];
      list.innerHTML = ev.length
        ? ev
            .map((e) => {
              const ts = (e.ts || "").replace("T", " ").slice(0, 19);
              return `<li><span>${escapeHtml(e.action)}</span><span class="conf">${escapeHtml(ts)} · ${escapeHtml(e.detail || "")}</span></li>`;
            })
            .join("")
        : `<li class="muted">Sin eventos</li>`;
    } catch (err) {
      list.innerHTML = `<li class="muted">${escapeHtml(err.message || "No se pudo cargar")}</li>`;
    }
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
      const wantId = !!els.chkIdentify?.checked && Date.now() - lastIdentifyAt > 2200;
      if (wantId) lastIdentifyAt = Date.now();
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
    if (cloud.configured || (health?.data_persistent && !health?.data_ephemeral_risk)) {
      el.classList.add("hidden");
      el.textContent = "";
      return;
    }
    el.classList.remove("hidden");
    el.innerHTML =
      "<strong>Falta volumen durable:</strong> Render Free no guarda disco. " +
      "Solución gratis: corré <code>activate-free-durable.ps1</code> (Hugging Face, sin pago). " +
      "Las personas quedan en un dataset privado y sobreviven al sleep.";
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
              ? `<img class="worker-photo" src="${w.photo_url}?t=${encodeURIComponent(w.last_seen || w.face_samples || 0)}" alt="Foto de ${escapeHtml(w.name || "trabajador")}" />`
              : `<div class="worker-photo placeholder" aria-hidden="true"></div>`;
            const qn = w.quality || 0;
            const ready =
              w.ready === true ||
              ((w.face_samples || 0) >= (w.min_samples_ready || 4) && (w.embedding_count || w.face_samples || 0) >= 3);
            const qLabel = qualityLabel(qn, ready);
            const consentLabel = w.consent_ok
              ? `consentimiento ${formatLastSeen(w.consent_at)}`
              : "sin consentimiento";
            return `<li data-worker-id="${w.id}" class="${active ? "" : "is-inactive"}">
              ${photo}
              <div class="worker-meta">
                <strong>${escapeHtml(displayPersonName(w.name) || "Sin nombre")}${active ? "" : " · inactivo"}${ready ? "" : " · incompleto"}</strong>
                <span class="conf">${escapeHtml(w.rut || "—")}${w.group ? " · " + escapeHtml(w.group) : ""}</span>
                <span class="conf">${w.face_samples || 0}/4 muestras · calidad ${qn}% (${qLabel}) · ${formatLastSeen(w.last_seen)}</span>
                <span class="conf">${consentLabel}</span>
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
    const name = prompt("Nombre (usá «Especialista …» en vez de Dr./Dra.)", displayPersonName(w.name || ""));
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
        body: JSON.stringify({
          name: normalizePersonNameForSave(name.trim()),
          rut: rut.trim(),
          group: group.trim(),
        }),
      });
      if (els.enrollCoach) {
        els.enrollCoach.textContent = `Actualizado: ${displayPersonName(data.worker?.name || name)}`;
      }
      if (data.worker) {
        els.workerName.value = displayPersonName(data.worker.name || "");
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
      setAppMode("live");
      if (els.chkIdentify) {
        els.chkIdentify.checked = true;
        settings.identifyDefault = true;
      }
    }
  }

  async function requestAdminPinToExitKiosk() {
    const pin = window.prompt("Salir de portería requiere PIN de administrador:");
    if (pin == null) return false;
    if (!String(pin).trim()) return false;
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin: String(pin).trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        window.alert(data.detail || "PIN incorrecto");
        return false;
      }
      if ((data.role || "") !== "admin") {
        window.alert("Solo el PIN de administrador puede salir del modo portería.");
        return false;
      }
      if (data.token) sessionStorage.setItem("vigiepp.token", data.token);
      applyRoleUI("admin");
      return true;
    } catch (err) {
      window.alert(err.message || "Error de red");
      return false;
    }
  }

  async function exitKioskSafe() {
    if (!settings.kioskMode) return;
    const ok = await requestAdminPinToExitKiosk();
    if (ok) setKioskMode(false);
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
      name.textContent = id?.known && id?.name ? displayPersonName(id.name) : hasPeople ? "Sin identificar" : "Acercá a la cámara";
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
    if (!els.chkBiometricConsent?.checked) {
      if (els.enrollCoach) {
        els.enrollCoach.textContent = "Marcá el consentimiento biométrico antes de enrolar.";
      }
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
      const name = normalizePersonNameForSave(els.workerName.value.trim());
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
          fd.append("consent", "true");
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
          ? `Listo ${okCount}/4. Andá a Monitoreo: la identificación ya quedó activa.`
          : `Incompleto ${okCount}/4. Rehacé poses con luz frontal (calidad obligatoria).`;
      if (els.enrollCoach) els.enrollCoach.textContent = done;
      if (okCount >= 4) {
        enableIdentifyForPorteria("Identificación ON tras enrolar");
      }
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
    const name = normalizePersonNameForSave(els.workerName.value.trim());
    const rut = els.workerRut.value.trim();
    if (!name && !rut) {
      if (els.enrollCoach) els.enrollCoach.textContent = "Escribí nombre o RUT antes de adjuntar fotos";
      return;
    }
    if (!els.chkBiometricConsent?.checked) {
      if (els.enrollCoach) els.enrollCoach.textContent = "Marcá el consentimiento biométrico antes de adjuntar fotos.";
      return;
    }
    const files = [...(fileList || [])].slice(0, 40);
    if (!files.length) return;
    if (els.enrollCoach) els.enrollCoach.textContent = `Cargando ${files.length} fotos de rostro…`;
    const fd = new FormData();
    fd.append("name", name);
    fd.append("rut", rut);
    fd.append("consent", "true");
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
    stopDetectLoop();
    if (!mediaStream) await startCamera({ silentDetect: true });
    showLive();
    try {
      const data = await identifyLiveFrame({ flash: true });
      if (!data) {
        els.identityMethod.textContent = els.identityMethod.textContent || "Sin resultado. Reintentá.";
      } else if (data.image_b64) {
        els.annotatedImg.hidden = false;
        els.annotatedImg.src = `data:image/jpeg;base64,${data.image_b64}`;
        await sleep(1200);
        showLive();
      }
    } catch (err) {
      els.identityMethod.textContent = err.message || "No se pudo identificar";
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
      const gate = ac.gate || {};
      const mb = gate.modbus || {};
      const hd = gate.http_dual || {};
      const wg = gate.wiegand || {};
      const et = notifConfig.email_transport || {};
      const emailHint =
        et.mode === "resend"
          ? "Email real vía Resend"
          : et.mode === "smtp"
            ? `Email real vía SMTP (${et.smtp_host || "host"})`
            : "Sin SMTP/Resend → solo abre mailto en el navegador";
      const driver = gate.driver || "esp32";
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
          <label><span>WhatsApp Business Cloud (Meta)</span>
            <input type="checkbox" id="nWaCloudEn" ${ch.whatsapp_cloud?.enabled ? "checked" : ""}/> Activar
            <small class="card-meta">Token en WHATSAPP_TOKEN / VIGIEPP_WHATSAPP_TOKEN del servidor</small>
            <input type="text" id="nWaCloudPhoneId" placeholder="Phone number ID" value="${ch.whatsapp_cloud?.phone_number_id || ""}"/>
            <input type="text" id="nWaCloudTo" placeholder="+56912345678 o varios separados por coma" value="${ch.whatsapp_cloud?.to || ""}"/>
          </label>
          <label><span>Email</span>
            <input type="checkbox" id="nEmEn" ${ch.email?.enabled ? "checked" : ""}/> Activar
            <input type="email" id="nEmTo" placeholder="seguridad@empresa.cl" value="${ch.email?.to || ""}"/>
            <input type="email" id="nEmCc" placeholder="cc opcional" value="${ch.email?.cc || ""}"/>
          </label>
          <p class="card-kicker">Driver de acceso físico</p>
          <label><span>Torniquete / relé / Wiegand</span>
            <select id="nGateDriver">
              <option value="esp32" ${driver === "esp32" ? "selected" : ""}>ESP32 HTTP (/ok /alarma)</option>
              <option value="modbus" ${driver === "modbus" ? "selected" : ""}>Modbus TCP (coils)</option>
              <option value="http_dual" ${driver === "http_dual" ? "selected" : ""}>HTTP dual (allow/deny URL)</option>
              <option value="wiegand" ${driver === "wiegand" ? "selected" : ""}>Gateway Wiegand HTTP</option>
            </select>
            <input type="checkbox" id="nGateHwEn" ${gate.enabled ? "checked" : ""}/> Activar driver
          </label>
          <div id="nGateEsp32" class="${driver === "esp32" ? "" : "hidden"}">
            <p class="card-kicker">ESP32 / baliza</p>
            <input type="url" id="nHwUrl" placeholder="http://192.168.1.50" value="${gate.esp32?.base_url || ac.hardware?.base_url || ""}"/>
            <label class="check"><input type="checkbox" id="nHwBad" ${gate.on_non_compliant !== false ? "checked" : ""}/> Alarma en incumplimiento EPP</label>
            <label class="check"><input type="checkbox" id="nHwUnk" ${gate.on_unknown_face !== false ? "checked" : ""}/> Alarma en rostro desconocido</label>
            <label class="check"><input type="checkbox" id="nHwOk" ${gate.auto_ok !== false ? "checked" : ""}/> /ok automático si EPP cumple</label>
          </div>
          <div id="nGateModbus" class="${driver === "modbus" ? "" : "hidden"}">
            <p class="card-kicker">Modbus TCP</p>
            <input type="text" id="nMbHost" placeholder="192.168.1.20" value="${mb.host || ""}"/>
            <input type="number" id="nMbPort" placeholder="502" value="${mb.port || 502}"/>
            <input type="number" id="nMbUnit" placeholder="Unit ID" value="${mb.unit_id || 1}"/>
            <input type="number" id="nMbCoilAllow" placeholder="Coil allow" value="${mb.coil_allow || 0}"/>
            <input type="number" id="nMbCoilDeny" placeholder="Coil deny" value="${mb.coil_deny || 1}"/>
          </div>
          <div id="nGateHttp" class="${driver === "http_dual" ? "" : "hidden"}">
            <p class="card-kicker">HTTP dual</p>
            <input type="url" id="nHdAllow" placeholder="URL allow" value="${hd.allow_url || ""}"/>
            <input type="url" id="nHdDeny" placeholder="URL deny" value="${hd.deny_url || ""}"/>
          </div>
          <div id="nGateWiegand" class="${driver === "wiegand" ? "" : "hidden"}">
            <p class="card-kicker">Wiegand gateway</p>
            <input type="url" id="nWgBase" placeholder="http://192.168.1.30" value="${wg.base_url || ""}"/>
            <input type="text" id="nWgAllow" placeholder="/open" value="${wg.allow_path || "/open"}"/>
            <input type="text" id="nWgDeny" placeholder="/close" value="${wg.deny_path || "/close"}"/>
          </div>
          <div class="rep-actions" style="margin:0.5rem 0 1rem">
            <button type="button" class="btn secondary" id="btnHwAlarma">Probar deny</button>
            <button type="button" class="btn secondary" id="btnHwOk">Probar allow</button>
          </div>
          <pre class="rep-pre" id="hwTestOut" style="display:none">—</pre>
          <p class="card-kicker">Abrir acceso (portería lógica)</p>
          <label><span>Control de acceso</span>
            <input type="checkbox" id="nAcEn" ${ac.enabled ? "checked" : ""}/> Activar gate
            <small class="card-meta">Allow solo si identidad conocida + EPP OK. Driver físico según selección arriba.</small>
            <label class="check"><input type="checkbox" id="nAcId" ${ac.require_identity !== false ? "checked" : ""}/> Exigir identidad</label>
            <label class="check"><input type="checkbox" id="nAcNf" ${ac.notify !== false ? "checked" : ""}/> Notificar decisión</label>
          </label>
          <button class="btn primary" type="submit">Guardar canales</button>
        </form>`;
      const toggleGatePanels = () => {
        const d = $("#nGateDriver")?.value || "esp32";
        $("#nGateEsp32")?.classList.toggle("hidden", d !== "esp32");
        $("#nGateModbus")?.classList.toggle("hidden", d !== "modbus");
        $("#nGateHttp")?.classList.toggle("hidden", d !== "http_dual");
        $("#nGateWiegand")?.classList.toggle("hidden", d !== "wiegand");
      };
      $("#nGateDriver")?.addEventListener("change", toggleGatePanels);
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
            whatsapp_cloud: {
              enabled: $("#nWaCloudEn").checked,
              phone_number_id: $("#nWaCloudPhoneId").value.trim(),
              to: $("#nWaCloudTo").value.trim(),
            },
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
              enabled: $("#nGateDriver").value === "esp32" && $("#nGateHwEn").checked,
              base_url: $("#nHwUrl").value.trim(),
              alarma_path: "/alarma",
              ok_path: "/ok",
              method: "GET",
              on_non_compliant: $("#nHwBad").checked,
              on_unknown_face: $("#nHwUnk").checked,
              auto_ok: $("#nHwOk").checked,
            },
            gate: {
              enabled: $("#nGateHwEn").checked,
              driver: $("#nGateDriver").value,
              on_non_compliant: $("#nHwBad").checked,
              on_unknown_face: $("#nHwUnk").checked,
              auto_ok: $("#nHwOk").checked,
              esp32: {
                enabled: $("#nGateDriver").value === "esp32" && $("#nGateHwEn").checked,
                base_url: $("#nHwUrl").value.trim(),
                alarma_path: "/alarma",
                ok_path: "/ok",
                method: "GET",
              },
              modbus: {
                host: $("#nMbHost").value.trim(),
                port: Number($("#nMbPort").value) || 502,
                unit_id: Number($("#nMbUnit").value) || 1,
                coil_allow: Number($("#nMbCoilAllow").value) || 0,
                coil_deny: Number($("#nMbCoilDeny").value) || 1,
              },
              http_dual: {
                allow_url: $("#nHdAllow").value.trim(),
                deny_url: $("#nHdDeny").value.trim(),
              },
              wiegand: {
                base_url: $("#nWgBase").value.trim(),
                allow_path: $("#nWgAllow").value.trim() || "/open",
                deny_path: $("#nWgDeny").value.trim() || "/close",
              },
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
  document.addEventListener("click", (ev) => {
    const btn = ev.target.closest(".cfg-nav-btn");
    if (!btn) return;
    const sec = btn.getAttribute("data-cfg-sec");
    if (sec) setConfigSection(sec);
  });
  $$(".rep-item").forEach((b) => b.addEventListener("click", () => openReport(b.dataset.rep)));
  if (els.btnRepRefresh) els.btnRepRefresh.addEventListener("click", () => openReport(currentRep || "overview"));
  if (els.repDays) els.repDays.addEventListener("change", () => openReport(currentRep || "overview"));
  if (els.repProfile) els.repProfile.addEventListener("change", () => openReport(currentRep || "overview"));
  $$(".tab").forEach((t) => {
    if (t.dataset.source) t.addEventListener("click", () => setSource(t.dataset.source));
  });
  els.profileSelect.addEventListener("change", renderProfile);
  els.btnResetPpe?.addEventListener("click", () => {
    resetProfileRequired(els.profileSelect.value);
    renderProfile();
  });
  els.btnCfgResetPpe?.addEventListener("click", () => {
    resetProfileRequired(els.profileSelect.value);
    renderProfile();
  });
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
  $("#cfgQrOnlyMode")?.addEventListener("change", () => readSettingsFromForm());
  $("#cfgRetentionDays")?.addEventListener("input", () => readSettingsFromForm());
  $("#btnAuditRefresh")?.addEventListener("click", () => refreshAudit());
  $("#cfgSiteSelect")?.addEventListener("change", async (ev) => {
    const siteId = ev.target.value;
    try {
      await api("/api/sites/active", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ site_id: siteId }),
      });
      const health = await api("/api/health");
      applyHealth(health);
      await refreshWorkers();
      await loadZones();
      els.repSideSummary.textContent = "Faena activa actualizada";
    } catch (err) {
      els.repSideSummary.textContent = err.message || "Error al cambiar faena";
    }
  });
  $("#btnSiteCreate")?.addEventListener("click", async () => {
    const name = ($("#cfgSiteNewName")?.value || "").trim();
    if (!name) return;
    try {
      await api("/api/sites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      $("#cfgSiteNewName").value = "";
      await refreshSitesUi();
      els.repSideSummary.textContent = `Faena «${name}» creada`;
    } catch (err) {
      els.repSideSummary.textContent = err.message || "Error al crear faena";
    }
  });
  $("#btnOidcLogin")?.addEventListener("click", async () => {
    try {
      const data = await api("/api/auth/oidc/login");
      if (data.url) window.location.href = data.url;
    } catch (err) {
      els.repSideSummary.textContent = err.message || "SSO no disponible";
    }
  });
  $("#btnEhsSave")?.addEventListener("click", async () => {
    try {
      await saveEhsConfig();
      els.repSideSummary.textContent = "Conectores EHS guardados";
    } catch (err) {
      els.repSideSummary.textContent = err.message || "Error EHS";
    }
  });
  $("#btnEhsTest")?.addEventListener("click", async () => {
    try {
      const r = await api("/api/ehs/test/webhook", { method: "POST" });
      els.repSideSummary.textContent = r.ok ? `EHS webhook OK: ${r.detail || ""}` : "EHS webhook falló";
    } catch (err) {
      els.repSideSummary.textContent = err.message || "EHS webhook falló";
    }
  });
  $("#btnEhsTestSafety")?.addEventListener("click", async () => {
    try {
      const r = await api("/api/ehs/test/safetycloud", { method: "POST" });
      els.repSideSummary.textContent = r.ok ? `SafetyCloud OK: ${r.detail || ""}` : "SafetyCloud falló";
    } catch (err) {
      els.repSideSummary.textContent = err.message || "SafetyCloud falló";
    }
  });
  $("#btnEhsTestSap")?.addEventListener("click", async () => {
    try {
      const r = await api("/api/ehs/test/sap_ewm", { method: "POST" });
      els.repSideSummary.textContent = r.ok ? `SAP EWM OK: ${r.detail || ""}` : "SAP EWM falló";
    } catch (err) {
      els.repSideSummary.textContent = err.message || "SAP EWM falló";
    }
  });
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
    selectedZoneIndex = zonesCache.length - 1;
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
    if (selectedZoneIndex === i) selectedZoneIndex = -1;
    else if (selectedZoneIndex > i) selectedZoneIndex -= 1;
    renderZonesEditor();
  });
  els.zonesList?.addEventListener("input", (e) => {
    if (!e.target.matches("[data-z]")) return;
    zonesCache = readZonesFromEditor();
    const row = e.target.closest(".zone-row");
    if (row) {
      const i = Number(row.getAttribute("data-zi"));
      if (!Number.isNaN(i)) selectedZoneIndex = i;
    }
    drawZonesEditorCanvas();
  });
  els.zonesList?.addEventListener("change", (e) => {
    if (!e.target.matches("[data-z='en'], [data-z='type'], [data-z='name']")) return;
    zonesCache = readZonesFromEditor();
    drawZonesEditorCanvas();
  });

  $("#btnKiosk")?.addEventListener("click", () => {
    if (settings.kioskMode) {
      exitKioskSafe();
    } else {
      setKioskMode(true);
    }
  });
  $("#btnKioskExit")?.addEventListener("click", () => {
    exitKioskSafe();
  });
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && settings.kioskMode) {
      e.preventDefault();
      exitKioskSafe();
    }
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

  $("#btnConsentExport")?.addEventListener("click", () => {
    downloadUrl("/api/identity/consent.csv");
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

  // ── Vigilancia masiva + NVR / DVR ─────────────────────────────────────────
  let massLoopOn = false;
  let massTimer = null;
  let watchlistCache = [];
  let nvrDevicesCache = [];

  function fillMassProfiles() {
    const massSel = $("#massProfileSelect");
    const src = els.profileSelect;
    if (!massSel || !src) return;
    massSel.innerHTML = src.innerHTML;
    if (src.value) massSel.value = src.value;
  }

  function renderMassGridPlaceholder() {
    const grid = $("#massGrid");
    if (!grid || watchlistCache.length) return;
    grid.innerHTML = `<p class="muted mass-empty">Agregá canales en <b>Equipos</b> o importá un NVR Dahua/Hikvision.</p>`;
  }

  function renderMassGrid(cells) {
    const grid = $("#massGrid");
    if (!grid) return;
    if (!cells?.length) {
      renderMassGridPlaceholder();
      return;
    }
    grid.innerHTML = cells
      .map((c) => {
        const cls = !c.connected ? "offline" : c.compliant ? "ok" : c.ok ? "bad" : "offline";
        const status = !c.connected
          ? "Sin señal"
          : c.compliant
            ? "Cumple"
            : `Falta: ${(c.missing || []).join(", ") || "EPP"}`;
        const thumb = c.thumb ? `data:image/jpeg;base64,${c.thumb}` : "";
        return `<div class="mass-cell ${cls}" data-mass-id="${escapeHtml(c.id || "")}">
          ${thumb ? `<img src="${thumb}" alt="Vista ${escapeHtml(c.name || "canal")} — ${escapeHtml(status)}" />` : `<div class="mass-cell-meta" style="top:40%">Sin imagen</div>`}
          <div class="mass-cell-meta"><strong>${escapeHtml(c.name || "Canal")}</strong> · ${escapeHtml(status)}</div>
        </div>`;
      })
      .join("");
    const sum = $("#massSummaryText");
    if (sum) {
      const online = cells.filter((c) => c.connected).length;
      const alerts = cells.filter((c) => c.connected && !c.compliant).length;
      sum.textContent = `${cells.length} canales · ${online} en línea · ${alerts} alertas EPP`;
    }
  }

  async function refreshWatchlistUi() {
    try {
      const data = await api("/api/watchlist");
      watchlistCache = data.channels || [];
      const list = $("#watchlistList");
      if (list) {
        list.innerHTML =
          watchlistCache.length
            ? watchlistCache
                .map(
                  (c) =>
                    `<li><span>${escapeHtml(c.name)}</span><span class="conf">${c.enabled ? "ON" : "off"} · ${escapeHtml((c.url || "").slice(0, 42))}…</span></li>`
                )
                .join("")
            : `<li class="muted">Sin canales</li>`;
      }
    } catch (err) {
      const list = $("#watchlistList");
      if (list) list.innerHTML = `<li class="muted">${escapeHtml(err.message)}</li>`;
    }
  }

  async function refreshNvrDevices() {
    try {
      const data = await api("/api/nvr/devices");
      nvrDevicesCache = data.devices || [];
      const list = $("#nvrDeviceList");
      if (!list) return;
      list.innerHTML =
        nvrDevicesCache.length
          ? nvrDevicesCache
              .map(
                (d) =>
                  `<li><span>${escapeHtml(d.name)} (${escapeHtml(d.vendor)})</span><span class="conf">${d.channel_count || 0} ch · ${escapeHtml(d.host || "")}</span></li>`
              )
              .join("")
          : `<li class="muted">Sin NVR registrados</li>`;
    } catch (err) {
      const list = $("#nvrDeviceList");
      if (list) list.innerHTML = `<li class="muted">${escapeHtml(err.message)}</li>`;
    }
  }

  async function runMassScan() {
    const profile = $("#massProfileSelect")?.value || els.profileSelect?.value || "general";
    const q = new URLSearchParams({ profile, required: requiredQueryValue() });
    const data = await api(`/api/surveillance/mass/scan?${q}`, { method: "POST" });
    renderMassGrid(data.cells || []);
    return data;
  }

  function startMassLoop() {
    if (massLoopOn) return;
    massLoopOn = true;
    $("#btnMassStart")?.setAttribute("disabled", "true");
    $("#btnMassStop")?.removeAttribute("disabled");
    const tick = async () => {
      if (!massLoopOn) return;
      try {
        await runMassScan();
      } catch (err) {
        const hint = $("#massStatusHint");
        if (hint) hint.textContent = err.message || "Error en barrido";
      }
      if (massLoopOn) massTimer = setTimeout(tick, 4000);
    };
    tick();
  }

  function stopMassLoop() {
    massLoopOn = false;
    if (massTimer) {
      clearTimeout(massTimer);
      massTimer = null;
    }
    $("#btnMassStart")?.removeAttribute("disabled");
    $("#btnMassStop")?.setAttribute("disabled", "true");
  }

  $("#btnMassStart")?.addEventListener("click", () => startMassLoop());
  $("#btnMassStop")?.addEventListener("click", () => stopMassLoop());
  $("#btnMassRefresh")?.addEventListener("click", () => runMassScan().catch((e) => alert(e.message)));

  $("#btnNvrProbe")?.addEventListener("click", async () => {
    const hint = $("#nvrProbeHint");
    if (hint) hint.textContent = "Probando…";
    try {
      const body = {
        vendor: $("#nvrVendor")?.value || "dahua",
        host: $("#nvrHost")?.value?.trim(),
        username: $("#nvrUser")?.value || "",
        password: $("#nvrPass")?.value || "",
        port: Number($("#nvrPort")?.value) || 554,
        channel_count: Number($("#nvrChannelCount")?.value) || 8,
        subtype: Number($("#nvrSubtype")?.value) || 0,
      };
      const data = await api("/api/nvr/probe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (hint) {
        hint.textContent = `${data.device_name || data.host} · ${data.channel_count} canales RTSP generados${data.probe_note ? ` · ${data.probe_note}` : ""}`;
      }
    } catch (err) {
      if (hint) hint.textContent = err.message;
    }
  });

  $("#btnNvrSave")?.addEventListener("click", async () => {
    const hint = $("#nvrProbeHint");
    try {
      const body = {
        vendor: $("#nvrVendor")?.value || "dahua",
        host: $("#nvrHost")?.value?.trim(),
        name: $("#nvrName")?.value?.trim(),
        username: $("#nvrUser")?.value || "",
        password: $("#nvrPass")?.value || "",
        port: Number($("#nvrPort")?.value) || 554,
        channel_count: Number($("#nvrChannelCount")?.value) || 8,
        subtype: Number($("#nvrSubtype")?.value) || 0,
      };
      await api("/api/nvr/devices", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      await refreshNvrDevices();
      if (hint) hint.textContent = "NVR guardado";
    } catch (err) {
      if (hint) hint.textContent = err.message;
    }
  });

  $("#btnNvrImportWatch")?.addEventListener("click", async () => {
    const hint = $("#nvrProbeHint");
    try {
      let deviceId = nvrDevicesCache[0]?.id;
      if (!deviceId) {
        const saved = await api("/api/nvr/devices", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            vendor: $("#nvrVendor")?.value || "dahua",
            host: $("#nvrHost")?.value?.trim(),
            name: $("#nvrName")?.value?.trim(),
            username: $("#nvrUser")?.value || "",
            password: $("#nvrPass")?.value || "",
            port: Number($("#nvrPort")?.value) || 554,
            channel_count: Number($("#nvrChannelCount")?.value) || 8,
            subtype: Number($("#nvrSubtype")?.value) || 0,
          }),
        });
        deviceId = saved.device?.id;
        await refreshNvrDevices();
      }
      if (!deviceId) throw new Error("Guardá el NVR primero");
      const res = await api(`/api/nvr/devices/${deviceId}/import-watchlist?replace=false`, { method: "POST" });
      await refreshWatchlistUi();
      if (hint) hint.textContent = `Importados ${res.imported} canales a Masivo`;
      if (appMode === "mass") renderMassGridPlaceholder();
    } catch (err) {
      if (hint) hint.textContent = err.message;
    }
  });

  $("#btnDevicesSaveCam")?.addEventListener("click", async () => {
    const url = $("#devicesRtspUrl")?.value?.trim();
    const name = $("#devicesCameraName")?.value?.trim() || "Canal";
    if (!url) return alert("URL RTSP requerida");
    await api("/api/cameras", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, url }),
    });
    await refreshCameras();
    alert("Canal guardado para Vivo (máx. 4)");
  });

  bindAuthController(() => {
    setAppMode("live");
    setKioskMode(true);
  });

  boot();
