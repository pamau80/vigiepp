import { $ } from "./dom.js";

/** Sitios multi-faena y conectores EHS (config enterprise). */
export function createEnterpriseController(api) {
  async function refreshSitesUi() {
    const sel = $("#cfgSiteSelect");
    if (!sel) return;
    try {
      const data = await api("/api/sites");
      sel.innerHTML = (data.sites || [])
        .map(
          (s) =>
            `<option value="${s.id}" ${s.id === data.active_site_id ? "selected" : ""}>${s.name}</option>`
        )
        .join("");
    } catch (_) {
      sel.innerHTML = `<option value="default">Faena principal</option>`;
    }
  }

  async function refreshEhsUi() {
    const hint = $("#cfgEhsHint");
    const urlEl = $("#cfgEhsWebhookUrl");
    const enEl = $("#cfgEhsWebhookEnabled");
    const authEl = $("#cfgEhsWebhookAuth");
    const safetyUrl = $("#cfgEhsSafetyUrl");
    const safetyKey = $("#cfgEhsSafetyKey");
    const safetySite = $("#cfgEhsSafetySite");
    const safetyEn = $("#cfgEhsSafetyEnabled");
    const sapUrl = $("#cfgEhsSapUrl");
    const sapClient = $("#cfgEhsSapClient");
    const sapPlant = $("#cfgEhsSapPlant");
    const sapEn = $("#cfgEhsSapEnabled");
    if (!urlEl) return;
    try {
      const data = await api("/api/ehs/config");
      const c = data.config?.connectors || {};
      const w = c.webhook || {};
      const sc = c.safetycloud || {};
      const sap = c.sap_ewm || {};
      urlEl.value = w.url || "";
      if (enEl) enEl.checked = !!w.enabled;
      if (authEl) {
        authEl.value = "";
        authEl.placeholder = w.auth_header_set ? "Configurado — nuevo valor para cambiar" : "Bearer …";
      }
      if (safetyUrl) safetyUrl.value = sc.url || "";
      if (safetySite) safetySite.value = sc.site_code || "";
      if (safetyEn) safetyEn.checked = !!sc.enabled;
      if (safetyKey) {
        safetyKey.value = "";
        safetyKey.placeholder = sc.api_key_set ? "Configurado — nuevo valor para cambiar" : "API key";
      }
      if (sapUrl) sapUrl.value = sap.url || "";
      if (sapPlant) sapPlant.value = sap.plant || "";
      if (sapEn) sapEn.checked = !!sap.enabled;
      if (sapClient) {
        sapClient.value = "";
        sapClient.placeholder = sap.client_id_set ? "Configurado — nuevo valor para cambiar" : "Client ID";
      }
      const active = [w.enabled && "Webhook", sc.enabled && "SafetyCloud", sap.enabled && "SAP"].filter(Boolean);
      if (hint) hint.textContent = active.length ? `Activos: ${active.join(", ")}` : "Sin conectores EHS activos";
    } catch (e) {
      if (hint) hint.textContent = String(e.message || e);
    }
  }

  async function saveEhsConfig() {
    const connectors = {
      webhook: {
        url: ($("#cfgEhsWebhookUrl")?.value || "").trim(),
        enabled: !!$("#cfgEhsWebhookEnabled")?.checked,
      },
      safetycloud: {
        url: ($("#cfgEhsSafetyUrl")?.value || "").trim(),
        enabled: !!$("#cfgEhsSafetyEnabled")?.checked,
        site_code: ($("#cfgEhsSafetySite")?.value || "").trim(),
      },
      sap_ewm: {
        url: ($("#cfgEhsSapUrl")?.value || "").trim(),
        enabled: !!$("#cfgEhsSapEnabled")?.checked,
        plant: ($("#cfgEhsSapPlant")?.value || "").trim(),
      },
    };
    const authHdr = ($("#cfgEhsWebhookAuth")?.value || "").trim();
    if (authHdr) connectors.webhook.auth_header = authHdr;
    const scKey = ($("#cfgEhsSafetyKey")?.value || "").trim();
    if (scKey) connectors.safetycloud.api_key = scKey;
    const sapClientVal = ($("#cfgEhsSapClient")?.value || "").trim();
    if (sapClientVal) connectors.sap_ewm.client_id = sapClientVal;
    await api("/api/ehs/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ connectors }),
    });
    await refreshEhsUi();
  }

  function updateEnterpriseHints(health, { combinedInference = false, els: elsRef } = {}) {
    const hint = $("#cfgCombinedHint");
    const ent = $("#cfgEnterpriseHint");
    if (hint) {
      hint.textContent = combinedInference
        ? "Inferencia combinada activa: ID + EPP en el mismo frame (edge / volumen persistente)."
        : "Inferencia separada: alterna EPP e identidad para evitar OOM en cloud.";
    }
    if (ent && health) {
      const site = health.active_site?.name || "Faena principal";
      ent.textContent = `Sitio activo: ${site} · datos en ${health.data_dir || "—"}`;
    }
    const oidcBtn = $("#btnOidcLogin");
    if (oidcBtn) {
      oidcBtn.hidden = !health?.oidc?.enabled;
    }
    if (elsRef?.modelStatusText && health?.production_pin_warning) {
      elsRef.modelStatusText.textContent = "⚠ Configura PIN en producción";
    }
  }

  return { refreshSitesUi, refreshEhsUi, saveEhsConfig, updateEnterpriseHints };
}
