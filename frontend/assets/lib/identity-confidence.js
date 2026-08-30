/** Etiquetas y formato de confianza de identidad (panel + kiosk). */

export const CONF_LABELS = {
  high: "confianza alta",
  medium: "confianza media",
  low: "confianza baja",
  ambiguous: "ID dudosa",
  none: "",
};

export const CONF_SHORT = {
  high: "ID alta",
  medium: "ID media",
  low: "ID baja",
  ambiguous: "ID dudosa",
  none: "",
};

export function identityScorePct(identity) {
  if (identity?.score == null || Number.isNaN(Number(identity.score))) return null;
  return `${Math.round(Number(identity.score) * 100)}%`;
}

export function identityConfidenceLabel(identity, short = false) {
  const map = short ? CONF_SHORT : CONF_LABELS;
  return map[identity?.confidence] || "";
}

/** Línea corta de exactitud para kiosk / panel. */
export function formatIdentityAccuracy(identity, { short = false } = {}) {
  if (!identity?.faces_detected) return "";
  const score = identityScorePct(identity);
  const conf = identityConfidenceLabel(identity, short);
  if (identity.known) {
    return [conf, score].filter(Boolean).join(" · ");
  }
  if (identity.gallery_size === 0) return "Sin plantillas en servidor";
  if (identity.confidence === "ambiguous") return "ID dudosa — revisar identidad";
  return identity.reject_reason || "No registrado";
}

export function buildKioskDetail(payload) {
  const c = payload?.compliance || {};
  const ok = !!c.overall_compliant;
  const hasPeople = (c.persons || []).length > 0 || (payload?.detections || []).length > 0;
  const id = payload?.identity;
  if (!hasPeople) return "";

  const parts = [];
  if (id?.known && id?.name) {
    if (id.rut && !String(id.rut).startsWith("SIN-RUT")) parts.push(String(id.rut));
    const acc = formatIdentityAccuracy(id, { short: true });
    if (acc) parts.push(acc);
  } else if (id?.faces_detected) {
    parts.push(formatIdentityAccuracy(id, { short: true }));
  }

  if (!ok) {
    const miss = (c.persons?.[0]?.missing || []).slice(0, 3).join(", ");
    if (miss) parts.push(`Falta: ${miss}`);
    else if (!parts.length) parts.push(c.summary || "Revisá EPP");
  } else if (!parts.length) {
    parts.push("EPP OK");
  }

  return parts.join(" · ");
}
