import { $ } from "./dom.js";

/** Modo portería / kiosk con salida protegida por PIN admin. */
export function createKioskController({
  settings,
  saveSettings,
  els,
  setAppMode,
  applyRoleUI,
  displayPersonName,
  getLastIdentity,
}) {
  function setKioskMode(on) {
    settings.kioskMode = !!on;
    saveSettings(true);
    document.body.classList.toggle("kiosk-mode", settings.kioskMode);
    $("#kioskOverlay")?.classList.toggle("hidden", !settings.kioskMode);
    const btn = $("#btnKiosk");
    if (btn) btn.classList.toggle("active", settings.kioskMode);
    if (settings.kioskMode) {
      setAppMode("live");
      if (els.chkIdentify) {
        els.chkIdentify.checked = true;
        settings.identifyDefault = true;
      }
    }
  }

  async function requestAdminPinToExitKiosk() {
    const pin = window.prompt("Salir de portería requiere PIN de administrador:");
    if (pin == null) return false;
    if (!String(pin).trim()) return false;
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin: String(pin).trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        window.alert(data.detail || "PIN incorrecto");
        return false;
      }
      if ((data.role || "") !== "admin") {
        window.alert("Solo el PIN de administrador puede salir del modo portería.");
        return false;
      }
      if (data.token) sessionStorage.setItem("vigiepp.token", data.token);
      applyRoleUI("admin");
      return true;
    } catch (err) {
      window.alert(err.message || "Error de red");
      return false;
    }
  }

  async function exitKioskSafe() {
    if (!settings.kioskMode) return;
    const ok = await requestAdminPinToExitKiosk();
    if (ok) setKioskMode(false);
  }

  function updateKioskBanner(payload) {
    if (!settings.kioskMode) return;
    const c = payload?.compliance || {};
    const ok = !!c.overall_compliant;
    const hasPeople = (c.persons || []).length > 0 || (payload?.detections || []).length > 0;
    const id = payload?.identity || getLastIdentity();
    const res = $("#kioskResult");
    const name = $("#kioskName");
    const detail = $("#kioskDetail");
    const overlay = $("#kioskOverlay");
    if (!res || !overlay) return;
    overlay.dataset.state = !hasPeople ? "idle" : ok ? "ok" : "bad";
    res.textContent = !hasPeople ? "En espera" : ok ? "CUMPLE" : "NO CUMPLE";
    if (name) {
      name.textContent =
        id?.known && id?.name ? displayPersonName(id.name) : hasPeople ? "Sin identificar" : "Acercá a la cámara";
    }
    if (detail) {
      const miss = (c.persons?.[0]?.missing || []).slice(0, 3).join(", ");
      detail.textContent = !hasPeople ? "" : ok ? id?.rut || "EPP OK" : miss || c.summary || "Revisá EPP";
    }
  }

  function bindKioskEvents() {
    $("#btnKiosk")?.addEventListener("click", () => {
      if (settings.kioskMode) {
        exitKioskSafe();
      } else {
        setKioskMode(true);
      }
    });
    $("#btnKioskExit")?.addEventListener("click", () => {
      exitKioskSafe();
    });
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && settings.kioskMode) {
        e.preventDefault();
        exitKioskSafe();
      }
    });
  }

  return {
    setKioskMode,
    exitKioskSafe,
    updateKioskBanner,
    bindKioskEvents,
  };
}
