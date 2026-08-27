import { $, $$ } from "./dom.js";

/** Control de login PIN / sesión y UI por rol. */
export function createAuthController({ onOperatorLogin } = {}) {
  let userRole = "admin";

  function showAuthGate(show, hint = "") {
    const gate = $("#authGate");
    if (!gate) return;
    gate.classList.toggle("hidden", !show);
    document.body.classList.toggle("auth-locked", !!show);
    const h = $("#authHint");
    if (h) h.textContent = hint || "";
    if (show) $("#authPin")?.focus();
  }

  function getRole() {
    return userRole;
  }

  function applyRoleUI(role) {
    userRole = role || "admin";
    sessionStorage.setItem("vigiepp.role", userRole);
    document.body.dataset.role = userRole;
    const isOp = userRole === "operator";
    $$(".mode-btn").forEach((b) => {
      const mode = b.dataset.mode;
      const allow = !isOp || mode === "live" || mode === "monitor";
      b.classList.toggle("hidden", !allow);
      b.disabled = !allow;
    });
    if (isOp && onOperatorLogin) onOperatorLogin();
    const tag = $(".brand-tag");
    if (tag) tag.textContent = isOp ? "Portería · operador" : "EPP + identidad · Chile";
  }

  async function ensureAuth(force = false) {
    try {
      const st = await fetch("/api/auth/status", { credentials: "include" }).then((r) => r.json());
      if (!st.auth_enabled) {
        showAuthGate(false);
        $("#btnLogout")?.classList.add("hidden");
        applyRoleUI("admin");
        return true;
      }
      if (!force) {
        const me = await fetch("/api/auth/me", {
          credentials: "include",
          headers: sessionStorage.getItem("vigiepp.token")
            ? { "X-VigiEPP-Key": sessionStorage.getItem("vigiepp.token") }
            : {},
        });
        if (me.ok) {
          const data = await me.json().catch(() => ({}));
          showAuthGate(false);
          $("#btnLogout")?.classList.remove("hidden");
          applyRoleUI(data.role || sessionStorage.getItem("vigiepp.role") || "admin");
          return true;
        }
      }
    } catch (_) {
      /* mostrar gate */
    }

    return new Promise((resolve) => {
      showAuthGate(true, "PIN admin o portería (operador)");
      const form = $("#authForm");
      const onSubmit = async (e) => {
        e.preventDefault();
        const pin = $("#authPin")?.value || "";
        const hint = $("#authHint");
        try {
          const res = await fetch("/api/auth/login", {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pin }),
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            if (hint) hint.textContent = data.detail || "PIN incorrecto";
            return;
          }
          if (data.token) sessionStorage.setItem("vigiepp.token", data.token);
          applyRoleUI(data.role || "admin");
          showAuthGate(false);
          $("#btnLogout")?.classList.remove("hidden");
          form?.removeEventListener("submit", onSubmit);
          resolve(true);
        } catch (err) {
          if (hint) hint.textContent = err.message || "Error de red";
        }
      };
      form?.addEventListener("submit", onSubmit);
    });
  }

  return { ensureAuth, showAuthGate, applyRoleUI, getRole };
}
