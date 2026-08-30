/** Progreso de entrenamiento EPP — compartido entre teach, wizard y acciones. */
export const CORE_PPE = [
  { id: "casco", label: "Casco", min: 30, teachClass: "casco" },
  {
    id: "chaleco",
    label: "Ropa completa",
    min: 30,
    teachClass: "chaleco",
    aliases: ["chaleco_fluor", "polera", "casaca", "uniforme_completo", "ropa_reflectante"],
  },
  { id: "lentes", label: "Lentes", min: 30, teachClass: "lentes" },
  { id: "guantes", label: "Guantes", min: 30, teachClass: "guantes" },
];

/** Clases para reglas de Acciones (cámara en altura). */
export const CORE_ACTIONS = [
  { id: "montacargas", label: "Montacargas / grúa", min: 40, teachClass: "montacargas" },
  { id: "celular", label: "Celular en faena", min: 30, teachClass: "celular" },
  { id: "carga_suspendida", label: "Carga suspendida", min: 35, teachClass: "carga_suspendida" },
];

export function countForFamily(classes, family) {
  const ids = new Set([family.id, ...(family.aliases || [])]);
  for (const c of classes) {
    const cid = String(c.id || "").toLowerCase();
    if (cid.includes(family.id) || [...ids].some((x) => cid.includes(x))) ids.add(c.id);
  }
  let total = 0;
  for (const c of classes) {
    if (ids.has(c.id) || String(c.id || "").toLowerCase().includes(family.id)) {
      total += Number(c.count) || 0;
    }
  }
  return total;
}

export function ppeProgress(classes, guide) {
  const minRec = guide?.stats?.min_recommended || 30;
  return CORE_PPE.map((item) => {
    const n = countForFamily(classes, item);
    const min = item.min || minRec;
    return { ...item, count: n, min, done: n >= min, pct: Math.min(100, Math.round((n / min) * 100)) };
  });
}

export function actionTeachProgress(classes, guide) {
  const minRec = guide?.stats?.min_recommended || 30;
  return CORE_ACTIONS.map((item) => {
    const n = countForFamily(classes, item);
    const min = item.min || minRec;
    return { ...item, count: n, min, done: n >= min, pct: Math.min(100, Math.round((n / min) * 100)) };
  });
}

export function faenaReady(progress, guide, eppCustom) {
  const allPpe = progress.every((p) => p.done);
  const trained = !!guide?.stats?.training?.custom_model_ready || !!eppCustom;
  return allPpe && trained;
}
