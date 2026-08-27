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
import { createIdentityCardController } from "./modules/identity-card.js";
import { createAppHealthController } from "./modules/app-health.js";
import { createSettingsFormController } from "./modules/settings-form.js";
import { createBootController } from "./modules/app-boot.js";
import { createAuditLogController } from "./modules/audit-log.js";
import { createIdentityBackupController } from "./modules/identity-backup.js";

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

  const APP_BUILD = globalThis.VIGIEPP_BUILD || "v48";

  const identityCard = createIdentityCardController({ els });
  const { displayPersonName, normalizePersonNameForSave, setIdentityCard } = identityCard;

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






  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }



















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
    syncZonesCanvasSize,
  } = zones;

  const audio = createAudioAlertsController({ settings });

  const ppeProfiles = createPpeProfilesController({
    api,
    els,
    settings,
    saveSettings,
  });

  const auditLog = createAuditLogController({ api });

  let settingsForm;
  let appHealth;
  let bootCtrl;

  let modes;
  let livePanel;

  const guide = createSilhouetteGuideController({
    els,
    settings,
    saveSettings,
    enrollState,
    getAppMode: () => modes.getAppMode(),
  });

  settingsForm = createSettingsFormController({
    api,
    els,
    settings,
    saveSettings,
    applyGuideMode: guide.applyGuideMode,
    onAudioRepeatsChange: () => audio.resetSpeakIncident(),
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

  appHealth = createAppHealthController({
    els,
    enterprise,
    workers,
    setCombinedInference: (v) => { combinedInference = v; },
    setLastHealth: (v) => { lastHealth = v; },
  });
  const { applyHealth } = appHealth;

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
        if (id === "audit") auditLog.refreshAudit();
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

  bootCtrl = createBootController({
    api,
    els,
    settings,
    ensureAuth,
    applyHealth,
    applyMobileChrome,
    loadSettings,
    ppeProfiles,
    workers,
    teach,
    camera,
    loadZones,
    settingsForm,
    guide,
    modes,
    kiosk,
    buildVersion: "48",
  });
  const { boot } = bootCtrl;

  const identityBackup = createIdentityBackupController({ els, workers, ensureAuth });
  identityBackup.bindBackupEvents(downloadUrl);
  auditLog.bindAuditEvents();
  settingsForm.bindSettingsEvents();

  bindAuthController(() => {
    modes.setAppMode("live");
    kiosk.setKioskMode(true);
  });

  boot();
