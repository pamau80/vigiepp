/** Estado del backend / modelos IA en la barra superior. */
export function createAppHealthController({
  els,
  enterprise,
  workers,
  setCombinedInference,
  setLastHealth,
}) {
  function applyHealth(health) {
    if (!health) return false;
    setLastHealth(health);
    const combinedInference = !!health.combined_inference;
    setCombinedInference(combinedInference);
    const idOn = !!els.chkIdentify?.checked;
    const idReady = !!health.identity_ready;
    const eppReady = !!health.model_ready;
    const ready = idOn ? idReady && eppReady : eppReady || idReady;
    els.modelStatus.classList.toggle("ready", ready);
    els.modelStatus.classList.toggle("error", !ready && !!health.warning);
    if (idOn) {
      if (idReady && eppReady) {
        els.modelStatusText.textContent = `ID+EPP listos · ${health.workers_ready || 0} persona(s)`;
      } else if (idReady) {
        els.modelStatusText.textContent = "ID lista · EPP cargando (10–30 s)…";
      } else if (eppReady) {
        els.modelStatusText.textContent = "EPP lista · ID cargando…";
      } else {
        els.modelStatusText.textContent = health.warning || "Cargando ID+EPP…";
      }
    } else if (ready) {
      const custom = !!health.epp_custom;
      els.modelStatusText.textContent = custom
        ? `Modelo faena · ${health.workers_ready || 0} pers.`
        : `IA lista · ${health.model || "EPP"}`;
    } else {
      els.modelStatusText.textContent = health.warning || "Cargando IA…";
    }
    if (els.fpsLabel && health.build) {
      const mode = idOn && combinedInference ? "ID+EPP·1" : idOn ? "ID+EPP" : "EPP";
      els.fpsLabel.textContent = `${health.build} · ${mode}`;
    }
    enterprise.updateEnterpriseHints(health, { combinedInference, els });
    workers.showPersistBanner(health);
    return ready;
  }

  return { applyHealth };
}
