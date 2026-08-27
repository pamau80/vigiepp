export function createTeachController({ api, els, captureBlob, startCamera, hasMediaStream }) {
  async function refreshTeach() {
    try {
      const guide = await api("/api/teach/guide");
      const classes = guide.classes || [];
      els.teachClass.innerHTML = classes
        .map((c) => `<option value="${c.id}">${c.name} (${c.count})</option>`)
        .join("");
      els.teachStats.textContent = `${guide.stats?.total_samples || 0} ejemplos · ${guide.stats?.class_count || classes.length} clases`;
      const sel = classes.find((c) => c.id === els.teachClass.value);
      if (sel) els.teachHint.textContent = sel.hint;
      if (els.teachClassList) {
        const top = [...classes].sort((a, b) => (b.count || 0) - (a.count || 0)).slice(0, 12);
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
      els.teachHint.textContent = "Elegí o creá una clase primero";
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
      els.teachHint.textContent = "Elegí o creá una clase primero";
      return;
    }
    els.teachHint.textContent = "Procesando video (extrayendo frames)…";
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
      els.teachHint.textContent = "Escribí el nombre de la prenda nueva";
      return;
    }
    const fd = new FormData();
    fd.append("name", name);
    fd.append("hint", "Prenda personalizada — subí fotos y videos variados");
    try {
      const data = await api("/api/teach/class", { method: "POST", body: fd });
      els.teachNewClass.value = "";
      await refreshTeach();
      if (data.class?.id) els.teachClass.value = data.class.id;
      els.teachHint.textContent = `Clase creada: ${data.class?.name || name}. Ahora cargá fotos/video.`;
    } catch (err) {
      els.teachHint.textContent = err.message;
    }
  }

  function bindTeachEvents() {
    els.btnTeachSample.addEventListener("click", saveTeachSample);
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
      els.teachHint.textContent = "Entrenando modelo (puede tardar)…";
      try {
        const data = await api("/api/teach/train", { method: "POST" }, 60000);
        els.teachHint.textContent = data.message;
      } catch (err) {
        els.teachHint.textContent = err.message;
      }
    });
    els.btnTeachActivate.addEventListener("click", async () => {
      const data = await api("/api/teach/activate", { method: "POST" });
      els.modelStatusText.textContent = `IA lista · ${data.model}`;
      els.teachHint.textContent = "Modelo personalizado activado";
    });
  }

  return {
    refreshTeach,
    saveTeachSample,
    uploadTeachPhotos,
    uploadTeachVideo,
    createTeachClass,
    bindTeachEvents,
  };
}
