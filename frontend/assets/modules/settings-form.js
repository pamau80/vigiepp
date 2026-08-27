import { $ } from "./dom.js";

/** Sincronización del formulario de configuración y privacidad. */
export function createSettingsFormController({
  api,
  els,
  settings,
  saveSettings,
  applyGuideMode,
  onAudioRepeatsChange,
}) {
  function syncSettingsForm() {
    if (els.cfgSilhouette) els.cfgSilhouette.checked = !!settings.silhouetteEnabled;
    if (els.cfgSilhouetteGate) els.cfgSilhouetteGate.checked = !!settings.silhouetteGate;
    if (els.cfgFaceGuide) els.cfgFaceGuide.checked = !!settings.faceGuide;
    if (els.cfgBodyScale) els.cfgBodyScale.value = String(settings.bodyScale);
    if (els.cfgFaceScale) els.cfgFaceScale.value = String(settings.faceScale);
    if (els.cfgGuideY) els.cfgGuideY.value = String(settings.guideOffsetY);
    if (els.cfgBodyScaleVal) els.cfgBodyScaleVal.textContent = `${settings.bodyScale}%`;
    if (els.cfgFaceScaleVal) els.cfgFaceScaleVal.textContent = `${settings.faceScale}%`;
    if (els.cfgGuideYVal)
      els.cfgGuideYVal.textContent = `${settings.guideOffsetY > 0 ? "+" : ""}${settings.guideOffsetY}`;
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
      syncSettingsForm();
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

  function bindSettingsEvents() {
    $("#cfgQrOnlyMode")?.addEventListener("change", () => readSettingsFromForm());
    $("#cfgRetentionDays")?.addEventListener("input", () => readSettingsFromForm());

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
        if (el === els.cfgAudioRepeats) onAudioRepeatsChange?.();
      });
      el.addEventListener("change", () => {
        readSettingsFromForm();
        if (el === els.cfgAudioRepeats) onAudioRepeatsChange?.();
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
  }

  return {
    syncSettingsForm,
    loadPrivacyServer,
    readSettingsFromForm,
    bindSettingsEvents,
  };
}
