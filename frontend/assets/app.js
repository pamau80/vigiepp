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
import { createSilhouetteGuideController } from "./modules/silhouette-guide.js";
import { createOverlayCanvasController } from "./modules/overlay-canvas.js";
import { createAudioAlertsController } from "./modules/audio-alerts.js";
import { createPpeProfilesController } from "./modules/ppe-profiles.js";
import { createLivePanelController } from "./modules/live-panel.js";
import { createAppModesController } from "./modules/app-modes.js";

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

  const APP_BUILD = globalThis.VIGIEPP_BUILD || "v47";


  let eppStreak = 0;
  let lastScanRefreshAt = 0;
  const enrollState = { enrolling: false, identifyingNow: false, enrollAbort: false };
  let lastAccessAllow = null;
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
    guide.applyGuideMode();
  }




  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
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

    await ppeProfiles.loadProfiles();
    await ppeProfiles.loadCatalog();
    ppeProfiles.bindPpeChipContainer(els.requiredChips);
    ppeProfiles.bindPpeChipContainer(els.cfgPpeChips);
    ppeProfiles.renderProfile();

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
    guide.applyGuideMode();
    modes.setAppMode("live");
    if (settings.kioskMode) kiosk.setKioskMode(true);
    camera.hideLiveVideo();
    await camera.refreshCameraPermissionHint();
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.getRegistrations().then((regs) => {
        regs.forEach((r) => r.unregister().catch(() => {}));
      });
      setTimeout(() => {
        navigator.serviceWorker.register("/assets/sw.js?v=47").catch(() => {});
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
        guide.applyGuideMode();
      }, 250);
    });
    window.visualViewport?.addEventListener("resize", () => {
      syncViewportHeight();
      camera.syncCanvasSize();
    });
    window.addEventListener("resize", syncViewportHeight);
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
      if (el === els.cfgAudioRepeats) audio.resetSpeakIncident();
    });
    el.addEventListener("change", () => {
      readSettingsFromForm();
      if (el === els.cfgAudioRepeats) audio.resetSpeakIncident();
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
    getAppMode: () => modes.getAppMode(),
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

  const audio = createAudioAlertsController({ settings });

  const ppeProfiles = createPpeProfilesController({
    api,
    els,
    settings,
    saveSettings,
  });

  let modes;
  let livePanel;

  const guide = createSilhouetteGuideController({
    els,
    settings,
    saveSettings,
    enrollState,
    getAppMode: () => modes.getAppMode(),
  });

  let overlay;
  overlay = createOverlayCanvasController({
    els,
    settings,
    enrollState,
    getAppMode: () => modes.getAppMode(),
    getLastFaceBox: () => lastFaceBox,
    syncCanvasSize: () => camera.syncCanvasSize(),
    evaluateAlignment: guide.evaluateAlignment,
    drawZonesOverlay,
  });

  const reports = createReportsController({
    api,
    els,
    getProfiles: () => ppeProfiles.profiles,
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
    requiredQueryValue: ppeProfiles.requiredQueryValue,
    applyHealth,
    updateUi: (p) => livePanel.updateUi(p),
    applyGuideMode: guide.applyGuideMode,
    isLiveMode: () => modes.isLiveMode(),
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
    drawDetections: overlay.drawDetections,
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
    requiredQueryValue: ppeProfiles.requiredQueryValue,
    isMobile,
    isIOS,
    applyGuideMode: guide.applyGuideMode,
    setAlignment: guide.setAlignment,
    getAppMode: () => modes.getAppMode(),
    isDetectLoopOn: detectLive.isDetectLoopOn,
    startDetectLoop,
    stopDetectLoop,
    updateUi: (p) => livePanel.updateUi(p),
    getLastIdentifyAt: () => lastIdentifyAt,
    setLastIdentifyAt: (v) => {
      lastIdentifyAt = v;
    },
  });

  const mass = createMassController({
    api,
    els,
    requiredQueryValue: ppeProfiles.requiredQueryValue,
    getAppMode: () => modes.getAppMode(),
    refreshCameras: () => camera.refreshCameras(),
  });

  const teach = createTeachController({
    api,
    els,
    captureBlob,
    startCamera: camera.startCamera,
    hasMediaStream: camera.hasMediaStream,
  });
  modes = createAppModesController({
    els,
    settings,
    saveSettings,
    camera,
    guide,
    workers,
    teach,
    mass,
    zones,
    reports,
    stopDetectLoop,
    startDetectLoop,
    isDetectLoopOn: detectLive.isDetectLoopOn,
    loadZones,
    setConfigSectionCallbacks: {
      onSectionChange: (id) => {
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
      },
    },
  });

  const kiosk = createKioskController({
    settings,
    saveSettings,
    els,
    setAppMode: modes.setAppMode,
    applyRoleUI,
    displayPersonName,
    getLastIdentity: () => lastIdentity,
  });

  livePanel = createLivePanelController({
    els,
    settings,
    getAppMode: modes.getAppMode,
    camera,
    overlay,
    guide,
    zones,
    kiosk,
    getEnroll: () => enroll,
    audio,
    displayPersonName,
    setIdentityCard,
    getLastIdentity: () => lastIdentity,
    setLastIdentity: (v) => { lastIdentity = v; },
    setLastFaceBox: (v) => { lastFaceBox = v; },
    getLastFrameSize: () => lastFrameSize,
    setLastFrameSize: (v) => { lastFrameSize = v; },
    getLastAccessAllow: () => lastAccessAllow,
    setLastAccessAllow: (v) => { lastAccessAllow = v; },
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
    applyGuideMode: guide.applyGuideMode,
    drawDetections: overlay.drawDetections,
    getLastFrameSize: () => lastFrameSize,
    setLastFaceBox: (v) => {
      lastFaceBox = v;
    },
    refreshWorkers: () => workers.refreshWorkers(),
    enableIdentifyForPorteria: modes.enableIdentifyForPorteria,
    sleep,
    hasMediaStream: camera.hasMediaStream,
    setCaptureButtonsVisible,
  });

  workers.bindWorkerEvents();
  ppeProfiles.bindProfileEvents();
  modes.bindNavigationEvents();
  $$(".rep-item").forEach((b) => b.addEventListener("click", () => openReport(b.dataset.rep)));
  if (els.btnRepRefresh) els.btnRepRefresh.addEventListener("click", () => openReport(reports.getCurrentRep() || "overview"));
  if (els.repDays) els.repDays.addEventListener("change", () => openReport(reports.getCurrentRep() || "overview"));
  if (els.repProfile) els.repProfile.addEventListener("change", () => openReport(reports.getCurrentRep() || "overview"));
  guide.bindGuideEvents();
  camera.bindCameraEvents();
  kiosk.bindKioskEvents();
  mass.bindMassEvents();
  teach.bindTeachEvents();
  enroll.bindEnrollEvents();

  bindAuthController(() => {
    modes.setAppMode("live");
    kiosk.setKioskMode(true);
  });

  boot();
