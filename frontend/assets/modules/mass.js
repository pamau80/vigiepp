import { $, escapeHtml } from "./dom.js";

/** Vigilancia masiva, watchlist y equipos NVR/DVR. */
export function createMassController({ api, els, requiredQueryValue, getAppMode, refreshCameras }) {
  let massLoopOn = false;
  let massTimer = null;
  let watchlistCache = [];
  let nvrDevicesCache = [];

  function fillMassProfiles() {
    const massSel = $("#massProfileSelect");
    const src = els.profileSelect;
    if (!massSel || !src) return;
    massSel.innerHTML = src.innerHTML;
    if (src.value) massSel.value = src.value;
  }

  function renderMassGridPlaceholder() {
    const grid = $("#massGrid");
    if (!grid || watchlistCache.length) return;
    grid.innerHTML = `<p class="muted mass-empty">Agregá canales en <b>Equipos</b> o importá un NVR Dahua/Hikvision.</p>`;
  }

  function renderMassGrid(cells) {
    const grid = $("#massGrid");
    if (!grid) return;
    if (!cells?.length) {
      renderMassGridPlaceholder();
      return;
    }
    grid.innerHTML = cells
      .map((c) => {
        const cls = !c.connected ? "offline" : c.compliant ? "ok" : c.ok ? "bad" : "offline";
        const status = !c.connected
          ? "Sin señal"
          : c.compliant
            ? "Cumple"
            : `Falta: ${(c.missing || []).join(", ") || "EPP"}`;
        const thumb = c.thumb ? `data:image/jpeg;base64,${c.thumb}` : "";
        return `<div class="mass-cell ${cls}" data-mass-id="${escapeHtml(c.id || "")}">
          ${thumb ? `<img src="${thumb}" alt="Vista ${escapeHtml(c.name || "canal")} — ${escapeHtml(status)}" />` : `<div class="mass-cell-meta" style="top:40%">Sin imagen</div>`}
          <div class="mass-cell-meta"><strong>${escapeHtml(c.name || "Canal")}</strong> · ${escapeHtml(status)}</div>
        </div>`;
      })
      .join("");
    const sum = $("#massSummaryText");
    if (sum) {
      const online = cells.filter((c) => c.connected).length;
      const alerts = cells.filter((c) => c.connected && !c.compliant).length;
      sum.textContent = `${cells.length} canales · ${online} en línea · ${alerts} alertas`;
    }
    const massAlerts = $("#massAlertList");
    if (massAlerts) {
      const items = [];
      for (const c of cells) {
        if (!c.connected) continue;
        for (const a of c.alerts || []) {
          items.push({ ch: c.name, text: a });
        }
        for (const tr of c.actions || []) {
          items.push({ ch: c.name, text: tr.message || tr.name });
        }
      }
      massAlerts.innerHTML = items.length
        ? items
            .slice(0, 12)
            .map((it) => `<li class="warn"><span>${escapeHtml(it.ch || "Canal")}</span><span>${escapeHtml(it.text)}</span></li>`)
            .join("")
        : `<li class="muted">Sin alertas de acciones en este barrido</li>`;
    }
  }

  async function refreshWatchlistUi() {
    try {
      const data = await api("/api/watchlist");
      watchlistCache = data.channels || [];
      const list = $("#watchlistList");
      if (list) {
        list.innerHTML = watchlistCache.length
          ? watchlistCache
              .map(
                (c) =>
                  `<li><span>${escapeHtml(c.name)}</span><span class="conf">${c.enabled ? "ON" : "off"} · ${escapeHtml((c.url || "").slice(0, 42))}…</span></li>`
              )
              .join("")
          : `<li class="muted">Sin canales</li>`;
      }
    } catch (err) {
      const list = $("#watchlistList");
      if (list) list.innerHTML = `<li class="muted">${escapeHtml(err.message)}</li>`;
    }
  }

  async function refreshNvrDevices() {
    try {
      const data = await api("/api/nvr/devices");
      nvrDevicesCache = data.devices || [];
      const list = $("#nvrDeviceList");
      if (!list) return;
      list.innerHTML = nvrDevicesCache.length
        ? nvrDevicesCache
            .map(
              (d) =>
                `<li><span>${escapeHtml(d.name)} (${escapeHtml(d.vendor)})</span><span class="conf">${d.channel_count || 0} ch · ${escapeHtml(d.host || "")}</span></li>`
            )
            .join("")
        : `<li class="muted">Sin NVR registrados</li>`;
    } catch (err) {
      const list = $("#nvrDeviceList");
      if (list) list.innerHTML = `<li class="muted">${escapeHtml(err.message)}</li>`;
    }
  }

  async function runMassScan() {
    const profile = $("#massProfileSelect")?.value || els.profileSelect?.value || "general";
    const q = new URLSearchParams({ profile, required: requiredQueryValue() });
    const data = await api(`/api/surveillance/mass/scan?${q}`, { method: "POST" });
    renderMassGrid(data.cells || []);
    return data;
  }

  function startMassLoop() {
    if (massLoopOn) return;
    massLoopOn = true;
    $("#btnMassStart")?.setAttribute("disabled", "true");
    $("#btnMassStop")?.removeAttribute("disabled");
    const tick = async () => {
      if (!massLoopOn) return;
      try {
        await runMassScan();
      } catch (err) {
        const hint = $("#massStatusHint");
        if (hint) hint.textContent = err.message || "Error en barrido";
      }
      if (massLoopOn) massTimer = setTimeout(tick, 4000);
    };
    tick();
  }

  function stopMassLoop() {
    massLoopOn = false;
    if (massTimer) {
      clearTimeout(massTimer);
      massTimer = null;
    }
    $("#btnMassStart")?.removeAttribute("disabled");
    $("#btnMassStop")?.setAttribute("disabled", "true");
  }

  function bindMassEvents() {
    $("#btnMassStart")?.addEventListener("click", () => startMassLoop());
    $("#btnMassStop")?.addEventListener("click", () => stopMassLoop());
    $("#btnMassRefresh")?.addEventListener("click", () => runMassScan().catch((e) => alert(e.message)));

    $("#btnNvrProbe")?.addEventListener("click", async () => {
      const hint = $("#nvrProbeHint");
      if (hint) hint.textContent = "Probando…";
      try {
        const body = {
          vendor: $("#nvrVendor")?.value || "dahua",
          host: $("#nvrHost")?.value?.trim(),
          username: $("#nvrUser")?.value || "",
          password: $("#nvrPass")?.value || "",
          port: Number($("#nvrPort")?.value) || 554,
          channel_count: Number($("#nvrChannelCount")?.value) || 8,
          subtype: Number($("#nvrSubtype")?.value) || 0,
        };
        const data = await api("/api/nvr/probe", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (hint) {
          hint.textContent = `${data.device_name || data.host} · ${data.channel_count} canales RTSP generados${data.probe_note ? ` · ${data.probe_note}` : ""}`;
        }
      } catch (err) {
        if (hint) hint.textContent = err.message;
      }
    });

    $("#btnNvrSave")?.addEventListener("click", async () => {
      const hint = $("#nvrProbeHint");
      try {
        const body = {
          vendor: $("#nvrVendor")?.value || "dahua",
          host: $("#nvrHost")?.value?.trim(),
          name: $("#nvrName")?.value?.trim(),
          username: $("#nvrUser")?.value || "",
          password: $("#nvrPass")?.value || "",
          port: Number($("#nvrPort")?.value) || 554,
          channel_count: Number($("#nvrChannelCount")?.value) || 8,
          subtype: Number($("#nvrSubtype")?.value) || 0,
        };
        await api("/api/nvr/devices", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        await refreshNvrDevices();
        if (hint) hint.textContent = "NVR guardado";
      } catch (err) {
        if (hint) hint.textContent = err.message;
      }
    });

    $("#btnNvrImportWatch")?.addEventListener("click", async () => {
      const hint = $("#nvrProbeHint");
      try {
        let deviceId = nvrDevicesCache[0]?.id;
        if (!deviceId) {
          const saved = await api("/api/nvr/devices", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              vendor: $("#nvrVendor")?.value || "dahua",
              host: $("#nvrHost")?.value?.trim(),
              name: $("#nvrName")?.value?.trim(),
              username: $("#nvrUser")?.value || "",
              password: $("#nvrPass")?.value || "",
              port: Number($("#nvrPort")?.value) || 554,
              channel_count: Number($("#nvrChannelCount")?.value) || 8,
              subtype: Number($("#nvrSubtype")?.value) || 0,
            }),
          });
          deviceId = saved.device?.id;
          await refreshNvrDevices();
        }
        if (!deviceId) throw new Error("Guardá el NVR primero");
        const res = await api(`/api/nvr/devices/${deviceId}/import-watchlist?replace=false`, { method: "POST" });
        await refreshWatchlistUi();
        if (hint) hint.textContent = `Importados ${res.imported} canales a Masivo`;
        if (getAppMode() === "mass") renderMassGridPlaceholder();
      } catch (err) {
        if (hint) hint.textContent = err.message;
      }
    });

    $("#btnDevicesSaveCam")?.addEventListener("click", async () => {
      const url = $("#devicesRtspUrl")?.value?.trim();
      const name = $("#devicesCameraName")?.value?.trim() || "Canal";
      if (!url) return alert("URL RTSP requerida");
      await api("/api/cameras", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, url }),
      });
      if (refreshCameras) await refreshCameras();
      alert("Canal guardado para Vivo (máx. 4)");
    });
  }

  return {
    get nvrDevicesCache() {
      return nvrDevicesCache;
    },
    get watchlistCache() {
      return watchlistCache;
    },
    fillMassProfiles,
    refreshWatchlistUi,
    refreshNvrDevices,
    runMassScan,
    startMassLoop,
    stopMassLoop,
    renderMassGridPlaceholder,
    bindMassEvents,
  };
}
