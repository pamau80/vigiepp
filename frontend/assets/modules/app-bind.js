import { $$ } from "./dom.js";
import { createBootController } from "./app-boot.js";
import { createIdentityBackupController } from "./identity-backup.js";
import { createAppShellEventsController } from "./app-shell-events.js";
import { clearStoredAccess } from "./access-control.js";

/** Enlaza eventos de UI y arranca boot tras wiring de controladores. */
export function bindAppEvents({
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
  usersAdmin,
  bindEnterpriseEvents,
  detectBlob,
  openReport,
  downloadUrl,
  enroll,
  mass,
  buildVersion,
}) {
  workers.bindWorkerEvents();
  ppeProfiles.bindProfileEvents();
  modes.bindNavigationEvents();

  $$(".rep-item").forEach((b) => b.addEventListener("click", () => openReport(b.dataset.rep)));
  if (els.btnRepRefresh) {
    els.btnRepRefresh.addEventListener("click", () => openReport(reports.getCurrentRep() || "overview"));
  }
  if (els.repDays) {
    els.repDays.addEventListener("change", () => openReport(reports.getCurrentRep() || "overview"));
  }
  if (els.repProfile) {
    els.repProfile.addEventListener("change", () => openReport(reports.getCurrentRep() || "overview"));
  }

  guide.bindGuideEvents();
  camera.bindCameraEvents();
  kiosk.bindKioskEvents();
  mass.bindMassEvents();
  teach.bindTeachEvents();
  enroll.bindEnrollEvents();

  const bootCtrl = createBootController({
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
    buildVersion,
  });
  const { boot } = bootCtrl;

  const identityBackup = createIdentityBackupController({ els, workers, ensureAuth });
  identityBackup.bindBackupEvents(downloadUrl);
  auditLog.bindAuditEvents();
  settingsForm.bindSettingsEvents();
  usersAdmin.bindUsersAdminEvents();
  usersAdmin.loadCatalog().then(() => usersAdmin.refreshUsers());

  bindEnterpriseEvents({
    els,
    applyHealth,
    refreshWorkers: () => workers.refreshWorkers(),
    loadZones,
  });
  zones.bindZonesEditorEvents();

  const shellEvents = createAppShellEventsController({
    els,
    ensureAuth,
    detectBlob,
    camera,
  });
  shellEvents.bindShellEvents();

  boot();
}
