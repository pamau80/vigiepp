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
      els.identityMethod.textContent = "";
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
    const score = identity.score != null ? `${Math.round(Number(identity.score) * 100)}%` : null;
    const confMap = {
      high: "confianza alta",
      medium: "confianza media",
      low: "confianza baja",
      ambiguous: "ambigüedad",
      none: "",
    };
    const confTxt = confMap[identity.confidence] || "";
    if (known) {
      els.identityMethod.textContent = ["Rostro reconocido", score, confTxt].filter(Boolean).join(" · ");
    } else if (identity.faces_detected) {
      const why =
        identity.gallery_size === 0
          ? "Sin plantillas en servidor. Re-enrolá en Personas"
          : identity.reject_reason || "sin coincidencia";
      els.identityMethod.textContent = ["No identificado", score, why].filter(Boolean).join(" · ");
    } else {
      els.identityMethod.textContent = "Sin rostro detectado";
    }

    els.personChip.classList.remove("hidden");
    els.personChip.classList.toggle("unknown", !known);
    els.personChipName.textContent = els.identityName.textContent;
    els.personChipRut.textContent = els.identityRut.textContent;
  }

  return { displayPersonName, normalizePersonNameForSave, setIdentityCard };
}
