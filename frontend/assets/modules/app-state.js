import { $ } from "./dom.js";
import {
  getSettings,
  loadSettings as loadSettingsFromModule,
  saveSettings as saveSettingsToModule,
} from "./settings.js";
import { applyMobileChrome as applyMobileChromeModule } from "./mobile.js";

/** Referencias DOM de la aplicación. */
export function createAppElements() {
  return {
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
    usersList: $("#usersList"),
    userNewName: $("#userNewName"),
    userNewPin: $("#userNewPin"),
    userNewRole: $("#userNewRole"),
    userNewExtra: $("#userNewExtra"),
    btnUserCreate: $("#btnUserCreate"),
    userEditPanel: $("#userEditPanel"),
    userEditName: $("#userEditName"),
    userEditPin: $("#userEditPin"),
    userEditRole: $("#userEditRole"),
    userEditSites: $("#userEditSites"),
    userEditExtra: $("#userEditExtra"),
    userEditRevoked: $("#userEditRevoked"),
    btnUserSave: $("#btnUserSave"),
    btnUserCancel: $("#btnUserCancel"),
    usersHint: $("#usersHint"),
  };
}

/** Estado mutable compartido entre controladores en vivo. */
export function createAppRuntimeState() {
  const enrollState = { enrolling: false, identifyingNow: false, enrollAbort: false };
  let eppStreak = 0;
  let lastScanRefreshAt = 0;
  let lastAccessAllow = null;
  let lastIdentifyAt = 0;
  let lastFrameSize = { w: 640, h: 480 };
  let lastIdentity = null;
  let lastFaceBox = null;
  let combinedInference = false;
  let lastHealth = null;

  return {
    enrollState,
    getEppStreak: () => eppStreak,
    setEppStreak: (v) => {
      eppStreak = v;
    },
    getLastScanRefreshAt: () => lastScanRefreshAt,
    setLastScanRefreshAt: (v) => {
      lastScanRefreshAt = v;
    },
    getLastAccessAllow: () => lastAccessAllow,
    setLastAccessAllow: (v) => {
      lastAccessAllow = v;
    },
    getLastIdentifyAt: () => lastIdentifyAt,
    setLastIdentifyAt: (v) => {
      lastIdentifyAt = v;
    },
    getLastFrameSize: () => lastFrameSize,
    setLastFrameSize: (v) => {
      lastFrameSize = v;
    },
    getLastIdentity: () => lastIdentity,
    setLastIdentity: (v) => {
      lastIdentity = v;
    },
    getLastFaceBox: () => lastFaceBox,
    setLastFaceBox: (v) => {
      lastFaceBox = v;
    },
    getCombinedInference: () => combinedInference,
    setCombinedInference: (v) => {
      combinedInference = v;
    },
    getLastHealth: () => lastHealth,
    setLastHealth: (v) => {
      lastHealth = v;
    },
  };
}

/** Settings locales + persistencia + chrome móvil. */
export function createSettingsStore(els) {
  let settings = getSettings();

  function loadSettings() {
    loadSettingsFromModule();
    settings = getSettings();
  }

  function saveSettings(silent = false) {
    saveSettingsToModule(silent, els.cfgSavedHint);
  }

  function applyMobileChrome() {
    applyMobileChromeModule(settings, els);
  }

  return { settings, loadSettings, saveSettings, applyMobileChrome };
}

export function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}
