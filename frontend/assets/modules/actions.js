import { actionTeachProgress } from "../lib/teach-progress.js";

const SEV_LABEL = { critical: "Crítica", high: "Alta", medium: "Media", low: "Baja" };

const TYPE_LABEL = {
  epp_non_compliant: "Sin EPP en faena",
  fall_detected: "Caída",
  person_in_zone: "Persona en zona",
  detect_in_zone: "Objeto en zona",
  proximity: "Proximidad persona–objeto",
};

/** Pestaña Acciones: reglas, fuentes por cámara y distancia en metros. */
export function createActionsController({ api, els, setAppMode, teach }) {
  let rules = [];
  let settings = { meters_per_pixel: 0.045 };
  let sources = [{ id: "live", label: "Vivo / portería" }];
  let selectedId = null;

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function sourcesLabel(rule) {
    const src = rule.sources || ["*"];
    if (src.includes("*")) return "Todas las cámaras";
    if (src.length === 1) {
      const m = sources.find((s) => s.id === src[0]);
      return m?.label || src[0];
    }
    return `${src.length} cámaras`;
  }

  function selectedRule() {
    return rules.find((r) => r.id === selectedId) || null;
  }

  async function loadSources() {
    try {
      const data = await api("/api/actions/sources");
      sources = data.sources || sources;
    } catch (_) {}
  }

  async function loadRules() {
    await loadSources();
    const data = await api("/api/actions/rules");
    rules = data.rules || [];
    settings = data.settings || settings;
    render();
    renderDetail();
    syncCalibrationForm();
    await renderTeachProgress();
    return rules;
  }

  async function renderTeachProgress() {
    if (!els.actionsTeachList) return;
    try {
      const guide = await api("/api/teach/guide");
      const items = actionTeachProgress(guide.classes || [], guide);
      els.actionsTeachList.innerHTML = items.length
        ? items
            .map(
              (item) =>
                `<li class="${item.done ? "is-done" : ""}"><span>${escapeHtml(item.label)}</span><span class="muted">${item.count}/${item.min}</span></li>`
            )
            .join("")
        : `<li class="muted">Sin clases de acciones</li>`;
    } catch (_) {
      els.actionsTeachList.innerHTML = `<li class="muted">No se pudo cargar progreso</li>`;
    }
  }

  async function saveRules() {
    const data = await api("/api/actions/rules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rules }),
    });
    rules = data.rules || rules;
    render();
    renderDetail();
  }

  async function saveSettings() {
    const data = await api("/api/actions/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ settings }),
    });
    settings = data.settings || settings;
    syncCalibrationForm();
  }

  function syncCalibrationForm() {
    if (els.actionsMetersPerPixel) {
      els.actionsMetersPerPixel.value = String(settings.meters_per_pixel ?? 0.045);
    }
    if (els.actionsCalibHint && settings.reference) {
      els.actionsCalibHint.textContent = settings.reference;
    }
  }

  function render() {
    if (els.actionsRuleList) {
      els.actionsRuleList.innerHTML = rules.length
        ? rules
            .map((r) => {
              const on = !!r.enabled;
              const ctype = r.condition?.type || "—";
              const sel = r.id === selectedId ? " is-selected" : "";
              return `<li class="actions-rule${on ? "" : " is-off"}${sel}" data-rule-id="${escapeHtml(r.id)}">
                <label class="actions-rule-toggle">
                  <input type="checkbox" data-rule-id="${escapeHtml(r.id)}" ${on ? "checked" : ""} />
                  <span class="actions-rule-name">${escapeHtml(r.name)}</span>
                </label>
                <span class="actions-sev sev-${escapeHtml(r.severity || "medium")}">${escapeHtml(SEV_LABEL[r.severity] || r.severity || "Media")}</span>
                <span class="actions-type muted">${escapeHtml(TYPE_LABEL[ctype] || ctype)} · ${escapeHtml(sourcesLabel(r))}</span>
              </li>`;
            })
            .join("")
        : `<li class="muted">Sin reglas — agregá un preset</li>`;
    }
    if (els.actionsStats) {
      const on = rules.filter((r) => r.enabled).length;
      els.actionsStats.textContent = `${on} activa${on === 1 ? "" : "s"} · ${rules.length} total`;
    }
    if (els.actionsHint) {
      els.actionsHint.textContent =
        "Elegí una regla para editar cámaras y distancia. Entrená montacargas/celular en EPP.";
    }
  }

  function renderDetail() {
    const panel = els.actionsDetail;
    if (!panel) return;
    const r = selectedRule();
    if (!r) {
      panel.innerHTML = `<p class="muted">Seleccioná una regla de la lista para configurar cámaras y distancia.</p>`;
      return;
    }
    const cond = r.condition || {};
    const isProx = cond.type === "proximity";
    const allCam = (r.sources || []).includes("*");
    const srcChecks = sources
      .map((s) => {
        const on = allCam || (r.sources || []).includes(s.id);
        return `<label class="check actions-src-check"><input type="checkbox" data-src="${escapeHtml(s.id)}" ${on ? "checked" : ""} ${allCam ? "disabled" : ""}/> ${escapeHtml(s.label)}</label>`;
      })
      .join("");
    const meters =
      cond.max_distance_meters != null ? cond.max_distance_meters : cond.type === "proximity" ? 3 : "";
    panel.innerHTML = `
      <p class="card-kicker">Editar regla</p>
      <p class="actions-detail-name">${escapeHtml(r.name)}</p>
      <label class="field">
        <span>Nombre</span>
        <input type="text" id="actionsEditName" value="${escapeHtml(r.name)}" />
      </label>
      <label class="check"><input type="checkbox" id="actionsEditAllCam" ${allCam ? "checked" : ""}/> Todas las cámaras (vivo + NVR)</label>
      <div class="actions-src-grid" id="actionsSrcGrid">${srcChecks}</div>
      ${
        isProx
          ? `<label class="field cfg-slider-row">
        <span>Distancia máxima · <b id="actionsMetersVal">${meters}</b> m</span>
        <input type="range" id="actionsEditMeters" min="0.5" max="15" step="0.5" value="${meters || 3}" />
      </label>`
          : ""
      }
      <div class="actions-detail-actions">
        <button type="button" class="btn primary" id="btnActionsSaveRule">Guardar regla</button>
        ${
          ["montacargas", "celular", "carga_suspendida"].some((k) => (r.name + r.id).toLowerCase().includes(k.replace("_", "")) || (cond.object_keywords || []).join(" ").includes(k.split("_")[0]))
            ? `<button type="button" class="btn secondary" id="btnActionsTrain">Entrenar detección en EPP</button>`
            : ""
        }
      </div>`;

    panel.querySelector("#btnActionsSaveRule")?.addEventListener("click", () => saveDetail(r.id));
    panel.querySelector("#btnActionsTrain")?.addEventListener("click", () => openTeachForRule(r));
    const metersEl = panel.querySelector("#actionsEditMeters");
    metersEl?.addEventListener("input", () => {
      const v = panel.querySelector("#actionsMetersVal");
      if (v) v.textContent = metersEl.value;
    });
  }

  function openTeachForRule(r) {
    const cond = r.condition || {};
    let cls = "montacargas";
    const kws = (cond.object_keywords || []).join(" ").toLowerCase();
    if (kws.includes("cell") || kws.includes("celular") || kws.includes("phone")) cls = "celular";
    else if (kws.includes("carga") || kws.includes("suspend")) cls = "carga_suspendida";
    setAppMode?.("teach");
    if (els.teachClass) els.teachClass.value = cls;
    teach?.refreshTeach?.();
  }

  async function saveDetail(ruleId) {
    const r = rules.find((x) => x.id === ruleId);
    const panel = els.actionsDetail;
    if (!r || !panel) return;
    r.name = panel.querySelector("#actionsEditName")?.value?.trim() || r.name;
    r.message = r.name;
    const allCam = panel.querySelector("#actionsEditAllCam")?.checked;
    if (allCam) {
      r.sources = ["*"];
    } else {
      r.sources = [...panel.querySelectorAll("[data-src]:checked")].map((el) => el.getAttribute("data-src"));
      if (!r.sources.length) r.sources = ["live"];
    }
    const meters = panel.querySelector("#actionsEditMeters");
    if (meters && r.condition?.type === "proximity") {
      r.condition.max_distance_meters = parseFloat(meters.value) || 3;
    }
    await saveRules();
  }

  async function refreshPresets() {
    if (!els.actionsPresetSelect) return;
    const data = await api("/api/actions/presets");
    const presets = data.presets || [];
    els.actionsPresetSelect.innerHTML =
      `<option value="">— Agregar preset —</option>` +
      presets.map((p) => `<option value="${escapeHtml(p.id)}">${escapeHtml(p.name)}</option>`).join("");
  }

  function bindEvents() {
    els.actionsRuleList?.addEventListener("change", async (e) => {
      const cb = e.target.closest("input[data-rule-id]");
      if (!cb || e.target.type !== "checkbox") return;
      const id = cb.getAttribute("data-rule-id");
      const rule = rules.find((r) => r.id === id);
      if (rule) {
        rule.enabled = cb.checked;
        await saveRules();
      }
    });

    els.actionsRuleList?.addEventListener("click", (e) => {
      const row = e.target.closest("[data-rule-id]");
      if (!row || e.target.type === "checkbox") return;
      selectedId = row.getAttribute("data-rule-id");
      render();
      renderDetail();
    });

    els.btnActionsAddPreset?.addEventListener("click", async () => {
      const pid = els.actionsPresetSelect?.value;
      if (!pid) return;
      await api(`/api/actions/presets/${encodeURIComponent(pid)}`, { method: "POST" });
      await loadRules();
    });

    els.btnActionsReset?.addEventListener("click", async () => {
      if (!confirm("¿Restaurar reglas predeterminadas de acciones inseguras?")) return;
      await api("/api/actions/rules/reset", { method: "POST" });
      selectedId = null;
      await loadRules();
    });

    els.btnActionsOpenZones?.addEventListener("click", () => {
      document.querySelector('.mode-btn[data-mode="config"]')?.click();
      setTimeout(() => document.querySelector('.cfg-nav-btn[data-cfg-sec="zones"]')?.click(), 200);
    });

    els.actionsMetersPerPixel?.addEventListener("change", async () => {
      settings.meters_per_pixel = parseFloat(els.actionsMetersPerPixel.value) || 0.045;
      await saveSettings();
    });

    els.btnActionsOpenTeach?.addEventListener("click", () => {
      setAppMode?.("teach");
      if (els.teachClass) els.teachClass.value = "montacargas";
      teach?.refreshTeach?.();
    });
  }

  return { loadRules, refreshPresets, bindEvents, render, renderTeachProgress };
}
