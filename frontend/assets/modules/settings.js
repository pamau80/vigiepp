/** Configuración local persistente. */
export const SETTINGS_KEY = "vigiepp.settings.v6";

export function defaultSettings() {
  return {
    silhouetteEnabled: true,
    silhouetteGate: true,
    faceGuide: true,
    bodyScale: 100,
    faceScale: 100,
    guideOffsetY: 0,
    autoAdvanceEnroll: true,
    poseAttempts: 8,
    identifyDefault: false,
    showPpeBoxes: false,
    fullscreenDefault: false,
    identifyThreshold: 0.33,
    audioAlerts: true,
    audioAlertRepeats: 0,
    anonymizeFaces: true,
    showZones: true,
    kioskMode: false,
    qrOnlyMode: false,
    retentionDays: 90,
    ppeByProfile: {},
    skinId: "faena",
    dayZeroComplete: false,
    dayZeroDismissed: false,
    dayZeroStep: 0,
    dayZeroForceOpen: false,
  };
}

let settings = defaultSettings();

export function getSettings() {
  return settings;
}

export function setSettings(patch) {
  settings = { ...settings, ...patch };
  return settings;
}

export function loadSettings() {
  try {
    let raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) {
      raw = localStorage.getItem("vigiepp.settings.v5");
    }
    if (!raw) return;
    settings = { ...defaultSettings(), ...JSON.parse(raw) };
    settings.bodyScale = Math.max(55, Math.min(130, Number(settings.bodyScale) || 100));
    settings.faceScale = Math.max(55, Math.min(140, Number(settings.faceScale) || 100));
    settings.guideOffsetY = Math.max(-20, Math.min(20, Number(settings.guideOffsetY) || 0));
    settings.audioAlertRepeats = Math.max(0, Math.min(10, Number(settings.audioAlertRepeats) || 0));
    settings.identifyThreshold = Math.max(
      0.25,
      Math.min(0.65, Number(settings.identifyThreshold) || 0.33)
    );
    if (!settings._idThreshV30) {
      settings.identifyThreshold = 0.33;
      settings._idThreshV30 = true;
      try {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
      } catch (_) {}
    }
    if (!settings.ppeByProfile || typeof settings.ppeByProfile !== "object") {
      settings.ppeByProfile = {};
    }
  } catch (_) {
    settings = defaultSettings();
  }
}

export function saveSettings(silent = false, hintEl = null) {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    if (silent || !hintEl) return;
    hintEl.textContent = "Guardado · se aplica al instante";
    setTimeout(() => {
      if (hintEl) hintEl.textContent = "Los cambios se guardan en este navegador.";
    }, 1600);
  } catch (_) {}
}
