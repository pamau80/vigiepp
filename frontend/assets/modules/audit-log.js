import { $, escapeHtml } from "./dom.js";

/** Lista de eventos de auditoría en configuración. */
export function createAuditLogController({ api }) {
  async function refreshAudit() {
    const list = $("#auditList");
    if (!list) return;
    try {
      const data = await api("/api/audit?limit=60");
      const ev = data.events || [];
      list.innerHTML = ev.length
        ? ev
            .map((e) => {
              const ts = (e.ts || "").replace("T", " ").slice(0, 19);
              return `<li><span>${escapeHtml(e.action)}</span><span class="conf">${escapeHtml(ts)} · ${escapeHtml(e.detail || "")}</span></li>`;
            })
            .join("")
        : `<li class="muted">Sin eventos</li>`;
    } catch (err) {
      list.innerHTML = `<li class="muted">${escapeHtml(err.message || "No se pudo cargar")}</li>`;
    }
  }

  function bindAuditEvents() {
    $("#btnAuditExport")?.addEventListener("click", () => {
      window.open("/api/audit/export", "_blank");
    });
    $("#btnAuditRefresh")?.addEventListener("click", () => refreshAudit());
  }

  return { refreshAudit, bindAuditEvents };
}
