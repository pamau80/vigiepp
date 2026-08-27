/** Silueta vertical / óvalo facial, alineación y zoom de guía. */
export function createSilhouetteGuideController({
  els,
  settings,
  saveSettings,
  enrollState,
  getAppMode,
}) {
  function syncSilZoomUI() {
    const face = els.silhouetteGuide?.dataset.guide === "face";
    const val = face ? settings.faceScale || 100 : settings.bodyScale || 100;
    if (els.silZoomRange) {
      els.silZoomRange.min = face ? "55" : "55";
      els.silZoomRange.max = face ? "140" : "130";
      els.silZoomRange.value = String(val);
    }
    if (els.silZoomLabel) els.silZoomLabel.textContent = `${val}%`;
    if (els.cfgBodyScale && !face) els.cfgBodyScale.value = String(settings.bodyScale);
    if (els.cfgFaceScale && face) els.cfgFaceScale.value = String(settings.faceScale);
    if (els.cfgBodyScaleVal) els.cfgBodyScaleVal.textContent = `${settings.bodyScale}%`;
    if (els.cfgFaceScaleVal) els.cfgFaceScaleVal.textContent = `${settings.faceScale}%`;
  }

  function applyGuideMode() {
    const guide = els.silhouetteGuide;
    if (!guide) return;
    const wantFace = enrollState.enrolling || getAppMode() === "identity";
    const scanning = document.body.classList.contains("is-scanning") && getAppMode() === "live";
    const enabled = !scanning && (!!settings.silhouetteEnabled || wantFace);
    guide.classList.toggle("is-off", !enabled);
    if (els.alignBadge) els.alignBadge.classList.toggle("is-off", !enabled || enrollState.enrolling || scanning);
    guide.dataset.guide = wantFace ? "face" : "body";
    guide.classList.toggle("enroll-soft", !!enrollState.enrolling || wantFace);
    guide.style.setProperty("--body-scale", String((settings.bodyScale || 100) / 100));
    guide.style.setProperty("--face-scale", String((settings.faceScale || 100) / 100));
    guide.style.setProperty("--guide-y", `${settings.guideOffsetY || 0}%`);
    if (els.silZoom) els.silZoom.classList.toggle("hidden", scanning || !enabled);
    syncSilZoomUI();
    if (els.silHint) {
      els.silHint.textContent = wantFace
        ? "Encajá tu rostro en el óvalo"
        : "Encajá el cuerpo en la silueta vertical";
    }
  }

  function setSilhouetteZoom(next) {
    const face = els.silhouetteGuide?.dataset.guide === "face";
    if (face) {
      settings.faceScale = Math.max(55, Math.min(140, Math.round(next / 5) * 5));
    } else {
      settings.bodyScale = Math.max(55, Math.min(130, Math.round(next / 5) * 5));
    }
    saveSettings(true);
    applyGuideMode();
  }

  function guideRect(frameW, frameH) {
    const face = els.silhouetteGuide?.dataset.guide === "face";
    const scale = ((face ? settings.faceScale : settings.bodyScale) || 100) / 100;
    const yOff = ((settings.guideOffsetY || 0) / 100) * frameH;
    const cx = frameW * 0.5;
    const cy = (face ? frameH * 0.36 : frameH * 0.5) + yOff;
    const halfW = frameW * (face ? 0.26 : 0.3) * scale;
    const halfH = frameH * (face ? 0.26 : 0.455) * scale;
    return {
      x1: Math.max(0, cx - halfW),
      y1: Math.max(0, cy - halfH),
      x2: Math.min(frameW, cx + halfW),
      y2: Math.min(frameH, cy + halfH),
    };
  }

  function overlapRatio(box, guide) {
    const [x1, y1, x2, y2] = box;
    const ix1 = Math.max(x1, guide.x1);
    const iy1 = Math.max(y1, guide.y1);
    const ix2 = Math.min(x2, guide.x2);
    const iy2 = Math.min(y2, guide.y2);
    const inter = Math.max(0, ix2 - ix1) * Math.max(0, iy2 - iy1);
    const area = Math.max(1, (x2 - x1) * (y2 - y1));
    return inter / area;
  }

  function faceGuideActive() {
    return enrollState.enrolling || enrollState.identifyingNow || getAppMode() === "identity";
  }

  function setAlignment(state, text) {
    if (!settings.silhouetteEnabled && !faceGuideActive() && !(settings.faceGuide && getAppMode() === "live")) {
      if (els.alignBadge) {
        els.alignBadge.dataset.state = "idle";
        els.alignBadge.textContent = "Guía off";
      }
      return;
    }
    if (enrollState.enrolling) return;
    if (els.alignBadge) {
      els.alignBadge.dataset.state = state;
      els.alignBadge.textContent = text;
    }
    if (els.silhouetteGuide) {
      els.silhouetteGuide.classList.toggle("aligned", state === "ok");
      els.silhouetteGuide.classList.toggle("bad", state === "bad");
    }
    if (els.silHint) {
      const face = els.silhouetteGuide?.dataset.guide === "face";
      els.silHint.textContent =
        state === "ok"
          ? face
            ? "Rostro encajado · listo"
            : "Perfecto — cuerpo encajado · escaneando EPP"
          : state === "bad"
            ? face
              ? "Centrá la cara en el óvalo"
              : "Acercate / centrate en la silueta vertical"
            : face
              ? "Encajá tu rostro en el óvalo"
              : "Encajá tu cuerpo en la silueta (lectura vertical)";
    }
  }

  function evaluateAlignment(detections, frameW, frameH) {
    const guideActive =
      settings.silhouetteEnabled || faceGuideActive() || (!!settings.faceGuide && getAppMode() === "live");
    if (!guideActive) {
      setAlignment("idle", "Guía off");
      return true;
    }
    if (enrollState.enrolling) return true;
    const guide = guideRect(frameW, frameH);
    const boxes = (detections || []).map((d) => d.box);
    if (!boxes.length) {
      setAlignment(
        "idle",
        els.silhouetteGuide?.dataset.guide === "face" ? "Mirá a la cámara" : "Posicionate en la silueta"
      );
      return false;
    }
    const biggest = boxes.reduce((a, b) => {
      const aa = (a[2] - a[0]) * (a[3] - a[1]);
      const bb = (b[2] - b[0]) * (b[3] - b[1]);
      return bb > aa ? b : a;
    });
    const ratio = overlapRatio(biggest, guide);
    const faceMode = els.silhouetteGuide?.dataset.guide === "face";
    const boxH = (biggest[3] - biggest[1]) / frameH;
    const tallEnough = faceMode ? boxH >= 0.12 : boxH >= 0.48;
    const needRatio = faceMode ? 0.4 : 0.55;
    if (ratio >= needRatio && tallEnough) {
      setAlignment("ok", "Encaje correcto");
      return true;
    }
    if (ratio >= (faceMode ? 0.18 : 0.25)) {
      setAlignment("bad", "Ajusta la posición");
      return false;
    }
    setAlignment("bad", faceMode ? "Centrá el rostro" : "Entra en la silueta");
    return false;
  }

  function bindGuideEvents() {
    if (els.silZoomRange) {
      els.silZoomRange.addEventListener("input", () => setSilhouetteZoom(Number(els.silZoomRange.value)));
    }
    if (els.btnSilZoomIn) {
      els.btnSilZoomIn.addEventListener("click", () => {
        const face = els.silhouetteGuide?.dataset.guide === "face";
        const cur = face ? settings.faceScale : settings.bodyScale;
        setSilhouetteZoom(cur + 5);
      });
    }
    if (els.btnSilZoomOut) {
      els.btnSilZoomOut.addEventListener("click", () => {
        const face = els.silhouetteGuide?.dataset.guide === "face";
        const cur = face ? settings.faceScale : settings.bodyScale;
        setSilhouetteZoom(cur - 5);
      });
    }
  }

  return {
    applyGuideMode,
    syncSilZoomUI,
    setSilhouetteZoom,
    setAlignment,
    evaluateAlignment,
    bindGuideEvents,
  };
}
