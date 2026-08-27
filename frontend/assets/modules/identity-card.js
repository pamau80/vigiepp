import {
  CONF_LABELS,
  formatIdentityAccuracy,
  identityScorePct,
} from "../lib/identity-confidence.js";

/** Nombre visible y tarjeta de identidad en el panel. */
export function createIdentityCardController({ els }) {
  function displayPersonName(name) {
    let n = String(name || "").trim();
    if (!n) return n;
    n = n.replace(/^(dra\.?|dr\.?|doctora|doctor)\b\.?\s*/i, "Especialista ");
    n = n.replace(/\s{2,}/g, " ").trim();
    return n;
  }

  function normalizePersonNameForSave(name) {
    return displayPersonName(name);
  }

  function setIdentityCard(identity) {
    if (!identity) {
      els.identityName.textContent = "Sin identificar";
      els.identityRut.textContent = "Enrola personas en Enrolar personas";
      if (els.identityMethod) {
        els.identityMethod.textContent = "";
        els.identityMethod.className = "card-meta";
      }
      els.personChip.classList.add("hidden");
      return;
    }
    const known = !!identity.known;
    const displayName = displayPersonName(identity.name);
    els.identityName.textContent = displayName || (known ? "—" : "Desconocido");
    els.identityRut.textContent =
      identity.rut && !String(identity.rut).startsWith("SIN-RUT")
        ? `RUT ${identity.rut}`
        : known
          ? "Sin RUT"
          : "No está en el registro";

    const score = identityScorePct(identity);
    const confTxt = CONF_LABELS[identity.confidence] || "";
    if (els.identityMethod) {
      els.identityMethod.className = `card-meta conf-${identity.confidence || "none"}`;
      if (known) {
        els.identityMethod.textContent = ["Reconocido", score, confTxt].filter(Boolean).join(" · ");
      } else if (identity.faces_detected) {
        els.identityMethod.textContent = formatIdentityAccuracy(identity);
      } else {
        els.identityMethod.textContent = "Sin rostro detectado";
      }
    }

    const showChip = document.body.classList.contains("is-mobile");
    if (showChip) {
      els.personChip.classList.remove("hidden");
      els.personChip.classList.toggle("unknown", !known);
      els.personChipName.textContent = els.identityName.textContent;
      els.personChipRut.textContent = els.identityRut.textContent;
    } else {
      els.personChip.classList.add("hidden");
    }
  }

  return { displayPersonName, normalizePersonNameForSave, setIdentityCard };
}
