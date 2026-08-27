import { $, $$ } from "./dom.js";
import {
  applyNavVisibility,
  clearStoredAccess,
  readStoredPermissions,
  roleLabel,
  storeAccessProfile,
} from "./access-control.js";

/** Control de login PIN / sesión y UI por rol + permisos RBAC. */
export function createAuthController({ onPorteriaLogin } = {}) {
  let userRole = "admin";
  let permissions = ["*"];
  let displayName = "Administrador";

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

  function getPermissions() {
    return permissions;
  }

  function applyRoleUI(profileOrRole) {
    const profile =
      typeof profileOrRole === "object" && profileOrRole
        ? profileOrRole
        : { role: profileOrRole, permissions: readStoredPermissions() };

    userRole = profile.role || "admin";
    permissions = profile.permissions || readStoredPermissions();
    displayName = profile.display_name || roleLabel(userRole);

    storeAccessProfile({ role: userRole, permissions, display_name: displayName });
    document.body.dataset.role = userRole;
    applyNavVisibility(permissions);

    const tag = $(".brand-tag");
    if (tag) {
      tag.textContent =
        userRole === "admin"
          ? "EPP + identidad · Chile"
          : `${displayName} · ${roleLabel(userRole)}`;
    }

    if (userRole === "operator" && onPorteriaLogin) onPorteriaLogin();
  }

  async function ensureAuth(force = false) {
    try {
      const st = await fetch("/api/auth/status", { credentials: "include" }).then((r) => r.json());
      if (!st.auth_enabled) {
        showAuthGate(false);
        $("#btnLogout")?.classList.add("hidden");
        applyRoleUI({ role: "admin", permissions: ["*"], display_name: "Administrador" });
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
          applyRoleUI(data);
          return true;
        }
      }
    } catch (_) {
      /* mostrar gate */
    }

    return new Promise((resolve) => {
      showAuthGate(true, "PIN administrador o guardia autorizado");
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
          applyRoleUI(data);
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

  function logoutLocal() {
    clearStoredAccess();
    sessionStorage.removeItem("vigiepp.token");
  }

  return { ensureAuth, showAuthGate, applyRoleUI, getRole, getPermissions, logoutLocal };
}
