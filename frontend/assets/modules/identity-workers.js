import { $, $$, escapeHtml } from "./dom.js";

/** Lista de personas enroladas, respaldo IDB y escaneos recientes. */
export function createWorkersController({
  api,
  els,
  displayPersonName,
  normalizePersonNameForSave,
  setIdentityCard,
  getLastIdentity,
  setLastIdentity,
  setLastFaceBox,
}) {
  let workersCache = [];
  let workerFilter = "active";
  const IDB_NAME = "vigiepp-persist";
  const IDB_STORE = "backups";
  const IDB_KEY = "identity-latest";
  let browserBackupTimer = null;

  function formatLastSeen(iso) {
    if (!iso) return "Nunca visto";
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return "Nunca visto";
      const diff = (Date.now() - d.getTime()) / 1000;
      if (diff < 90) return "Ahora";
      if (diff < 3600) return `Hace ${Math.round(diff / 60)} min`;
      if (diff < 86400) return `Hace ${Math.round(diff / 3600)} h`;
      return d.toLocaleString("es-CL", { dateStyle: "short", timeStyle: "short" });
    } catch (_) {
      return "Nunca visto";
    }
  }

  function qualityLabel(q, ready) {
    if (ready === false) return "NO LISTO";
    const n = Number(q) || 0;
    if (n >= 85) return "Alta";
    if (n >= 60) return "Media";
    if (n > 0) return "Baja";
    return "Sin fotos";
  }

  function idbOpen() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(IDB_NAME, 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(IDB_STORE)) db.createObjectStore(IDB_STORE);
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function saveBrowserBackupBlob(blob) {
    const db = await idbOpen();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(IDB_STORE, "readwrite");
      tx.objectStore(IDB_STORE).put({ blob, savedAt: Date.now(), bytes: blob.size }, IDB_KEY);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  }

  async function loadBrowserBackupBlob() {
    const db = await idbOpen();
    const row = await new Promise((resolve, reject) => {
      const tx = db.transaction(IDB_STORE, "readonly");
      const req = tx.objectStore(IDB_STORE).get(IDB_KEY);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error);
    });
    db.close();
    return row;
  }

  function scheduleBrowserBackup() {
    if (browserBackupTimer) clearTimeout(browserBackupTimer);
    browserBackupTimer = setTimeout(() => {
      syncBrowserBackupFromServer().catch(() => {});
    }, 1500);
  }

  async function syncBrowserBackupFromServer() {
    const res = await fetch("/api/identity/backup", { credentials: "same-origin" });
    if (!res.ok) return;
    const blob = await res.blob();
    if (!blob || blob.size < 80) return;
    await saveBrowserBackupBlob(blob);
  }

  async function restoreBrowserBackupIfServerEmpty() {
    const stored = await loadBrowserBackupBlob();
    if (!stored?.blob) return false;
    const fd = new FormData();
    fd.append("file", stored.blob, "identity-browser-backup.zip");
    fd.append("mode", "replace");
    await api("/api/identity/backup/restore", { method: "POST", body: fd }, 90000);
    return true;
  }

  async function refreshWorkers() {
    try {
      workersCache = await api("/api/identity/workers");
      if (!workersCache.length) {
        const restored = await restoreBrowserBackupIfServerEmpty();
        if (restored) {
          workersCache = await api("/api/identity/workers");
          if (els.enrollCoach) {
            els.enrollCoach.textContent =
              "Se restauró el respaldo de este navegador (Render Free borra el disco al dormir).";
          }
        }
      } else {
        scheduleBrowserBackup();
      }
      renderWorkerList();
    } catch (err) {
      console.error(err);
      if (els.workerListHint) els.workerListHint.textContent = "No se pudo cargar la lista";
    }
  }

  function showPersistBanner(health) {
    const el = $("#persistBanner");
    if (!el) return;
    const cloud = health?.cloud_backup || {};
    if (cloud.configured || (health?.data_persistent && !health?.data_ephemeral_risk)) {
      el.classList.add("hidden");
      el.textContent = "";
      return;
    }
    el.classList.remove("hidden");
    el.innerHTML =
      "<strong>Falta volumen durable:</strong> Render Free no guarda disco. " +
      "Solución gratis: corré <code>activate-free-durable.ps1</code> (Hugging Face, sin pago). " +
      "Las personas quedan en un dataset privado y sobreviven al sleep.";
  }

  function renderWorkerList() {
    const q = (els.workerSearch?.value || "").trim().toLowerCase();
    let list = workersCache.filter((w) => {
      if (workerFilter === "active") return w.active !== false;
      if (workerFilter === "inactive") return w.active === false;
      return true;
    });
    if (q) {
      list = list.filter((w) => {
        const blob = `${w.name || ""} ${w.rut || ""} ${w.group || ""}`.toLowerCase();
        return blob.includes(q);
      });
    }
    const html = list.length
      ? list
          .map((w) => {
            const active = w.active !== false;
            const photo = w.photo_url
              ? `<img class="worker-photo" src="${w.photo_url}?t=${encodeURIComponent(w.last_seen || w.face_samples || 0)}" alt="Foto de ${escapeHtml(w.name || "trabajador")}" />`
              : `<div class="worker-photo placeholder" aria-hidden="true"></div>`;
            const qn = w.quality || 0;
            const ready =
              w.ready === true ||
              ((w.face_samples || 0) >= (w.min_samples_ready || 4) &&
                (w.embedding_count || w.face_samples || 0) >= 3);
            const qLabel = qualityLabel(qn, ready);
            const consentLabel = w.consent_ok
              ? `consentimiento ${formatLastSeen(w.consent_at)}`
              : "sin consentimiento";
            return `<li data-worker-id="${w.id}" class="${active ? "" : "is-inactive"}">
              ${photo}
              <div class="worker-meta">
                <strong>${escapeHtml(displayPersonName(w.name) || "Sin nombre")}${active ? "" : " · inactivo"}${ready ? "" : " · incompleto"}</strong>
                <span class="conf">${escapeHtml(w.rut || "—")}${w.group ? " · " + escapeHtml(w.group) : ""}</span>
                <span class="conf">${w.face_samples || 0}/4 muestras · calidad ${qn}% (${qLabel}) · ${formatLastSeen(w.last_seen)}</span>
                <span class="conf">${consentLabel}</span>
              </div>
              <div class="worker-actions">
                <button type="button" class="btn-mini" data-toggle-active="${w.id}">${active ? "Desactivar" : "Activar"}</button>
                <button type="button" class="btn-mini" data-edit="${w.id}">Editar</button>
                <button type="button" class="btn-mini" data-reset="${w.id}">Rehacer</button>
                <button type="button" class="btn-mini danger" data-del="${w.id}">Eliminar</button>
              </div>
            </li>`;
          })
          .join("")
      : `<li class="muted">${workersCache.length ? "Sin coincidencias" : "Nadie enrolado"}</li>`;
    if (els.workerList) els.workerList.innerHTML = html;
    const actives = workersCache.filter((w) => w.active !== false).length;
    if (els.workerListHint) {
      els.workerListHint.textContent = workersCache.length
        ? `${actives} activas / ${workersCache.length} total · Inactivo = no se identifica`
        : "";
    }
  }

  async function deleteWorker(id) {
    const w = workersCache.find((x) => x.id === id);
    const label = w ? `${w.name} (${w.rut || "sin RUT"})` : id;
    if (!confirm(`¿Eliminar a ${label}?\n\nSe borran ficha, fotos y reconocimiento. No se puede deshacer.`)) {
      return;
    }
    if (els.workerListHint) els.workerListHint.textContent = "Eliminando…";
    try {
      await api(`/api/identity/workers/${id}`, { method: "DELETE" });
      const lastIdentity = getLastIdentity();
      if (lastIdentity?.name && w && lastIdentity.name === w.name) {
        setIdentityCard(null);
        setLastIdentity(null);
        setLastFaceBox(null);
      }
      if (els.enrollCoach) els.enrollCoach.textContent = `Eliminado: ${w?.name || id}`;
      await refreshWorkers();
    } catch (err) {
      if (els.workerListHint) els.workerListHint.textContent = err.message || "No se pudo eliminar";
      if (els.enrollCoach) els.enrollCoach.textContent = err.message || "Error al eliminar";
      alert(err.message || "No se pudo eliminar");
    }
  }

  async function toggleWorkerActive(id) {
    const w = workersCache.find((x) => x.id === id);
    if (!w) return;
    const next = !(w.active !== false);
    try {
      await api(`/api/identity/workers/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: next }),
      });
      if (els.enrollCoach) {
        els.enrollCoach.textContent = next ? `Activado: ${w.name}` : `Desactivado: ${w.name} (no se identificará)`;
      }
      await refreshWorkers();
    } catch (err) {
      alert(err.message || "No se pudo cambiar estado");
    }
  }

  async function editWorker(id) {
    const w = workersCache.find((x) => x.id === id);
    if (!w) return;
    const name = prompt("Nombre (usá «Especialista …» en vez de Dr./Dra.)", displayPersonName(w.name || ""));
    if (name === null) return;
    const rutDefault = w.rut?.startsWith("SIN-RUT") ? "" : w.rut || "";
    const rut = prompt("RUT", rutDefault);
    if (rut === null) return;
    const group = prompt("Grupo / contratista / cuadrilla", w.group || "");
    if (group === null) return;
    try {
      const data = await api(`/api/identity/workers/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: normalizePersonNameForSave(name.trim()),
          rut: rut.trim(),
          group: group.trim(),
        }),
      });
      if (els.enrollCoach) {
        els.enrollCoach.textContent = `Actualizado: ${displayPersonName(data.worker?.name || name)}`;
      }
      if (data.worker) {
        els.workerName.value = displayPersonName(data.worker.name || "");
        els.workerRut.value = data.worker.rut?.startsWith("SIN-RUT") ? "" : data.worker.rut || "";
      }
      await refreshWorkers();
    } catch (err) {
      alert(err.message || "No se pudo editar");
    }
  }

  async function resetWorkerFaces(id) {
    const w = workersCache.find((x) => x.id === id);
    const label = w?.name || id;
    if (!confirm(`¿Borrar solo las fotos de ${label} y volver a enrolar?\n\nSe mantiene nombre, RUT y grupo.`)) return;
    try {
      const data = await api(`/api/identity/workers/${id}/reset-faces`, { method: "POST" });
      await refreshWorkers();
      if (data.worker) {
        els.workerName.value = data.worker.name || "";
        els.workerRut.value = data.worker.rut?.startsWith("SIN-RUT") ? "" : data.worker.rut || "";
      }
      if (els.enrollCoach) els.enrollCoach.textContent = "Rostros borrados. Enrolá 4 poses o adjuntá fotos.";
    } catch (err) {
      alert(err.message || "No se pudo rehacer");
    }
  }

  async function refreshScans() {
    try {
      const scans = await api("/api/scans/recent?limit=8");
      els.scanList.innerHTML = scans.length
        ? scans
            .map((s) => {
              const who = s.worker_name || "Sin nombre";
              const st = s.compliant ? "OK" : "Falta EPP";
              const ev = s.evidence_id
                ? ` <a class="evidence-link" href="/api/evidence/${encodeURIComponent(s.evidence_id)}" target="_blank" rel="noopener">foto</a>`
                : "";
              return `<li><span>${who}${ev}</span><span class="conf">${st}</span></li>`;
            })
            .join("")
        : `<li class="muted">Aún no hay escaneos con identidad</li>`;
    } catch (_) {}
  }

  function hasReadyWorkers() {
    return (workersCache || []).some(
      (w) =>
        w.active !== false &&
        (w.ready === true || (w.face_samples || 0) >= (w.min_samples_ready || 4))
    );
  }

  function bindWorkerEvents() {
    const onWorkerListClick = (e) => {
      const del = e.target.closest("[data-del]");
      const reset = e.target.closest("[data-reset]");
      const edit = e.target.closest("[data-edit]");
      const tog = e.target.closest("[data-toggle-active]");
      if (del) deleteWorker(del.getAttribute("data-del"));
      if (reset) resetWorkerFaces(reset.getAttribute("data-reset"));
      if (edit) editWorker(edit.getAttribute("data-edit"));
      if (tog) toggleWorkerActive(tog.getAttribute("data-toggle-active"));
    };
    if (els.workerList) els.workerList.addEventListener("click", onWorkerListClick);
    if (els.workerSearch) {
      els.workerSearch.addEventListener("input", () => renderWorkerList());
    }
    $$("[data-worker-filter]").forEach((b) => {
      b.addEventListener("click", () => {
        workerFilter = b.dataset.workerFilter || "active";
        $$("[data-worker-filter]").forEach((x) => x.classList.toggle("active", x === b));
        renderWorkerList();
      });
    });
  }

  return {
    get workersCache() {
      return workersCache;
    },
    hasReadyWorkers,
    refreshWorkers,
    renderWorkerList,
    refreshScans,
    showPersistBanner,
    deleteWorker,
    toggleWorkerActive,
    editWorker,
    resetWorkerFaces,
    bindWorkerEvents,
  };
}
