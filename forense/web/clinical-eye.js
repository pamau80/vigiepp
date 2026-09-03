/** Ojo clínico — evaluación del instante en el reproductor forense. */

function trackKindMap(frameRec) {
  const out = new Map();
  for (const tr of frameRec?.tracks || []) {
    if (tr.track_id != null) out.set(tr.track_id, tr.kind || "other");
  }
  return out;
}

function eventsNear(timeline, timeSec, tolerance = 1.5) {
  if (!timeline?.length) return [];
  return timeline.filter((ev) => Math.abs((ev.time_sec || 0) - timeSec) <= tolerance);
}

export function evaluateInstantAudit(frameRec, context = {}) {
  const {
    timeline = [],
    knowledgeMatches = [],
    videoCaption = null,
    timeSec = frameRec?.time_sec,
    minDistanceM = 2,
    maxMachineryKmh = 15,
    maxPersonKmh = 8,
    timeTolerance = 1.5,
  } = context;

  if (!frameRec) {
    return {
      level: "idle",
      statusLabel: "Sin datos",
      headline: "Esperando análisis del video…",
      glanceMetric: "",
      sections: [],
      eventsNear: [],
    };
  }

  const t = timeSec ?? frameRec.time_sec ?? 0;
  const counts = frameRec.counts || {};
  const persons = counts.persons || 0;
  const vehicles = counts.vehicles || 0;
  const prox = frameRec.proximity || [];
  const speeds = frameRec.speeds || [];
  const kindByTrack = trackKindMap(frameRec);
  const near = eventsNear(timeline, t, timeTolerance);

  let level = "ok";
  const issues = [];

  const proxAlert = prox.find((p) => p.alert);
  if (proxAlert) {
    level = "alert";
    issues.push(
      `Proximidad crítica ${proxAlert.distance_m} m (persona #${proxAlert.person_track} – máq. #${proxAlert.machinery_track})`,
    );
  } else if (prox.length) {
    const dist = prox[0].distance_m ?? 99;
    if (dist <= minDistanceM * 1.5) {
      level = "warn";
      issues.push(`Distancia persona–maquinaria: ${dist} m (umbral ${minDistanceM} m)`);
    }
  }

  const speedLines = [];
  for (const sp of speeds) {
    const tid = sp.track_id;
    const kmh = sp.speed_kmh ?? 0;
    const kind = kindByTrack.get(tid) || "other";
    speedLines.push({ tid, kmh, kind, line: `#${tid} ${kmh} km/h` });
    const limit = kind === "machinery" ? maxMachineryKmh : kind === "person" ? maxPersonKmh : null;
    if (limit != null && kmh > limit) {
      if (level !== "alert") level = "warn";
      issues.push(`Exceso velocidad #${tid}: ${kmh} km/h (límite ${limit})`);
    }
  }

  const knEvents = near.filter((e) => e.type === "knowledge_match" || e.type === "knowledge_conjecture");
  if (knEvents.length && level === "ok") level = "warn";

  let headline;
  if (issues.length) headline = issues[0];
  else if (persons || vehicles) headline = `Escena estable — ${persons} persona(s), ${vehicles} máquina(s)`;
  else headline = "Sin personas ni maquinaria detectadas en este instante";

  const glanceParts = [frameRec.time_label || ""];
  if (prox.length) glanceParts.push(`dist. ${prox[0].distance_m} m`);
  else if (persons || vehicles) glanceParts.push(`${persons}👤 · ${vehicles}🚛`);
  const glanceMetric = glanceParts.filter(Boolean).join(" · ");

  const detItems = (frameRec.detections || []).map((det) => ({
    label: det.label || det.kind || "objeto",
    value: `${Math.round((det.confidence || 0) * 100)}%`,
  }));

  const sections = [
    {
      title: "Detecciones",
      items: detItems.length ? detItems : [{ label: "—", value: "Sin detecciones" }],
    },
    {
      title: "Cinemática",
      items: speedLines.length
        ? speedLines.map((s) => ({ label: `#${s.tid}`, value: `${s.kmh} km/h (${s.kind})` }))
        : [{ label: "—", value: "Sin velocidad medible" }],
    },
    {
      title: "Proximidad persona–maquinaria",
      items: prox.length
        ? prox.slice(0, 4).map((p) => ({
            label: `#${p.person_track} ↔ #${p.machinery_track}`,
            value: `${p.distance_m} m`,
            severity: p.alert ? "alert" : null,
          }))
        : [{ label: "—", value: "Sin pares persona–máquina" }],
    },
  ];

  if (near.length) {
    sections.push({
      title: "Eventos en este instante",
      items: near.slice(0, 6).map((ev) => ({
        label: (ev.type || "evento").replace(/_/g, " "),
        value: ev.message || "—",
        severity: ev.severity,
      })),
    });
  }

  const knItems = [];
  for (const ev of knEvents.slice(0, 3)) {
    knItems.push({
      label: (ev.type || "").replace(/_/g, " "),
      value: ev.message || "—",
      severity: ev.type === "knowledge_conjecture" ? "warn" : "ok",
    });
  }
  for (const m of knowledgeMatches.slice(0, 2)) {
    knItems.push({
      label: m.conjecture ? "Conjetura" : "Coincidencia",
      value: `${m.title} (${m.confidence_pct}%)`,
      severity: m.conjecture ? "warn" : "ok",
    });
  }
  if (knItems.length) sections.push({ title: "Biblioteca de aprendizaje", items: knItems });

  if (videoCaption?.caption) {
    sections.unshift({
      title: "IA visual — este instante",
      items: [{ label: videoCaption.time_label || "video", value: videoCaption.caption }],
    });
  }

  const statusMap = { alert: "Riesgo alto", warn: "Atención", ok: "Estable", idle: "Sin datos" };
  return {
    level,
    statusLabel: statusMap[level] || "—",
    headline,
    glanceMetric,
    sections,
    eventsNear: near,
  };
}

export function nearestVideoCaption(videoAi, timeSec, tolerance = 2) {
  const captions = videoAi?.captions || [];
  if (!captions.length) return null;
  let best = captions[0];
  let bestDt = Math.abs((best.time_sec || 0) - timeSec);
  for (const cap of captions) {
    const dt = Math.abs((cap.time_sec || 0) - timeSec);
    if (dt < bestDt) {
      bestDt = dt;
      best = cap;
    }
  }
  return bestDt <= tolerance ? best : null;
}

export function clinicalProgressMessage(raw, progress = null) {
  const text = (raw || "").trim();
  if (!text) return "Preparando auditoría forense…";
  const low = text.toLowerCase();
  if (text === "En cola") return "En cola — preparando revisión forense del video";
  if (text === "Preparando fuentes de video") return "Preparando fuentes de video para auditoría";
  if (text.startsWith("Consultando biblioteca")) return "Contrastando escena con biblioteca de incidentes";
  if (text.startsWith("Analizando video con IA visual")) return "La IA revisa fotogramas clave del video";
  if (text.startsWith("Generando informes")) return "Redactando informe clínico del caso";
  if (text === "Completado") return "Auditoría completa — informe listo para revisión";
  if (text === "Error") return "La auditoría no pudo completarse";
  if (low.includes("calculando cinemática") || low.includes("mapa de calor")) {
    return "Cuantificando velocidades y zonas de tránsito";
  }
  if (low.includes("frame ") && text.includes("/")) {
    return text.replace(/frame /gi, "fotograma ").replace(/Cám\./g, "cámara");
  }
  if (progress != null && progress < 15) return `Iniciando lectura del video — ${text}`;
  return text;
}

export function renderClinicalAuditPanel(container, audit) {
  if (!container) return;
  container.innerHTML = "";
  for (const section of audit.sections || []) {
    const sec = document.createElement("div");
    sec.className = "clinical-section";
    const h = document.createElement("h4");
    h.textContent = section.title;
    sec.appendChild(h);
    const ul = document.createElement("ul");
    ul.className = "clinical-items";
    for (const item of section.items || []) {
      const li = document.createElement("li");
      if (item.severity) li.classList.add(`sev-${item.severity}`);
      li.innerHTML = `<span class="clinical-item-label">${item.label}</span><span class="clinical-item-value">${item.value}</span>`;
      ul.appendChild(li);
    }
    sec.appendChild(ul);
    container.appendChild(sec);
  }
  if (!audit.sections?.length) {
    container.textContent = "Sin datos de auditoría para este instante.";
  }
}
