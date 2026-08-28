const SEV_LABEL = { critical: "Crítica", high: "Alta", medium: "Media", low: "Baja" };
const TYPE_LABEL = {
  epp_non_compliant: "Sin EPP en faena",
  fall_detected: "Caída",
  person_in_zone: "Persona en zona",
  detect_in_zone: "Objeto en zona",
  proximity: "Proximidad persona–objeto",
};

/** Pestaña Acciones: reglas de conductas inseguras. */
export function createActionsController({ api, els }) {
  let rules = [];

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function loadRules() {
    const data = await api("/api/actions/rules");
    rules = data.rules || [];
    render();
    return rules;
  }

  async function saveRules() {
    await api("/api/actions/rules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rules }),
    });
    render();
  }

  function render() {
    if (els.actionsRuleList) {
      els.actionsRuleList.innerHTML = rules.length
        ? rules
            .map((r) => {
              const on = !!r.enabled;
              const ctype = r.condition?.type || "—";
              return `<li class="actions-rule${on ? "" : " is-off"}">
                <label class="actions-rule-toggle">
                  <input type="checkbox" data-rule-id="${escapeHtml(r.id)}" ${on ? "checked" : ""} />
                  <span class="actions-rule-name">${escapeHtml(r.name)}</span>
                </label>
                <span class="actions-sev sev-${escapeHtml(r.severity || "medium")}">${escapeHtml(SEV_LABEL[r.severity] || r.severity || "Media")}</span>
                <span class="actions-type muted">${escapeHtml(TYPE_LABEL[ctype] || ctype)}</span>
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
        "Las alertas aparecen en Vivo y Masivo. Entrená clases (montacargas, celular…) en EPP para mejor detección.";
    }
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
      if (!cb) return;
      const id = cb.getAttribute("data-rule-id");
      const rule = rules.find((r) => r.id === id);
      if (rule) {
        rule.enabled = cb.checked;
        await saveRules();
      }
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
      await loadRules();
    });

    els.btnActionsOpenZones?.addEventListener("click", () => {
      document.querySelector('.mode-btn[data-mode="config"]')?.click();
      setTimeout(() => document.querySelector('.cfg-nav-btn[data-cfg-sec="zones"]')?.click(), 200);
    });
  }

  return { loadRules, refreshPresets, bindEvents, render };
}
