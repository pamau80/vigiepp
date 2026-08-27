import { $ } from "./dom.js";

/** Eventos globales: logout, upload de archivo y resize de canvas. */
export function createAppShellEventsController({ els, ensureAuth, detectBlob, camera }) {
  function bindShellEvents() {
    $("#btnLogout")?.addEventListener("click", async () => {
      try {
        await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
      } catch (_) {}
      sessionStorage.removeItem("vigiepp.token");
      clearStoredAccess();
      await ensureAuth(true);
    });

    els.fileInput.addEventListener("change", async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      await detectBlob(file, { identify: true, returnImage: true });
    });

    window.addEventListener("resize", () => {
      if (camera.hasMediaStream()) camera.syncCanvasSize();
    });
  }

  return { bindShellEvents };
}
