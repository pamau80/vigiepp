/** Textos Forense — español de Chile (es-CL). */

export const STATUS = {
  queued: "en cola",
  processing: "procesando",
  done: "completado",
  error: "error",
};

export const KIND = {
  person: "persona",
  machinery: "maquinaria",
  other: "otro",
};

export const EVENT_TYPE = {
  action: "acción",
  epp_non_compliant: "incumplimiento EPP",
  zone: "zona restringida",
  speed_violation: "exceso de velocidad",
  proximity: "proximidad crítica",
  knowledge_match: "coincidencia biblioteca",
  knowledge_conjecture: "conjetura biblioteca",
  collision: "colisión",
  fall_risk: "riesgo de caída",
  unsafe_act: "acto inseguro",
};

export const SOURCE = {
  user: "usuario",
  live: "video en vivo",
  seed: "plantilla",
  osha: "OSHA",
};

export function statusLabel(code) {
  return STATUS[code] || code || "—";
}

export function kindLabel(code) {
  return KIND[code] || code || "—";
}

export function eventTypeLabel(code) {
  return EVENT_TYPE[code] || (code || "—").replace(/_/g, " ");
}

export function sourceLabel(code) {
  return SOURCE[code] || code || "";
}
