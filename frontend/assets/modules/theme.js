/** Skins / apariencia del software (variables CSS). */
export const SKINS = [
  {
    id: "faena",
    name: "Faena",
    desc: "Naranja industrial · oscuro (predeterminado)",
    themeColor: "#e85d04",
  },
  {
    id: "portuario",
    name: "Portuario",
    desc: "Azul mar · muelles y patios",
    themeColor: "#0ea5e9",
  },
  {
    id: "mineria",
    name: "Minería",
    desc: "Ámbar · faenas subterráneas",
    themeColor: "#f59e0b",
  },
  {
    id: "claro",
    name: "Claro",
    desc: "Fondo claro · salas bien iluminadas",
    themeColor: "#c2410c",
  },
  {
    id: "alto-contraste",
    name: "Alto contraste",
    desc: "Portería exterior · máxima legibilidad",
    themeColor: "#000000",
  },
];

export function applySkin(skinId) {
  const id = SKINS.some((s) => s.id === skinId) ? skinId : "faena";
  document.documentElement.dataset.skin = id;
  document.documentElement.style.colorScheme = id === "claro" ? "light" : "dark";
  const skin = SKINS.find((s) => s.id === id) || SKINS[0];
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", skin.themeColor);
  return id;
}

export function renderSkinPicker(container, currentId, onPick) {
  if (!container) return;
  container.innerHTML = SKINS.map(
    (s) => `<button type="button" class="skin-chip${s.id === currentId ? " active" : ""}" data-skin-id="${s.id}" aria-pressed="${s.id === currentId ? "true" : "false"}">
      <span class="skin-swatch" data-skin-preview="${s.id}" aria-hidden="true"></span>
      <span class="skin-chip-text"><strong>${s.name}</strong><small>${s.desc}</small></span>
    </button>`
  ).join("");
  container.querySelectorAll("[data-skin-id]").forEach((btn) => {
    btn.addEventListener("click", () => onPick(btn.getAttribute("data-skin-id")));
  });
}
