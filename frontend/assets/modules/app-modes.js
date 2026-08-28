import { $, $$ } from "./dom.js";

/** Navegación principal: modos de app, fuentes de video y secciones de config. */
export function createAppModesController({
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
  isDetectLoopOn,
  loadZones,
  setConfigSectionCallbacks,
}) {
  let appMode = "live";

  function getAppMode() {
    return appMode;
  }

  function isLiveMode() {
    return appMode === "live" || appMode === "monitor";
  }

  function isViewportMode() {
    return isLiveMode() || appMode === "identity" || appMode === "teach";
  }

  function enableIdentifyForPorteria(reason = "") {
    if (els.chkIdentify) els.chkIdentify.checked = true;
    settings.identifyDefault = true;
    if (els.cfgIdentifyDefault) els.cfgIdentifyDefault.checked = true;
    saveSettings(true);
    if (els.speedHint && reason) els.speedHint.textContent = reason;
  }

  function setConfigSection(sec) {
    const id = ["guides", "audio", "zones", "monitor", "privacy", "enterprise", "audit"].includes(sec)
      ? sec
      : "guides";
    try {
      localStorage.setItem("vigiepp-cfg-sec", id);
    } catch (_) {}
    $$("[data-cfg-section]").forEach((el) => {
      el.classList.toggle("hidden", el.getAttribute("data-cfg-section") !== id);
    });
    $$(".cfg-nav-btn").forEach((btn) => {
      const on = btn.getAttribute("data-cfg-sec") === id;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
    const panel = $("#sidePanel");
    if (panel && appMode === "config") panel.scrollTop = 0;
    const block = $("#configBlock");
    if (block) block.scrollTop = 0;
    setConfigSectionCallbacks?.onSectionChange?.(id);
  }

  function setSource(mode) {
    camera.setSourceMode(mode);
    $$(".tab").forEach((t) => {
      if (!t.dataset.source) return;
      const on = t.dataset.source === mode;
      t.classList.toggle("active", on);
      t.setAttribute("aria-selected", on ? "true" : "false");
    });
    const showCamBar = mode === "camera" || mode === "identity" || mode === "teach";
    els.cameraControls.classList.toggle("hidden", !showCamBar);
    els.rtspControls.classList.toggle("hidden", mode !== "rtsp");
    els.uploadControls.classList.toggle("hidden", mode !== "upload");
    els.identityControls.classList.toggle("hidden", mode !== "identity");
    if (els.teachControls) els.teachControls.classList.toggle("hidden", mode !== "teach");
    $("#massToolbar")?.classList.toggle("hidden", mode !== "mass");

    if (mode === "mass" || mode === "devices") {
      stopDetectLoop();
      camera.stopRtsp();
    }

    if (els.chkIdentify?.closest?.("label")) {
      const idLabel = els.chkIdentify.closest("label");
      idLabel.classList.toggle("hidden", mode === "identity" || mode === "teach");
    }
    if (els.chkFullscreen?.closest?.("label")) {
      const fsLabel = els.chkFullscreen.closest("label") || $("#lblFullscreen");
      if (fsLabel) fsLabel.classList.toggle("hidden", mode === "identity" || mode === "teach");
    }
    if (els.speedHint) {
      els.speedHint.classList.toggle("hidden", mode === "identity" || mode === "teach");
      if (mode === "camera") els.speedHint.textContent = "Lectura vertical · cuerpo completo";
      else if (mode === "identity") els.speedHint.textContent = "Guía facial · 4 poses";
      else if (mode === "teach") els.speedHint.textContent = "Foto o video de la prenda";
    }

    if (mode === "identity" || mode === "teach") {
      stopDetectLoop();
      if (!camera.hasMediaStream()) camera.startCamera({ silentDetect: true });
      else camera.showLive();
      if (mode === "identity") {
        if (els.complianceBox) els.complianceBox.dataset.state = "idle";
        if (els.complianceValue) els.complianceValue.textContent = "Enrolamiento";
        if (els.complianceSummary) {
          els.complianceSummary.textContent = "Registrá el rostro acá. El EPP se evalúa en Vivo.";
        }
        if (els.statusPill) els.statusPill.textContent = "Enrolamiento";
      }
      if (els.detList) els.detList.innerHTML = `<li class="muted">Sin escaneo EPP en este modo</li>`;
      if (els.alertList) els.alertList.innerHTML = `<li class="muted">Sin alertas de faena</li>`;
    } else if (mode === "config") {
      stopDetectLoop();
      camera.showLive();
    } else if (mode === "reports") {
      stopDetectLoop();
    } else if (mode === "camera") {
      camera.stopRtsp();
      if (els.complianceBox) els.complianceBox.dataset.state = "idle";
      if (els.complianceValue) els.complianceValue.textContent = "En espera";
      if (els.complianceSummary) {
        els.complianceSummary.textContent = els.chkIdentify?.checked
          ? "Iniciá el monitoreo para evaluar EPP e identidad."
          : "Marcá «Identificar rostro» abajo para reconocer personas enroladas.";
      }
      if (els.statusPill) els.statusPill.textContent = "Standby";
      if (els.detList) els.detList.innerHTML = `<li class="muted">Sin detecciones</li>`;
      if (els.alertList) els.alertList.innerHTML = `<li class="muted">Sin alertas</li>`;
      if (appMode === "live" && camera.hasMediaStream() && !isDetectLoopOn()) {
        startDetectLoop();
      }
    } else if (mode === "rtsp") {
      camera.stopCamera();
    } else {
      stopDetectLoop();
    }

    if (mode === "identity" && els.enrollCoach) {
      els.enrollCoach.textContent = "4 poses de calidad obligatorias · luz frontal · una persona";
    }
    guide.applyGuideMode();
  }

  function setAppMode(mode) {
    const prevMode = appMode;
    if (mode === "monitor") mode = "live";
    appMode = mode;

    if (mode !== "mass") mass.stopMassLoop();
    if (mode !== "live" && mode !== "identity" && mode !== "teach") {
      stopDetectLoop();
      if (mode !== "live") camera.stopRtsp();
    }

    document.body.classList.remove(
      "mode-live",
      "mode-monitor",
      "mode-mass",
      "mode-devices",
      "mode-identity",
      "mode-teach",
      "mode-config",
      "mode-reports"
    );
    document.body.classList.add(`mode-${mode}`);

    $$(".mode-btn").forEach((b) => {
      const on = b.dataset.mode === mode;
      b.classList.toggle("active", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });

    els.monitorToolbar?.classList.toggle("hidden", mode !== "live");
    $("#massToolbar")?.classList.toggle("hidden", mode !== "mass");

    $("#liveWorkspace")?.classList.toggle("hidden", !isViewportMode());
    $("#massWorkspace")?.classList.toggle("hidden", mode !== "mass");
    $("#devicesWorkspace")?.classList.toggle("hidden", mode !== "devices");

    const stage = $(".stage");
    if (stage) stage.classList.toggle("is-reports", mode === "reports");
    if (els.reportsDesk) els.reportsDesk.classList.toggle("hidden", mode !== "reports");

    const panel = $("#sidePanel");
    if (panel) panel.dataset.mode = mode;
    const ctx = $("#panelContext");
    if (ctx) {
      const labels = {
        live: "Monitoreo en vivo",
        mass: "Barrido multi-cámara",
        devices: "NVR y cámaras",
        identity: "Enrolamiento",
        teach: "Entrenar EPP de la faena",
        reports: "Informes",
        config: "Ajustes",
      };
      ctx.textContent = labels[mode] || labels.config;
    }

    $$(".panel-section").forEach((el) => {
      const show = el.getAttribute("data-show");
      if (!show) return;
      el.classList.toggle("hidden", show !== mode);
    });

    $$("[data-live-only]").forEach((el) => {
      el.classList.toggle("hidden", !isLiveMode());
    });

    if (mode === "live") {
      const src = camera.getSourceMode();
      setSource(
        src === "identity" || src === "teach" || src === "config" || src === "reports" ? "camera" : src
      );
      if (prevMode === "identity" && workers.hasReadyWorkers()) {
        enableIdentifyForPorteria("Identificación ON · volviste de Personas");
      }
    } else if (mode === "identity") setSource("identity");
    else if (mode === "teach") setSource("teach");
    else if (mode === "reports") setSource("reports");
    else if (mode === "config") setSource("config");
    else if (mode === "mass") setSource("mass");
    else if (mode === "devices") setSource("devices");

    guide.applyGuideMode();
    if (mode === "identity") workers.refreshWorkers();
    if (mode === "teach") teach.refreshTeach();
    if (mode === "config") {
      loadZones();
      setConfigSection(localStorage.getItem("vigiepp-cfg-sec") || "guides");
    } else {
      zones.stopZonesCanvasLoop();
    }
    if (mode === "mass") {
      mass.fillMassProfiles();
      mass.refreshWatchlistUi();
      mass.renderMassGridPlaceholder();
    }
    if (mode === "devices") {
      mass.refreshNvrDevices();
      mass.refreshWatchlistUi();
    }
    if (mode === "reports") {
      reports.fillRepProfiles();
      reports.openReport(reports.getCurrentRep() || "overview");
    }
    requestAnimationFrame(() => camera.syncCanvasSize());
  }

  function bindNavigationEvents() {
    $$(".mode-btn").forEach((b) => b.addEventListener("click", () => setAppMode(b.dataset.mode)));
    document.addEventListener("click", (ev) => {
      const btn = ev.target.closest(".cfg-nav-btn");
      if (!btn) return;
      const sec = btn.getAttribute("data-cfg-sec");
      if (sec) setConfigSection(sec);
    });
    $$(".tab").forEach((t) => {
      if (t.dataset.source) t.addEventListener("click", () => setSource(t.dataset.source));
    });
  }

  return {
    getAppMode,
    isLiveMode,
    isViewportMode,
    setAppMode,
    setSource,
    setConfigSection,
    enableIdentifyForPorteria,
    bindNavigationEvents,
  };
}
