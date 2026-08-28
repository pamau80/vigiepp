import { $ } from "./dom.js";
import { syncViewportHeight } from "./mobile.js";

/** Arranque de la aplicación tras login. */
export function createBootController({
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
  dayZero,
  applySkin,
  buildVersion,
}) {
  async function boot() {
    await ensureAuth();
    try {
      const health = await api("/api/health");
      applyHealth(health);
    } catch {
      if (els.modelStatus) els.modelStatus.classList.add("error");
      if (els.modelStatusText) els.modelStatusText.textContent = "Backend no disponible";
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
    applySkin?.(settings.skinId || "faena");
    await settingsForm.loadPrivacyServer();
    settings.fullscreenDefault = false;
    if (els.chkFullscreen) els.chkFullscreen.checked = false;
    settingsForm.syncSettingsForm();
    applyMobileChrome();
    guide.applyGuideMode();
    modes.setAppMode("live");
    if (settings.kioskMode) kiosk.setKioskMode(true);
    camera.hideLiveVideo();
    await camera.refreshCameraPermissionHint();
    await dayZero?.afterBoot?.();

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.getRegistrations().then((regs) => {
        regs.forEach((r) => r.unregister().catch(() => {}));
      });
      setTimeout(() => {
        navigator.serviceWorker.register(`/assets/sw.js?v=${buildVersion}`).catch(() => {});
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

  return { boot };
}
