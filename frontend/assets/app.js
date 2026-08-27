import { createApi } from "./modules/http.js";
import { createAuthController } from "./modules/auth.js";
import { createEnterpriseController } from "./modules/enterprise.js";
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
import { createAuditLogController } from "./modules/audit-log.js";
import {
  createAppElements,
  createAppRuntimeState,
  createSettingsStore,
  sleep,
} from "./modules/app-state.js";
import { bindAppEvents } from "./modules/app-bind.js";
import { isMobile, isIOS } from "./modules/mobile.js";

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
const { refreshSitesUi, refreshEhsUi, bindEnterpriseEvents } = enterprise;

function bindAuthController(onOperatorLogin) {
  const ctrl = createAuthController({ onOperatorLogin });
  ensureAuth = ctrl.ensureAuth;
  applyRoleUI = (role) => {
    userRole = role || "admin";
    ctrl.applyRoleUI(role);
  };
}

const APP_BUILD = globalThis.VIGIEPP_BUILD || "v51";
const els = createAppElements();
const state = createAppRuntimeState();
const { settings, loadSettings, saveSettings, applyMobileChrome } = createSettingsStore(els);

const identityCard = createIdentityCardController({ els });
const { displayPersonName, normalizePersonNameForSave, setIdentityCard } = identityCard;

let modes;
let livePanel;

const zones = createZonesController({
  api,
  els,
  settings,
  getAppMode: () => modes.getAppMode(),
});
const {
  loadZones,
  drawZonesOverlay,
  bindZonesCanvasEvents,
  startZonesCanvasLoop,
  stopZonesCanvasLoop,
  drawZonesEditorCanvas,
  syncZonesCanvasSize,
} = zones;

const audio = createAudioAlertsController({ settings });
const ppeProfiles = createPpeProfilesController({ api, els, settings, saveSettings });
const auditLog = createAuditLogController({ api });

const guide = createSilhouetteGuideController({
  els,
  settings,
  saveSettings,
  enrollState: state.enrollState,
  getAppMode: () => modes.getAppMode(),
});

const settingsForm = createSettingsFormController({
  api,
  els,
  settings,
  saveSettings,
  applyGuideMode: guide.applyGuideMode,
  onAudioRepeatsChange: () => audio.resetSpeakIncident(),
});

let overlay;
const reports = createReportsController({
  api,
  els,
  getProfiles: () => ppeProfiles.profiles,
});
const { openReport, downloadUrl } = reports;

const workers = createWorkersController({
  api,
  els,
  displayPersonName,
  normalizePersonNameForSave,
  setIdentityCard,
  getLastIdentity: state.getLastIdentity,
  setLastIdentity: state.setLastIdentity,
  setLastFaceBox: state.setLastFaceBox,
});

const appHealth = createAppHealthController({
  els,
  enterprise,
  workers,
  setCombinedInference: state.setCombinedInference,
  setLastHealth: state.setLastHealth,
});
const { applyHealth } = appHealth;

overlay = createOverlayCanvasController({
  els,
  settings,
  enrollState: state.enrollState,
  getAppMode: () => modes.getAppMode(),
  getLastFaceBox: state.getLastFaceBox,
  syncCanvasSize: () => camera.syncCanvasSize(),
  evaluateAlignment: guide.evaluateAlignment,
  drawZonesOverlay,
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
  getCombinedInference: state.getCombinedInference,
  getEppStreak: state.getEppStreak,
  setEppStreak: state.setEppStreak,
  getLastIdentifyAt: state.getLastIdentifyAt,
  setLastIdentifyAt: state.setLastIdentifyAt,
  getLastScanRefreshAt: state.getLastScanRefreshAt,
  setLastScanRefreshAt: state.setLastScanRefreshAt,
  refreshScans: () => workers.refreshScans(),
  setIdentityCard,
  drawDetections: overlay.drawDetections,
  getLastFrameSize: state.getLastFrameSize,
  setLastFaceBox: state.setLastFaceBox,
  setLastIdentity: state.setLastIdentity,
});
const { detectBlob, captureBlob, identifyLiveFrame, startDetectLoop, stopDetectLoop } = detectLive;

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
  getLastIdentifyAt: state.getLastIdentifyAt,
  setLastIdentifyAt: state.setLastIdentifyAt,
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
  getLastIdentity: state.getLastIdentity,
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
  getLastIdentity: state.getLastIdentity,
  setLastIdentity: state.setLastIdentity,
  setLastFaceBox: state.setLastFaceBox,
  getLastFrameSize: state.getLastFrameSize,
  setLastFrameSize: state.setLastFrameSize,
  getLastAccessAllow: state.getLastAccessAllow,
  setLastAccessAllow: state.setLastAccessAllow,
});

const enroll = createEnrollController({
  api,
  els,
  enrollState: state.enrollState,
  normalizePersonNameForSave,
  captureBlob,
  startCamera: camera.startCamera,
  stopDetectLoop,
  identifyLiveFrame,
  showLive: camera.showLive,
  applyGuideMode: guide.applyGuideMode,
  drawDetections: overlay.drawDetections,
  getLastFrameSize: state.getLastFrameSize,
  setLastFaceBox: state.setLastFaceBox,
  refreshWorkers: () => workers.refreshWorkers(),
  enableIdentifyForPorteria: modes.enableIdentifyForPorteria,
  sleep,
  hasMediaStream: camera.hasMediaStream,
});

bindAppEvents({
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
  zones,
  reports,
  auditLog,
  bindEnterpriseEvents,
  detectBlob,
  openReport,
  downloadUrl,
  enroll,
  mass,
  buildVersion: APP_BUILD.replace(/^v/, ""),
  bindAuthController,
});
