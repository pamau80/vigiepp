import { $ } from "./dom.js";

/** Panel lateral de monitoreo: compliance, listas, identidad y audio. */
export function createLivePanelController({
  els,
  settings,
  getAppMode,
  camera,
  overlay,
  guide,
  zones,
  kiosk,
  getEnroll,
  audio,
  displayPersonName,
  setIdentityCard,
  getLastIdentity,
  setLastIdentity,
  setLastFaceBox,
  getLastFrameSize,
  setLastFrameSize,
  getLastAccessAllow,
  setLastAccessAllow,
}) {
  function updateUi(payload) {
    if (!payload || !payload.ok) return;
    const t0 = performance.now();

    if (payload.frame_width && payload.frame_height) {
      setLastFrameSize({ w: payload.frame_width, h: payload.frame_height });
    }

    if (payload.identity?.face_box) setLastFaceBox(payload.identity.face_box);

    if (payload.image_b64 && !camera.hasMediaStream()) {
      els.overlayHint.hidden = true;
      els.liveVideo.hidden = true;
      els.overlayCanvas.hidden = true;
      els.annotatedImg.hidden = false;
      els.annotatedImg.src = `data:image/jpeg;base64,${payload.image_b64}`;
    } else {
      camera.showLive();
      const frame = getLastFrameSize();
      overlay.drawDetections(
        payload.detections,
        frame.w,
        frame.h,
        payload.identity || getLastIdentity(),
        payload.zones?.hits || []
      );
    }

    if (payload.zones?.defs) zones.zonesCache = payload.zones.defs;

    const gateOn = !!settings.silhouetteGate && !!settings.silhouetteEnabled && getAppMode() === "live";
    const frame = getLastFrameSize();
    const aligned = gateOn ? guide.evaluateAlignment(payload.detections || [], frame.w, frame.h) : true;

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

    if (getAppMode() === "live" && hasPeople && !ok) {
      const zoneAlert = (payload.zones?.alerts || [])[0];
      const miss = (c.persons?.[0]?.missing || []).slice(0, 2).join(" y ");
      if (zoneAlert) {
        audio.speakAlert(
          zoneAlert.replace("Near-miss:", "Cuidado.").replace("Zona restringida:", "Zona restringida.")
        );
      } else if (miss) audio.speakAlert(`Falta ${miss}. Ponete el equipo de protección.`);
      else audio.speakAlert("No cumple. Revisá tu EPP.");
    } else if (ok || !hasPeople) {
      audio.resetSpeakIncident();
      try {
        if (window.speechSynthesis?.speaking) window.speechSynthesis.cancel();
      } catch (_) {}
    }
    if (payload.access && payload.access.allow !== getLastAccessAllow()) {
      setLastAccessAllow(payload.access.allow);
      audio.speakAlert(payload.access.allow ? "Acceso permitido" : "Acceso denegado");
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
    const id = payload.identity || getLastIdentity();
    els.alertList.innerHTML = alerts.length
      ? alerts
          .map((a) => {
            const who = id?.known && id?.name ? `${displayPersonName(id.name)}: ` : "";
            return `<li class="warn">${who}${a}</li>`;
          })
          .join("")
      : `<li class="muted">Sin alertas</li>`;

    if (payload.identity) {
      setLastIdentity(payload.identity);
      setIdentityCard(payload.identity);
      if (payload.identity.faces_detected > 0 && settings.faceGuide && getAppMode() === "live") {
        const enrollCtrl = getEnroll?.() ?? enroll;
        if (enrollCtrl) enrollCtrl.flashIdentifyingGuide();
      }
    } else if (getAppMode() === "live" && !els.chkIdentify?.checked) {
      els.identityName.textContent = "ID apagada";
      els.identityRut.textContent = "Marcá «Identificar rostro» abajo";
      if (els.identityMethod) els.identityMethod.textContent = "";
    }

    const ms = Math.round(performance.now() - t0);
    els.fpsLabel.textContent = `${ms} ms UI`;
  }

  return { updateUi };
}
