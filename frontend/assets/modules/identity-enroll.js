export const POSES = [
  { title: "1/4 Frente", hint: "Mirá de frente a la cámara" },
  { title: "2/4 Izquierda", hint: "Girá la cabeza un poco a tu IZQUIERDA" },
  { title: "3/4 Derecha", hint: "Girá la cabeza un poco a tu DERECHA" },
  { title: "4/4 Mentón", hint: "Levantá un poco el mentón" },
];

/** Enrolamiento por poses, fotos y identificación manual. */
export function createEnrollController({
  api,
  els,
  enrollState,
  normalizePersonNameForSave,
  captureBlob,
  startCamera,
  stopDetectLoop,
  identifyLiveFrame,
  showLive,
  applyGuideMode,
  drawDetections,
  getLastFrameSize,
  setLastFaceBox,
  refreshWorkers,
  enableIdentifyForPorteria,
  sleep,
  hasMediaStream,
}) {
  let capturePoseResolver = null;

  function setCaptureButtonsVisible(show) {
    for (const btn of [els.btnCapturePose, els.btnCapturePoseId]) {
      if (!btn) continue;
      btn.classList.toggle("hidden", !show);
      btn.disabled = !show;
    }
  }

  function waitForCaptureClick() {
    return new Promise((resolve, reject) => {
      if (capturePoseResolver) {
        capturePoseResolver.reject(new Error("Cancelado"));
        capturePoseResolver = null;
      }
      setCaptureButtonsVisible(true);
      capturePoseResolver = {
        resolve: (v) => {
          capturePoseResolver = null;
          setCaptureButtonsVisible(false);
          resolve(v);
        },
        reject: (e) => {
          capturePoseResolver = null;
          setCaptureButtonsVisible(false);
          reject(e);
        },
      };
    });
  }

  function triggerCapturePose() {
    if (capturePoseResolver) capturePoseResolver.resolve(true);
  }

  function cancelWaitingCapture() {
    if (capturePoseResolver) capturePoseResolver.reject(new Error("Cancelado"));
  }

  function setPoseUI(stepIndex, countdownText, okCount = 0) {
    const pose = POSES[stepIndex];
    const progressed = Math.max(okCount, stepIndex);
    const width = `${Math.round((progressed / POSES.length) * 100)}%`;
    const label = pose
      ? `${pose.title} · OK ${okCount}/${POSES.length}`
      : `Completado · ${okCount}/${POSES.length}`;
    if (els.poseProgress) {
      els.poseProgress.classList.remove("hidden");
      if (els.poseBarFill) els.poseBarFill.style.width = width;
      if (els.poseStepLabel) els.poseStepLabel.textContent = label;
    }
    els.enrollOverlay.classList.remove("hidden");
    if (pose) {
      els.enrollPoseTitle.textContent = pose.title;
      els.enrollPoseHint.textContent = pose.hint;
    }
    els.enrollCount.textContent = countdownText || "";
    if (els.enrollCoach && pose) els.enrollCoach.textContent = pose.hint;
  }

  function endPoseUI() {
    cancelWaitingCapture();
    setCaptureButtonsVisible(false);
    els.enrollOverlay.classList.add("hidden");
    els.enrollCount.textContent = "";
    if (els.poseBarFill) els.poseBarFill.style.width = "100%";
    if (els.poseStepLabel) els.poseStepLabel.textContent = "4/4 completo";
    enrollState.enrolling = false;
    document.body.classList.remove("is-enrolling");
    applyGuideMode();
  }

  async function enrollWorker() {
    if (enrollState.enrolling) return;
    if (!els.workerName.value.trim() && !els.workerRut.value.trim()) {
      if (els.enrollCoach) els.enrollCoach.textContent = "Escribí al menos el nombre";
      return;
    }
    if (!els.chkBiometricConsent?.checked) {
      if (els.enrollCoach) {
        els.enrollCoach.textContent = "Marcá el consentimiento biométrico antes de enrolar.";
      }
      return;
    }
    enrollState.enrolling = true;
    enrollState.enrollAbort = false;
    document.body.classList.add("is-enrolling");
    stopDetectLoop();
    applyGuideMode();
    els.btnEnroll.disabled = true;
    if (els.btnIdentify) els.btnIdentify.disabled = true;
    els.btnCancelEnroll.classList.remove("hidden");
    try {
      if (!hasMediaStream()) await startCamera({ silentDetect: true });
      else stopDetectLoop();
      showLive();
      const name = normalizePersonNameForSave(els.workerName.value.trim());
      const rut = els.workerRut.value.trim();
      let okCount = 0;

      for (let i = 0; i < POSES.length; i++) {
        if (enrollState.enrollAbort) throw new Error("Cancelado");
        let captured = false;
        while (!captured) {
          if (enrollState.enrollAbort) throw new Error("Cancelado");
          setPoseUI(i, "Pulsá «Tomar foto»", okCount);
          if (els.enrollCoach) els.enrollCoach.textContent = `${POSES[i].hint} · después pulsá Tomar foto`;
          try {
            await waitForCaptureClick();
          } catch (waitErr) {
            throw waitErr.message === "Cancelado" ? waitErr : new Error("Cancelado");
          }
          if (enrollState.enrollAbort) throw new Error("Cancelado");
          setPoseUI(i, "Capturando…", okCount);
          const blob = await captureBlob(0.92, 960);
          if (!blob) {
            els.enrollCount.textContent = "Sin cámara — reintentá";
            if (els.enrollCoach) {
              els.enrollCoach.textContent = "No hay imagen de cámara. Revisá permisos y reintentá.";
            }
            continue;
          }
          const fd = new FormData();
          fd.append("file", blob, `pose_${i}.jpg`);
          fd.append("name", name);
          fd.append("rut", rut);
          fd.append("consent", "true");
          try {
            const last = await api("/api/identity/enroll", { method: "POST", body: fd }, 20000);
            if (last.face_box) {
              setLastFaceBox(last.face_box);
              const frameSize = getLastFrameSize();
              drawDetections([], frameSize.w, frameSize.h, {
                face_box: last.face_box,
                known: true,
                name: last.worker?.name,
              });
            }
            if (last.face_enrolled) {
              okCount += 1;
              captured = true;
              setPoseUI(i, "OK · siguiente pose", okCount);
              if (last.worker?.name) els.workerName.value = last.worker.name;
              await sleep(450);
              break;
            }
            const why = last.error || last.message || "Sin rostro válido";
            els.enrollCount.textContent = "Calidad baja — reintentá";
            if (els.enrollCoach) {
              els.enrollCoach.textContent = why;
            }
          } catch (e) {
            els.enrollCount.textContent = "Rechazado — reintentá";
            if (els.enrollCoach) els.enrollCoach.textContent = e.message;
          }
        }
      }
      endPoseUI();
      await refreshWorkers();
      const done =
        okCount >= 4
          ? `Listo ${okCount}/4. Andá a Monitoreo: la identificación ya quedó activa.`
          : `Incompleto ${okCount}/4. Rehacé poses con luz frontal (calidad obligatoria).`;
      if (els.enrollCoach) els.enrollCoach.textContent = done;
      if (okCount >= 4) {
        enableIdentifyForPorteria("Identificación ON tras enrolar");
      }
    } catch (err) {
      if (els.enrollCoach) els.enrollCoach.textContent = err.message;
      endPoseUI();
    } finally {
      enrollState.enrolling = false;
      document.body.classList.remove("is-enrolling");
      setCaptureButtonsVisible(false);
      applyGuideMode();
      els.btnEnroll.disabled = false;
      if (els.btnIdentify) els.btnIdentify.disabled = false;
      els.btnCancelEnroll.classList.add("hidden");
      showLive();
    }
  }

  async function uploadFacePhotos(fileList) {
    const name = normalizePersonNameForSave(els.workerName.value.trim());
    const rut = els.workerRut.value.trim();
    if (!name && !rut) {
      if (els.enrollCoach) els.enrollCoach.textContent = "Escribí nombre o RUT antes de adjuntar fotos";
      return;
    }
    if (!els.chkBiometricConsent?.checked) {
      if (els.enrollCoach) els.enrollCoach.textContent = "Marcá el consentimiento biométrico antes de adjuntar fotos.";
      return;
    }
    const files = [...(fileList || [])].slice(0, 40);
    if (!files.length) return;
    if (els.enrollCoach) els.enrollCoach.textContent = `Cargando ${files.length} fotos de rostro…`;
    const fd = new FormData();
    fd.append("name", name);
    fd.append("rut", rut);
    fd.append("consent", "true");
    for (const f of files) fd.append("files", f, f.name);
    try {
      const data = await api("/api/identity/enroll-photos", { method: "POST", body: fd }, 120000);
      if (els.enrollCoach) els.enrollCoach.textContent = data.message;
      if (data.worker?.name) els.workerName.value = data.worker.name;
      await refreshWorkers();
    } catch (err) {
      if (els.enrollCoach) els.enrollCoach.textContent = err.message;
    }
  }

  async function identifyWorker() {
    enrollState.identifyingNow = true;
    applyGuideMode();
    stopDetectLoop();
    if (!hasMediaStream()) await startCamera({ silentDetect: true });
    showLive();
    try {
      const data = await identifyLiveFrame({ flash: true });
      if (!data) {
        els.identityMethod.textContent = els.identityMethod.textContent || "Sin resultado. Reintentá.";
      } else if (data.image_b64) {
        els.annotatedImg.hidden = false;
        els.annotatedImg.src = `data:image/jpeg;base64,${data.image_b64}`;
        await sleep(1200);
        showLive();
      }
    } catch (err) {
      els.identityMethod.textContent = err.message || "No se pudo identificar";
    } finally {
      enrollState.identifyingNow = false;
      applyGuideMode();
    }
  }

  function flashIdentifyingGuide() {
    enrollState.identifyingNow = true;
    applyGuideMode();
    clearTimeout(window.__vigieppFaceGuideTimer);
    window.__vigieppFaceGuideTimer = setTimeout(() => {
      if (!enrollState.enrolling) {
        enrollState.identifyingNow = false;
        applyGuideMode();
      }
    }, 2800);
  }

  function bindEnrollEvents() {
    els.btnEnroll.addEventListener("click", enrollWorker);
    els.btnCancelEnroll.addEventListener("click", () => {
      enrollState.enrollAbort = true;
      cancelWaitingCapture();
    });
    for (const btn of [els.btnCapturePose, els.btnCapturePoseId]) {
      if (btn) btn.addEventListener("click", triggerCapturePose);
    }
    if (els.faceTrainPhotos) {
      els.faceTrainPhotos.addEventListener("change", async (e) => {
        await uploadFacePhotos(e.target.files);
        e.target.value = "";
      });
    }
    els.btnIdentify.addEventListener("click", identifyWorker);
  }

  return {
    enrollWorker,
    identifyWorker,
    uploadFacePhotos,
    flashIdentifyingGuide,
    bindEnrollEvents,
    isEnrolling: () => enrollState.enrolling,
    isIdentifyingNow: () => enrollState.identifyingNow,
  };
}
