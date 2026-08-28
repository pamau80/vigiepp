import { $ } from "./dom.js";
import { CORE_PPE, ppeProgress, faenaReady } from "../lib/teach-progress.js";

const STEPS = ["intro", "profile", "ppe-casco", "ppe-chaleco", "ppe-lentes", "ppe-guantes", "train", "done"];

export function createDayZeroWizardController({
  api,
  els,
  settings,
  saveSettings,
  getRole,
  setAppMode,
  teach,
  ppeProfiles,
  applyHealth,
}) {
  let stepIdx = 0;
  let lastGuide = null;

  function isAdmin() {
    return getRole?.() !== "operator";
  }

  function shouldShowWizard() {
    if (!isAdmin()) return false;
    if (settings.dayZeroComplete) return false;
    return !settings.dayZeroDismissed || settings.dayZeroForceOpen;
  }

  function shouldShowBanner() {
    if (!isAdmin()) return false;
    if (settings.dayZeroComplete) return false;
    return settings.dayZeroDismissed;
  }

  function currentPpeStep() {
    const id = STEPS[stepIdx];
    if (!id?.startsWith("ppe-")) return null;
    return CORE_PPE.find((p) => id === `ppe-${p.id}`) || null;
  }

  function progressSummary(guide, eppCustom) {
    const classes = guide?.classes || [];
    const prog = ppeProgress(classes, guide);
    const doneCount = prog.filter((p) => p.done).length;
    return { prog, doneCount, total: CORE_PPE.length, ready: faenaReady(prog, guide, eppCustom) };
  }

  function renderBody(guide, eppCustom) {
    const body = els.dayZeroBody;
    if (!body) return;
    const step = STEPS[stepIdx];
    const { prog, doneCount } = progressSummary(guide, eppCustom);

    if (step === "intro") {
      body.innerHTML = `
        <p class="day-zero-lead">Configurá el EPP real de tu faena antes de usar portería en producción.</p>
        <ul class="day-zero-bullets">
          <li>Perfil <strong>EPP completo</strong> (casco, ropa, lentes, guantes)</li>
          <li>Fotos de <em>tu</em> equipo — color y tipo</li>
          <li>Entrenar y activar modelo en el servidor edge</li>
        </ul>
        <p class="card-meta">Duración orientativa: 20–40 min · podés pausar y continuar después.</p>`;
      return;
    }

    if (step === "profile") {
      if (els.profileSelect) els.profileSelect.value = "epp_completo";
      ppeProfiles?.renderProfile?.();
      body.innerHTML = `
        <p class="day-zero-lead">Perfil <strong>EPP completo faena</strong> activado.</p>
        <p class="card-meta">Obligatorio en portería: casco, ropa de alta visibilidad, lentes y guantes.</p>
        <p class="card-meta">Podés cambiarlo luego en <strong>Perfil faena</strong> (barra superior).</p>`;
      return;
    }

    const ppe = currentPpeStep();
    if (ppe) {
      const item = prog.find((x) => x.id === ppe.id) || { count: 0, min: ppe.min, pct: 0, done: false };
      const idx = CORE_PPE.findIndex((x) => x.id === ppe.id) + 1;
      body.innerHTML = `
        <p class="day-zero-kicker">Ítem ${idx} de ${CORE_PPE.length}</p>
        <p class="day-zero-lead">Entrená <strong>${ppe.label}</strong> de tu faena</p>
        <div class="day-zero-meter"><span style="width:${item.pct}%"></span></div>
        <p class="day-zero-count">${item.count} / ${item.min} fotos ${item.done ? "✓" : ""}</p>
        <p class="card-meta">Variá ángulos, luz y personas. Podés adjuntar fotos o un video corto.</p>
        <button type="button" class="btn primary" id="btnDayZeroOpenTeach">Abrir entrenamiento EPP</button>`;
      $("#btnDayZeroOpenTeach")?.addEventListener("click", () => {
        setAppMode("teach");
        if (els.teachClass) els.teachClass.value = ppe.teachClass || ppe.id;
        teach.refreshTeach();
        closeModal(false);
      });
      return;
    }

    if (step === "train") {
      const stats = guide?.stats || {};
      const canTrain = !!stats.ready_to_train;
      const canActivate = !!stats.training?.custom_model_ready || !!eppCustom;
      body.innerHTML = `
        <p class="day-zero-lead">Progreso EPP: <strong>${doneCount}/${CORE_PPE.length}</strong> ítems listos</p>
        <ul class="day-zero-checklist">${prog
          .map((p) => `<li class="${p.done ? "done" : ""}">${p.label} · ${p.count}/${p.min}</li>`)
          .join("")}</ul>
        <div class="day-zero-actions">
          <button type="button" class="btn secondary" id="btnDayZeroTrain" ${canTrain ? "" : "disabled"}>Entrenar modelo</button>
          <button type="button" class="btn primary" id="btnDayZeroActivate" ${canActivate ? "" : "disabled"}>Activar en vivo</button>
        </div>
        <p class="card-meta" id="dayZeroTrainHint">${canActivate ? "Modelo listo — activá para portería." : canTrain ? "Hay suficientes fotos — entrená el modelo." : "Completá fotos en los ítems anteriores (mín. 30 c/u)."}</p>`;
      $("#btnDayZeroTrain")?.addEventListener("click", async () => {
        const hint = $("#dayZeroTrainHint");
        if (hint) hint.textContent = "Entrenando…";
        try {
          const data = await api("/api/teach/train", { method: "POST" }, 60000);
          if (hint) hint.textContent = data.message;
          await refreshGuide();
          renderBody(lastGuide, eppCustom);
        } catch (e) {
          if (hint) hint.textContent = e.message;
        }
      });
      $("#btnDayZeroActivate")?.addEventListener("click", async () => {
        const hint = $("#dayZeroTrainHint");
        try {
          const data = await api("/api/teach/activate", { method: "POST" });
          if (hint) hint.textContent = "Modelo activo en monitoreo y portería";
          if (els.modelStatusText) els.modelStatusText.textContent = `Modelo faena · ${data.model}`;
          try {
            const health = await api("/api/health");
            applyHealth?.(health);
          } catch (_) {}
          await refreshGuide();
          renderBody(lastGuide, true);
        } catch (e) {
          if (hint) hint.textContent = e.message;
        }
      });
      return;
    }

    if (step === "done") {
      body.innerHTML = `
        <p class="day-zero-lead">Faena lista para portería</p>
        <ul class="day-zero-bullets">
          <li>Perfil EPP completo configurado</li>
          <li>Modelo entrenado con tu equipo</li>
          <li>Podés activar <strong>Modo portería</strong> en Vivo</li>
        </ul>`;
    }
  }

  function updateChrome(guide, eppCustom) {
    const { doneCount, total } = progressSummary(guide, eppCustom);
    if (els.dayZeroProgress) {
      els.dayZeroProgress.textContent = `Paso ${stepIdx + 1} de ${STEPS.length}`;
    }
    if (els.dayZeroTitle) {
      const titles = {
        intro: "Bienvenido · Día cero",
        profile: "Perfil de faena",
        train: "Entrenar y activar",
        done: "Configuración completa",
      };
      const ppe = currentPpeStep();
      els.dayZeroTitle.textContent = ppe ? `Entrenar ${ppe.label}` : titles[STEPS[stepIdx]] || "Configuración faena";
    }
    if (els.btnDayZeroBack) els.btnDayZeroBack.classList.toggle("hidden", stepIdx === 0);
    if (els.btnDayZeroNext) {
      const isLast = stepIdx >= STEPS.length - 1;
      els.btnDayZeroNext.textContent = STEPS[stepIdx] === "train" && faenaReady(progressSummary(guide, eppCustom).prog, guide, eppCustom)
        ? "Finalizar"
        : isLast
          ? "Cerrar"
          : "Siguiente";
    }
    if (els.dayZeroBanner) {
      els.dayZeroBanner.classList.toggle("hidden", !shouldShowBanner());
      els.dayZeroBanner.textContent = `Configuración faena ${doneCount}/${total} · Continuar`;
    }
  }

  async function refreshGuide() {
    try {
      lastGuide = await api("/api/teach/guide");
      teach?.updateModelBadgeFromGuide?.();
    } catch (_) {
      lastGuide = null;
    }
    return lastGuide;
  }

  async function openModal(force = false) {
    if (!isAdmin()) return;
    if (force) settings.dayZeroForceOpen = true;
    if (!shouldShowWizard() && !force) return;
    const health = await api("/api/health").catch(() => ({}));
    const eppCustom = !!health.epp_custom;
    const guide = (await refreshGuide()) || { classes: [], stats: {} };
    if (settings.dayZeroStep >= 0 && settings.dayZeroStep < STEPS.length) {
      stepIdx = settings.dayZeroStep;
    }
    renderBody(guide, eppCustom);
    updateChrome(guide, eppCustom);
    els.dayZeroWizard?.classList.remove("hidden");
    document.body.classList.add("day-zero-open");
  }

  function closeModal(dismiss = false) {
    settings.dayZeroStep = stepIdx;
    if (dismiss) {
      settings.dayZeroDismissed = true;
      settings.dayZeroForceOpen = false;
    }
    saveSettings(true);
    els.dayZeroWizard?.classList.add("hidden");
    document.body.classList.remove("day-zero-open");
    updateChrome(lastGuide || {}, false);
  }

  function completeWizard() {
    settings.dayZeroComplete = true;
    settings.dayZeroDismissed = false;
    settings.dayZeroForceOpen = false;
    saveSettings(true);
    closeModal(false);
    els.dayZeroBanner?.classList.add("hidden");
  }

  async function nextStep() {
    const health = await api("/api/health").catch(() => ({}));
    const eppCustom = !!health.epp_custom;
    const guide = (await refreshGuide()) || lastGuide || { classes: [], stats: {} };

    if (STEPS[stepIdx] === "train") {
      const { ready } = progressSummary(guide, eppCustom);
      if (ready) {
        stepIdx = STEPS.indexOf("done");
        renderBody(guide, eppCustom);
        updateChrome(guide, eppCustom);
        return;
      }
    }

    if (stepIdx >= STEPS.length - 1) {
      completeWizard();
      return;
    }

    stepIdx += 1;
    settings.dayZeroStep = stepIdx;
    saveSettings(true);
    renderBody(guide, eppCustom);
    updateChrome(guide, eppCustom);

    if (STEPS[stepIdx] === "done") {
      completeWizard();
    }
  }

  function prevStep() {
    if (stepIdx <= 0) return;
    stepIdx -= 1;
    settings.dayZeroStep = stepIdx;
    saveSettings(true);
    refreshGuide().then((guide) => {
      renderBody(guide || {}, false);
      updateChrome(guide || {}, false);
    });
  }

  function bindEvents() {
    els.btnDayZeroNext?.addEventListener("click", () => nextStep());
    els.btnDayZeroBack?.addEventListener("click", () => prevStep());
    els.btnDayZeroSkip?.addEventListener("click", () => closeModal(true));
    els.dayZeroBanner?.addEventListener("click", () => openModal(true));
    els.btnDayZeroReopen?.addEventListener("click", () => {
      settings.dayZeroForceOpen = true;
      stepIdx = settings.dayZeroStep || 0;
      openModal(true);
    });
    els.btnDayZeroReset?.addEventListener("click", () => {
      settings.dayZeroComplete = false;
      settings.dayZeroDismissed = false;
      settings.dayZeroStep = 0;
      stepIdx = 0;
      saveSettings(true);
      openModal(true);
    });
  }

  async function afterBoot() {
    if (!isAdmin()) return;
    const guide = await refreshGuide();
    const health = await api("/api/health").catch(() => ({}));
    updateChrome(guide || {}, !!health.epp_custom);
    if (shouldShowWizard()) {
      setTimeout(() => openModal(false), 600);
    }
  }

  return {
    bindEvents,
    afterBoot,
    openModal,
    refreshGuide,
    shouldShowBanner,
  };
}
