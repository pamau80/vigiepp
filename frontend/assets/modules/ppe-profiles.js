import { $, escapeHtml } from "./dom.js";

const PPE_LABEL = {
  casco: "Casco",
  chaleco: "Chaleco / flúor",
  lentes: "Lentes",
  guantes: "Guantes",
  arnes: "Arnés",
};

/** Perfiles de faena y chips de EPP obligatorio por perfil. */
export function createPpeProfilesController({ api, els, settings, saveSettings }) {
  let profiles = [];
  let ppeCatalog = [];

  function catalogItems() {
    if (ppeCatalog.length) return ppeCatalog;
    return Object.entries(PPE_LABEL).map(([id, label]) => ({ id, label }));
  }

  function getProfileDefaults(profileId) {
    const p = profiles.find((x) => x.id === profileId);
    return p ? [...(p.required || [])] : [];
  }

  function getEffectiveRequired(profileId) {
    const pid = profileId || els.profileSelect?.value || "general";
    if (settings.ppeByProfile && Object.prototype.hasOwnProperty.call(settings.ppeByProfile, pid)) {
      return [...(settings.ppeByProfile[pid] || [])];
    }
    return getProfileDefaults(pid);
  }

  function setProfileRequired(profileId, list) {
    if (!settings.ppeByProfile) settings.ppeByProfile = {};
    settings.ppeByProfile[profileId] = [...list];
    saveSettings(true);
  }

  function resetProfileRequired(profileId) {
    if (!settings.ppeByProfile) return;
    delete settings.ppeByProfile[profileId];
    saveSettings(true);
  }

  function renderPpeSelector(container, profileId) {
    if (!container) return;
    const pid = profileId || els.profileSelect?.value || "general";
    const required = new Set(getEffectiveRequired(pid));
    container.innerHTML = catalogItems()
      .map((item) => {
        const on = required.has(item.id);
        return `<button type="button" class="chip ppe-toggle" data-ppe="${escapeHtml(item.id)}" aria-pressed="${on ? "true" : "false"}">${escapeHtml(item.label)}</button>`;
      })
      .join("");
  }

  function renderProfile() {
    const p = profiles.find((x) => x.id === els.profileSelect.value);
    if (!p) return;
    els.profileDesc.textContent = p.description || p.name;
    const req = getEffectiveRequired(p.id);
    const custom = settings.ppeByProfile && Object.prototype.hasOwnProperty.call(settings.ppeByProfile, p.id);
    const hint = $("#ppeSelectHint");
    if (hint) {
      hint.textContent = custom
        ? `Personalizado (${req.length} obligatorio${req.length === 1 ? "" : "s"}). Tocá para cambiar.`
        : "Tocá cada ítem para marcarlo obligatorio u opcional.";
    }
    renderPpeSelector(els.requiredChips, p.id);
    renderPpeSelector(els.cfgPpeChips, p.id);
  }

  function bindPpeChipContainer(container) {
    if (!container || container._ppeBound) return;
    container._ppeBound = true;
    container.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-ppe]");
      if (!btn) return;
      const key = btn.getAttribute("data-ppe");
      const pid = els.profileSelect?.value || "general";
      const req = new Set(getEffectiveRequired(pid));
      if (req.has(key)) req.delete(key);
      else req.add(key);
      setProfileRequired(pid, [...req]);
      renderProfile();
    });
  }

  function requiredQueryValue(profileId) {
    return JSON.stringify(getEffectiveRequired(profileId || els.profileSelect?.value || "general"));
  }

  async function loadProfiles() {
    try {
      profiles = await api("/api/profiles");
      els.profileSelect.innerHTML = profiles
        .map((p) => `<option value="${p.id}">${p.name}</option>`)
        .join("");
      els.profileSelect.value = "portuario";
    } catch (err) {
      console.error(err);
    }
  }

  async function loadCatalog() {
    try {
      const cat = await api("/api/ppe/catalog");
      ppeCatalog = cat.items || [];
    } catch (_) {
      ppeCatalog = catalogItems();
    }
  }

  function bindProfileEvents() {
    els.profileSelect.addEventListener("change", renderProfile);
    els.btnResetPpe?.addEventListener("click", () => {
      resetProfileRequired(els.profileSelect.value);
      renderProfile();
    });
    els.btnCfgResetPpe?.addEventListener("click", () => {
      resetProfileRequired(els.profileSelect.value);
      renderProfile();
    });
  }

  return {
    get profiles() {
      return profiles;
    },
    loadProfiles,
    loadCatalog,
    renderProfile,
    bindPpeChipContainer,
    bindProfileEvents,
    requiredQueryValue,
    resetProfileRequired,
  };
}
