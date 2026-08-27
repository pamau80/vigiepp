import { $, $$, escapeHtml } from "./modules/dom.js";
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
import { videoCoverSize } from "./modules/geometry.js";
import { createZonesController } from "./modules/zones.js";
import { createReportsController } from "./modules/reports.js";
import { createDetectLiveController } from "./modules/detect-live.js";

import { createWorkersController } from "./modules/identity-workers.js";
import { createEnrollController } from "./modules/identity-enroll.js";
import { createKioskController } from "./modules/kiosk.js";
import { createTeachController } from "./modules/teach.js";
import { createMassController } from "./modules/mass.js";
import { createCameraController } from "./modules/camera.js";

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

  const APP_BUILD = globalThis.VIGIEPP_BUILD || "v45";

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
  let appMode = "live";
  const enrollState = { enrolling: false, identifyingNow: false, enrollAbort: false };
  let lastIdentifyAt = 0;
  let lastFrameSize = { w: 640, h: 480 };
  let lastIdentity = null;
  let lastFaceBox = null;
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
    const wantFace = enrollState.enrolling || appMode === "identity";
    const scanning = document.body.classList.contains("is-scanning") && appMode === "live";
    const enabled = !scanning && (!!settings.silhouetteEnabled || wantFace);
    guide.classList.toggle("is-off", !enabled);
    if (els.alignBadge) els.alignBadge.classList.toggle("is-off", !enabled || enrollState.enrolling || scanning);
    guide.dataset.guide = wantFace ? "face" : "body";
    guide.classList.toggle("enroll-soft", !!enrollState.enrolling || wantFace);
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
    return enrollState.enrolling || enrollState.identifyingNow || appMode === "identity";
  }

  function setAlignment(state, text) {
    if (!settings.silhouetteEnabled && !faceGuideActive() && !(settings.faceGuide && appMode === "live")) {
      if (els.alignBadge) {
        els.alignBadge.dataset.state = "idle";
        els.alignBadge.textContent = "Guía off";
      }
      return;
    }
    if (enrollState.enrolling) return; // overlay de poses maneja el coaching
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
    if (enrollState.enrolling) return true;
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


  function drawDetections(detections, frameW, frameH, identity, zoneHits) {
    camera.syncCanvasSize();
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
    if (faceBox && (enrollState.enrolling || appMode === "identity")) {
      drawFaceBox(ctx, faceBox, frameW, frameH, cover);
    }
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
    workers.showPersistBanner(health);
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

    await workers.refreshWorkers();
    await teach.refreshTeach();
    await workers.refreshScans();
    await camera.refreshCameras();
    await loadZones();
    loadSettings();
    await loadPrivacyServer();
    settings.fullscreenDefault = false;
    if (els.chkFullscreen) els.chkFullscreen.checked = false;
    syncSettingsForm();
    applyMobileChrome();
    applyGuideMode();
    setAppMode("live");
    if (settings.kioskMode) kiosk.setKioskMode(true);
    camera.hideLiveVideo();
    await camera.refreshCameraPermissionHint();
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.getRegistrations().then((regs) => {
        regs.forEach((r) => r.unregister().catch(() => {}));
      });
      setTimeout(() => {
        navigator.serviceWorker.register("/assets/sw.js?v=45").catch(() => {});
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
        camera.syncCanvasSize();
        applyGuideMode();
      }, 250);
    });
    window.visualViewport?.addEventListener("resize", () => {
      syncViewportHeight();
      camera.syncCanvasSize();
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

  function setAppMode(mode) {
    const prevMode = appMode;
    if (mode === "monitor") mode = "live";
    appMode = mode;

    if (mode !== "mass") mass.stopMassLoop();
    if (mode !== "live" && mode !== "identity" && mode !== "teach") {
      stopDetectLoop();
      if (mode !== "live") camera.stopRtsp();
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
        camera.getSourceMode() === "identity" || camera.getSourceMode() === "teach" || camera.getSourceMode() === "config" || camera.getSourceMode() === "reports"
          ? "camera"
          : camera.getSourceMode()
      );
      if (prevMode === "identity" && workers.hasReadyWorkers()) {
        enableIdentifyForPorteria("Identificación ON · volviste de Personas");
      }
    } else if (mode === "identity") setSource("identity");
    else if (mode === "teach") setSource("teach");
    else if (mode === "reports") setSource("reports");
    else if (mode === "config") setSource("config");
    else if (mode === "mass") setSource("mass");
    else if (mode === "devices") setSource("devices");

    applyGuideMode();
    if (mode === "identity") workers.refreshWorkers();
    if (mode === "teach") teach.refreshTeach();
    if (mode === "config") {
      loadZones();
      setConfigSection(localStorage.getItem("vigiepp-cfg-sec") || "guides");
    } else {
      stopZonesCanvasLoop();
    }
    if (mode === "mass") {
      mass.fillMassProfiles();
      mass.refreshWatchlistUi();
      mass.renderMassGridPlaceholder();
    }
    if (mode === "devices") {
      mass.refreshNvrDevices();
      mass.refreshWatchlistUi();
    }
    if (mode === "reports") {
      fillRepProfiles();
      openReport(reports.getCurrentRep() || "overview");
    }
    requestAnimationFrame(() => camera.syncCanvasSize());
  }

  function setSource(mode) {
    camera.setSourceMode(mode);
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
      camera.stopRtsp();
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
      if (!camera.hasMediaStream()) camera.startCamera({ silentDetect: true });
      else camera.showLive();
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
      camera.showLive();
    } else if (mode === "reports") {
      stopDetectLoop();
    } else if (mode === "camera") {
      camera.stopRtsp();
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
      if (appMode === "live" && camera.hasMediaStream() && !detectLive.isDetectLoopOn()) {
        startDetectLoop();
      }
    } else if (mode === "rtsp") {
      camera.stopCamera();
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
    if (payload.image_b64 && !camera.hasMediaStream()) {
      els.overlayHint.hidden = true;
      els.liveVideo.hidden = true;
      els.overlayCanvas.hidden = true;
      els.annotatedImg.hidden = false;
      els.annotatedImg.src = `data:image/jpeg;base64,${payload.image_b64}`;
    } else {
      camera.showLive();
      drawDetections(
        payload.detections,
        lastFrameSize.w,
        lastFrameSize.h,
        payload.identity || lastIdentity,
        payload.zones?.hits || []
      );
    }

    if (payload.zones?.defs) zones.zonesCache = payload.zones.defs;

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
    kiosk.updateKioskBanner(payload);

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
        enroll.flashIdentifyingGuide();
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






  // Events
  $$(".mode-btn").forEach((b) => b.addEventListener("click", () => setAppMode(b.dataset.mode)));
  document.addEventListener("click", (ev) => {
    const btn = ev.target.closest(".cfg-nav-btn");
    if (!btn) return;
    const sec = btn.getAttribute("data-cfg-sec");
    if (sec) setConfigSection(sec);
  });
  $$(".rep-item").forEach((b) => b.addEventListener("click", () => openReport(b.dataset.rep)));
  if (els.btnRepRefresh) els.btnRepRefresh.addEventListener("click", () => openReport(reports.getCurrentRep() || "overview"));
  if (els.repDays) els.repDays.addEventListener("change", () => openReport(reports.getCurrentRep() || "overview"));
  if (els.repProfile) els.repProfile.addEventListener("change", () => openReport(reports.getCurrentRep() || "overview"));
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
      await workers.refreshWorkers();
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
  window.addEventListener("resize", () => {
    if (camera.hasMediaStream()) camera.syncCanvasSize();
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
    zones.zonesCache = readZonesFromEditor();
    zones.zonesCache.push({
      id: `zona-${Date.now()}`,
      name: `Zona ${zones.zonesCache.length + 1}`,
      type: "restricted",
      enabled: true,
      x: 0.05,
      y: 0.1,
      w: 0.25,
      h: 0.35,
      color: "#e85d04",
    });
    zones.selectedZoneIndex = zones.zonesCache.length - 1;
    renderZonesEditor();
  });
  els.btnZoneSave?.addEventListener("click", async () => {
    zones.zonesCache = readZonesFromEditor();
    try {
      const res = await api("/api/zones", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ zones: zones.zonesCache }),
      });
      zones.zonesCache = res.zones || zones.zonesCache;
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
        zones.zonesCache = res.zones || [];
        renderZonesEditor();
        if (els.zonesHint) els.zonesHint.textContent = `Preset «${id}» aplicado · ${zones.zonesCache.length} zonas`;
      } catch (err) {
        if (els.zonesHint) els.zonesHint.textContent = err.message;
      }
    });
  });
  els.zonesList?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-z-del]");
    if (!btn) return;
    const i = Number(btn.getAttribute("data-z-del"));
    zones.zonesCache = readZonesFromEditor().filter((_, idx) => idx !== i);
    if (zones.selectedZoneIndex === i) zones.selectedZoneIndex = -1;
    else if (zones.selectedZoneIndex > i) zones.selectedZoneIndex -= 1;
    renderZonesEditor();
  });
  els.zonesList?.addEventListener("input", (e) => {
    if (!e.target.matches("[data-z]")) return;
    zones.zonesCache = readZonesFromEditor();
    const row = e.target.closest(".zone-row");
    if (row) {
      const i = Number(row.getAttribute("data-zi"));
      if (!Number.isNaN(i)) zones.selectedZoneIndex = i;
    }
    drawZonesEditorCanvas();
  });
  els.zonesList?.addEventListener("change", (e) => {
    if (!e.target.matches("[data-z='en'], [data-z='type'], [data-z='name']")) return;
    zones.zonesCache = readZonesFromEditor();
    drawZonesEditorCanvas();
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
      await workers.refreshWorkers();
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

  const zones = createZonesController({
    api,
    els,
    settings,
    getAppMode: () => appMode,
  });
  const {
    loadZones,
    renderZonesEditor,
    readZonesFromEditor,
    drawZonesOverlay,
    bindZonesCanvasEvents,
    startZonesCanvasLoop,
    stopZonesCanvasLoop,
    drawZonesEditorCanvas,
  } = zones;

  const reports = createReportsController({
    api,
    els,
    getProfiles: () => profiles,
  });
  const { openReport, fillRepProfiles, downloadUrl } = reports;

  const workers = createWorkersController({
    api,
    els,
    displayPersonName,
    normalizePersonNameForSave,
    setIdentityCard,
    getLastIdentity: () => lastIdentity,
    setLastIdentity: (v) => {
      lastIdentity = v;
    },
    setLastFaceBox: (v) => {
      lastFaceBox = v;
    },
  });

  const detectLive = createDetectLiveController({
    api,
    els,
    settings,
    requiredQueryValue,
    applyHealth,
    updateUi,
    applyGuideMode,
    isLiveMode,
    getSourceMode: () => camera.getSourceMode(),
    getCombinedInference: () => combinedInference,
    getEppStreak: () => eppStreak,
    setEppStreak: (v) => {
      eppStreak = v;
    },
    getLastIdentifyAt: () => lastIdentifyAt,
    setLastIdentifyAt: (v) => {
      lastIdentifyAt = v;
    },
    getLastScanRefreshAt: () => lastScanRefreshAt,
    setLastScanRefreshAt: (v) => {
      lastScanRefreshAt = v;
    },
    refreshScans: () => workers.refreshScans(),
    setIdentityCard,
    drawDetections,
    getLastFrameSize: () => lastFrameSize,
    setLastFaceBox: (v) => {
      lastFaceBox = v;
    },
    setLastIdentity: (v) => {
      lastIdentity = v;
    },
  });
  const {
    detectBlob,
    captureBlob,
    captureFaceBlob,
    identifyLiveFrame,
    startDetectLoop,
    stopDetectLoop,
  } = detectLive;

  const camera = createCameraController({
    api,
    els,
    settings,
    requiredQueryValue,
    isMobile,
    isIOS,
    applyGuideMode,
    setAlignment,
    getAppMode: () => appMode,
    isDetectLoopOn: detectLive.isDetectLoopOn,
    startDetectLoop,
    stopDetectLoop,
    updateUi,
    getLastIdentifyAt: () => lastIdentifyAt,
    setLastIdentifyAt: (v) => {
      lastIdentifyAt = v;
    },
  });

  const kiosk = createKioskController({
    settings,
    saveSettings,
    els,
    setAppMode,
    applyRoleUI,
    displayPersonName,
    getLastIdentity: () => lastIdentity,
  });

  const mass = createMassController({
    api,
    els,
    requiredQueryValue,
    getAppMode: () => appMode,
    refreshCameras: () => camera.refreshCameras(),
  });

  const teach = createTeachController({
    api,
    els,
    captureBlob,
    startCamera: camera.startCamera,
    hasMediaStream: camera.hasMediaStream,
  });

  const enroll = createEnrollController({
    api,
    els,
    enrollState,
    normalizePersonNameForSave,
    captureBlob,
    startCamera: camera.startCamera,
    stopDetectLoop,
    identifyLiveFrame,
    showLive: camera.showLive,
    applyGuideMode,
    drawDetections,
    getLastFrameSize: () => lastFrameSize,
    setLastFaceBox: (v) => {
      lastFaceBox = v;
    },
    refreshWorkers: () => workers.refreshWorkers(),
    enableIdentifyForPorteria,
    sleep,
    hasMediaStream: camera.hasMediaStream,
    setCaptureButtonsVisible,
  });

  workers.bindWorkerEvents();
  camera.bindCameraEvents();
  kiosk.bindKioskEvents();
  mass.bindMassEvents();
  teach.bindTeachEvents();
  enroll.bindEnrollEvents();

  bindAuthController(() => {
    setAppMode("live");
    kiosk.setKioskMode(true);
  });

  boot();
