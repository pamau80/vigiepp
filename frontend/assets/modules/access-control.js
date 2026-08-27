/** RBAC frontend — permisos granulares y visibilidad por rol. */

export const PERM_ALL = "*";

export const MODE_PERMISSIONS = {
  live: "live.view",
  mass: "mass.view",
  devices: "devices.view",
  identity: "identity.view",
  teach: "teach.use",
  config: "config.view",
  reports: "reports.view",
};

export const CFG_SECTION_PERMISSIONS = {
  guides: "config.view",
  audio: "config.view",
  zones: "config.manage",
  monitor: "config.view",
  privacy: "config.manage",
  enterprise: "enterprise.manage",
  audit: "audit.view",
  users: "users.manage",
};

export function canAccess(permissions, perm) {
  const grants = permissions || [];
  if (grants.includes(PERM_ALL)) return true;
  return grants.includes(perm);
}

export function canAny(permissions, perms) {
  return (perms || []).some((p) => canAccess(permissions, p));
}

export function roleLabel(role) {
  if (role === "admin") return "Administrador";
  if (role === "guard") return "Guardia · sala de cámaras";
  if (role === "operator") return "Portería";
  return role || "Usuario";
}

export function applyNavVisibility(permissions) {
  document.querySelectorAll(".mode-btn").forEach((btn) => {
    const mode = btn.dataset.mode;
    const perm = MODE_PERMISSIONS[mode];
    const allow = !perm || canAccess(permissions, perm);
    btn.classList.toggle("hidden", !allow);
    btn.disabled = !allow;
  });

  document.querySelectorAll(".cfg-nav-btn").forEach((btn) => {
    const sec = btn.getAttribute("data-cfg-sec");
    const perm = CFG_SECTION_PERMISSIONS[sec];
    const allow = !perm || canAccess(permissions, perm);
    btn.classList.toggle("hidden", !allow);
    btn.disabled = !allow;
  });

  const usersSec = document.querySelector('[data-cfg-section="users"]');
  if (usersSec) {
    usersSec.classList.toggle("hidden", !canAccess(permissions, "users.manage"));
  }
}

export function readStoredPermissions() {
  try {
    const raw = sessionStorage.getItem("vigiepp.permissions");
    if (raw) return JSON.parse(raw);
  } catch (_) {}
  return [PERM_ALL];
}

export function storeAccessProfile(profile) {
  sessionStorage.setItem("vigiepp.role", profile?.role || "admin");
  sessionStorage.setItem("vigiepp.permissions", JSON.stringify(profile?.permissions || [PERM_ALL]));
  if (profile?.display_name) sessionStorage.setItem("vigiepp.display_name", profile.display_name);
}

export function clearStoredAccess() {
  sessionStorage.removeItem("vigiepp.role");
  sessionStorage.removeItem("vigiepp.permissions");
  sessionStorage.removeItem("vigiepp.display_name");
}
