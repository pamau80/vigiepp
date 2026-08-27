import { $ } from "./dom.js";

/** Exportar / importar backup de personas enroladas. */
export function createIdentityBackupController({ els, workers, ensureAuth }) {
  async function authHeaders() {
    const headers = {};
    const token = sessionStorage.getItem("vigiepp.token");
    if (token) headers["X-VigiEPP-Key"] = token;
    return headers;
  }

  function bindBackupEvents(downloadUrl) {
    $("#btnBackupExport")?.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/identity/backup", {
          credentials: "include",
          headers: await authHeaders(),
        });
        if (res.status === 401) {
          await ensureAuth(true);
          throw new Error("Sesión expirada");
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const blob = await res.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `vigiepp-personas-${new Date().toISOString().slice(0, 10)}.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(a.href);
        if (els.workerListHint) els.workerListHint.textContent = "Backup descargado";
      } catch (err) {
        if (els.workerListHint) els.workerListHint.textContent = err.message || "No se pudo exportar";
      }
    });

    $("#btnConsentExport")?.addEventListener("click", () => {
      downloadUrl("/api/identity/consent.csv");
    });

    $("#backupImportFile")?.addEventListener("change", async (e) => {
      const file = e.target.files?.[0];
      e.target.value = "";
      if (!file) return;
      const mode = $("#backupImportMode")?.value || "merge";
      if (mode === "replace" && !confirm("¿Reemplazar TODAS las personas por el backup?")) return;
      const fd = new FormData();
      fd.append("file", file);
      fd.append("mode", mode);
      try {
        if (els.workerListHint) els.workerListHint.textContent = "Restaurando…";
        const res = await fetch("/api/identity/backup/restore", {
          method: "POST",
          credentials: "include",
          headers: await authHeaders(),
          body: fd,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        await workers.refreshWorkers();
        if (els.workerListHint) {
          els.workerListHint.textContent =
            mode === "replace"
              ? `Restaurado · ${data.workers || 0} personas`
              : `Fusionado · +${data.added || 0} / ~${data.updated || 0} · total ${data.workers || 0}`;
        }
      } catch (err) {
        if (els.workerListHint) els.workerListHint.textContent = err.message || "Restore falló";
      }
    });
  }

  return { bindBackupEvents };
}
