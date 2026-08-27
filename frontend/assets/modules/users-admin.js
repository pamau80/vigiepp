import { escapeHtml } from "./dom.js";
import { canAccess, roleLabel } from "./access-control.js";

/** Panel admin — gestión de guardias y permisos (SaaS). */
export function createUsersAdminController({ api, els }) {
  let catalog = { permissions: [], roles: [] };

  async function loadCatalog() {
    try {
      const data = await api("/api/auth/permissions");
      catalog = data || catalog;
      fillPermCheckboxes(els.userNewExtra, [], "extra");
    } catch (_) {}
  }

  function permLabel(id) {
    const row = (catalog.permissions || []).find((p) => p.id === id);
    return row?.label || id;
  }

  function renderUsers(users) {
    const list = els.usersList;
    if (!list) return;
    if (!users?.length) {
      list.innerHTML = `<li class="muted">Sin cuentas de guardia. Creá una abajo.</li>`;
      return;
    }
    list.innerHTML = users
      .map((u) => {
        const extras = (u.extra_permissions || []).map((p) => `<span class="chip">${escapeHtml(permLabel(p))}</span>`).join(" ");
        const revoked = (u.revoked_permissions || []).length
          ? `<span class="muted"> (−${u.revoked_permissions.length} revocados)</span>`
          : "";
        const sites =
          u.site_ids?.length && !u.site_ids.includes("*")
            ? `<span class="muted"> · faenas: ${escapeHtml(u.site_ids.join(", "))}</span>`
            : `<span class="muted"> · todas las faenas</span>`;
        return `<li class="user-row" data-user-id="${escapeHtml(u.id)}">
          <strong>${escapeHtml(u.name)}</strong>
          <span class="muted"> · ${escapeHtml(roleLabel(u.role))}${u.active ? "" : " (inactivo)"}</span>
          ${sites}
          <div class="user-perms">${extras}${revoked}</div>
          <div class="user-actions">
            <button type="button" class="btn ghost btn-user-edit" data-id="${escapeHtml(u.id)}">Editar</button>
            <button type="button" class="btn ghost btn-user-toggle" data-id="${escapeHtml(u.id)}" data-active="${u.active ? "1" : "0"}">${u.active ? "Desactivar" : "Activar"}</button>
          </div>
        </li>`;
      })
      .join("");

    list.querySelectorAll(".btn-user-edit").forEach((btn) => {
      btn.addEventListener("click", () => openEditor(btn.dataset.id, users));
    });
    list.querySelectorAll(".btn-user-toggle").forEach((btn) => {
      btn.addEventListener("click", () => toggleUser(btn.dataset.id, btn.dataset.active !== "1"));
    });
  }

  function fillPermCheckboxes(container, selected, prefix) {
    if (!container) return;
    container.innerHTML = (catalog.permissions || [])
      .map(
        (p) => `<label class="cfg-toggle-row">
          <span>${escapeHtml(p.label)}</span>
          <input type="checkbox" name="${prefix}" value="${escapeHtml(p.id)}" ${selected.includes(p.id) ? "checked" : ""} />
        </label>`
      )
      .join("");
  }

  function openEditor(userId, users) {
    const u = users.find((x) => x.id === userId);
    if (!u || !els.userEditPanel) return;
    els.userEditName.value = u.name || "";
    els.userEditRole.value = u.role || "guard";
    els.userEditPin.value = "";
    els.userEditSites.value = (u.site_ids || []).join(", ");
    fillPermCheckboxes(els.userEditExtra, u.extra_permissions || [], "extra");
    fillPermCheckboxes(els.userEditRevoked, u.revoked_permissions || [], "revoked");
    els.userEditPanel.dataset.userId = userId;
    els.userEditPanel.classList.remove("hidden");
    if (els.usersHint) els.usersHint.textContent = `Editando: ${u.name}`;
  }

  async function refreshUsers() {
    if (!canAccess(JSON.parse(sessionStorage.getItem("vigiepp.permissions") || '["*"]'), "users.manage")) return;
    await loadCatalog();
    try {
      const data = await api("/api/auth/users");
      renderUsers(data.users || []);
      if (els.usersHint) els.usersHint.textContent = `${(data.users || []).filter((u) => u.active).length} cuentas activas`;
    } catch (err) {
      if (els.usersHint) els.usersHint.textContent = err.message || "No se pudo cargar usuarios";
    }
  }

  async function createUser() {
    const name = els.userNewName?.value?.trim();
    const pin = els.userNewPin?.value?.trim();
    const role = els.userNewRole?.value || "guard";
    if (!name || !pin) {
      if (els.usersHint) els.usersHint.textContent = "Nombre y PIN son obligatorios";
      return;
    }
    const extra = [...(els.userNewExtra?.querySelectorAll('input[name="extra"]:checked') || [])].map((i) => i.value);
    try {
      await api("/api/auth/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, pin, role, extra_permissions: extra }),
      });
      if (els.userNewName) els.userNewName.value = "";
      if (els.userNewPin) els.userNewPin.value = "";
      if (els.usersHint) els.usersHint.textContent = "Guardia creado";
      await refreshUsers();
    } catch (err) {
      if (els.usersHint) els.usersHint.textContent = err.message || "Error al crear";
    }
  }

  async function saveEditor() {
    const userId = els.userEditPanel?.dataset.userId;
    if (!userId) return;
    const patch = {
      name: els.userEditName?.value?.trim(),
      role: els.userEditRole?.value,
      extra_permissions: [...(els.userEditExtra?.querySelectorAll('input[name="extra"]:checked') || [])].map((i) => i.value),
      revoked_permissions: [...(els.userEditRevoked?.querySelectorAll('input[name="revoked"]:checked') || [])].map((i) => i.value),
      site_ids: (els.userEditSites?.value || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };
    const pin = els.userEditPin?.value?.trim();
    if (pin) patch.pin = pin;
    try {
      await api(`/api/auth/users/${userId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      els.userEditPanel.classList.add("hidden");
      if (els.usersHint) els.usersHint.textContent = "Usuario actualizado";
      await refreshUsers();
    } catch (err) {
      if (els.usersHint) els.usersHint.textContent = err.message || "Error al guardar";
    }
  }

  async function toggleUser(userId, activate) {
    try {
      await api(`/api/auth/users/${userId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: activate }),
      });
      await refreshUsers();
    } catch (err) {
      if (els.usersHint) els.usersHint.textContent = err.message || "Error";
    }
  }

  function bindUsersAdminEvents() {
    els.btnUserCreate?.addEventListener("click", createUser);
    els.btnUserSave?.addEventListener("click", saveEditor);
    els.btnUserCancel?.addEventListener("click", () => els.userEditPanel?.classList.add("hidden"));
  }

  return { refreshUsers, bindUsersAdminEvents, loadCatalog };
}
