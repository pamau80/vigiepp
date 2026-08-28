import { ppeProgress } from "../lib/teach-progress.js";

function stepState(guide, classes, selected) {
  const stats = guide.stats || {};
  const selCount = selected?.count || 0;
  const readyTrain = !!stats.ready_to_train;
  const customReady = !!stats.training?.custom_model_ready;
  return {
    pick: !!selected,
    photos: selCount >= 10,
    train: readyTrain || customReady,
    activate: customReady,
  };
}

export function createTeachController({ api, els, captureBlob, startCamera, hasMediaStream, onModelActivated }) {
  let lastGuide = null;

  function renderChecklist(classes, guide) {
    if (!els.teachChecklist) return;
    const items = ppeProgress(classes, guide);
    els.teachChecklist.innerHTML = items
      .map(
        (item) => `<li class="teach-check${item.done ? " is-done" : ""}">
        <span class="teach-check-label">${item.label}</span>
        <span class="teach-check-bar" aria-hidden="true"><span style="width:${item.pct}%"></span></span>
        <span class="teach-check-count">${item.count}/${item.min}</span>
      </li>`
      )
      .join("");
  }

  function renderSteps(classes, guide) {
    if (!els.teachSteps) return;
    const selected = classes.find((c) => c.id === els.teachClass?.value);
    const st = stepState(guide, classes, selected);
    els.teachSteps.querySelectorAll("[data-teach-step]").forEach((el) => {
      const key = el.getAttribute("data-teach-step");
      el.classList.toggle("is-active", !!st[key]);
      el.classList.toggle("is-done", key === "pick" && st.photos);
    });
  }

  function updateModelBadge(guide) {
    const badge = els.teachModelBadge;
    if (!badge) return;
    const training = guide?.stats?.training || {};
    const customActive = String(els.modelStatusText?.textContent || "").toLowerCase().includes("personalizado");
    if (customActive) {
      badge.textContent = "Modelo faena activo";
      badge.dataset.state = "custom";
    } else if (training.custom_model_ready) {
      badge.textContent = "Listo para activar";
      badge.dataset.state = "ready";
    } else {
      badge.textContent = "Modelo base";
      badge.dataset.state = "base";
    }
  }

  async function refreshTeach() {
    try {
      const guide = await api("/api/teach/guide");
      lastGuide = guide;
      const classes = guide.classes || [];
      const prev = els.teachClass.value;
      els.teachClass.innerHTML = classes
        .map((c) => `<option value="${c.id}">${c.name} (${c.count})</option>`)
        .join("");
      if (prev && classes.some((c) => c.id === prev)) els.teachClass.value = prev;
      els.teachStats.textContent = `${guide.stats?.total_samples || 0} fotos · ${guide.stats?.class_count || classes.length} clases`;
      renderChecklist(classes, guide);
      renderSteps(classes, guide);
      updateModelBadge(guide);
      if (!els.teachHint.textContent.trim()) {
        const sel = classes.find((c) => c.id === els.teachClass.value);
        if (sel?.hint) els.teachHint.textContent = sel.hint;
      }
      if (els.teachClassList) {
        const top = [...classes].sort((a, b) => (b.count || 0) - (a.count || 0));
        els.teachClassList.innerHTML = top.length
          ? top
              .map(
                (c) =>
                  `<li><span>${c.custom ? "★ " : ""}${c.name}</span><span class="conf">${c.count}</span></li>`
              )
              .join("")
          : `<li class="muted">Sin ejemplos aún</li>`;
      }
    } catch (_) {}
  }

  async function saveTeachSample() {
    if (!hasMediaStream()) await startCamera({ silentDetect: true });
    const blob = await captureBlob(0.8, 720);
    const fd = new FormData();
    fd.append("file", blob, "sample.jpg");
    fd.append("class_id", els.teachClass.value);
    const data = await api("/api/teach/sample", { method: "POST", body: fd });
    els.teachHint.textContent = data.message;
    await refreshTeach();
  }

  async function uploadTeachPhotos(fileList) {
    const files = [...(fileList || [])].slice(0, 80);
    if (!files.length) return;
    const classId = els.teachClass.value;
    if (!classId) {
      els.teachHint.textContent = "Elegí o creá un ítem primero";
      return;
    }
    els.teachHint.textContent = `Subiendo ${files.length} fotos…`;
    const fd = new FormData();
    fd.append("class_id", classId);
    for (const f of files) fd.append("files", f, f.name);
    try {
      const data = await api("/api/teach/samples", { method: "POST", body: fd }, 120000);
      els.teachHint.textContent = data.message;
      await refreshTeach();
    } catch (err) {
      els.teachHint.textContent = err.message;
    }
  }

  async function uploadTeachVideo(file) {
    if (!file) return;
    const classId = els.teachClass.value;
    if (!classId) {
      els.teachHint.textContent = "Elegí o creá un ítem primero";
      return;
    }
    els.teachHint.textContent = "Extrayendo frames del video…";
    const fd = new FormData();
    fd.append("file", file, file.name);
    fd.append("class_id", classId);
    fd.append("max_frames", "40");
    fd.append("stride", "12");
    try {
      const data = await api("/api/teach/video", { method: "POST", body: fd }, 300000);
      els.teachHint.textContent = data.message;
      await refreshTeach();
    } catch (err) {
      els.teachHint.textContent = err.message;
    }
  }

  async function createTeachClass() {
    const name = els.teachNewClass?.value?.trim();
    if (!name) {
      els.teachHint.textContent = "Escribí el nombre de la prenda";
      return;
    }
    const fd = new FormData();
    fd.append("name", name);
    fd.append("hint", "Subí fotos variadas de esta prenda en faena real");
    try {
      const data = await api("/api/teach/class", { method: "POST", body: fd });
      els.teachNewClass.value = "";
      await refreshTeach();
      if (data.class?.id) els.teachClass.value = data.class.id;
      els.teachHint.textContent = `Creado: ${data.class?.name || name}. Adjuntá fotos o video.`;
    } catch (err) {
      els.teachHint.textContent = err.message;
    }
  }

  function bindTeachEvents() {
    els.btnTeachSample.addEventListener("click", saveTeachSample);
    els.teachClass?.addEventListener("change", () => {
      const guide = lastGuide;
      const classes = guide?.classes || [];
      const sel = classes.find((c) => c.id === els.teachClass.value);
      if (sel) els.teachHint.textContent = sel.hint;
      renderSteps(classes, guide || { stats: {} });
    });
    if (els.teachPhotos) {
      els.teachPhotos.addEventListener("change", async (e) => {
        await uploadTeachPhotos(e.target.files);
        e.target.value = "";
      });
    }
    if (els.teachVideo) {
      els.teachVideo.addEventListener("change", async (e) => {
        await uploadTeachVideo(e.target.files?.[0]);
        e.target.value = "";
      });
    }
    if (els.btnTeachAddClass) els.btnTeachAddClass.addEventListener("click", createTeachClass);
    els.btnTeachTrain.addEventListener("click", async () => {
      els.teachHint.textContent = "Entrenando… puede tardar unos minutos";
      try {
        const data = await api("/api/teach/train", { method: "POST" }, 60000);
        els.teachHint.textContent = data.message;
        await refreshTeach();
      } catch (err) {
        els.teachHint.textContent = err.message;
      }
    });
    els.btnTeachActivate.addEventListener("click", async () => {
      try {
        const data = await api("/api/teach/activate", { method: "POST" });
        els.modelStatusText.textContent = `Modelo faena · ${data.model}`;
        els.teachHint.textContent = "Modelo activo en monitoreo y portería";
        onModelActivated?.();
        await refreshTeach();
      } catch (err) {
        els.teachHint.textContent = err.message;
      }
    });
  }

  return {
    refreshTeach,
    saveTeachSample,
    uploadTeachPhotos,
    uploadTeachVideo,
    createTeachClass,
    bindTeachEvents,
    updateModelBadgeFromGuide: () => lastGuide && updateModelBadge(lastGuide),
  };
}
