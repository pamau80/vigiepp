/** Alertas de voz en piso (Web Speech API). */
export function createAudioAlertsController({ settings }) {
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

  return { speakAlert, resetSpeakIncident };
}
