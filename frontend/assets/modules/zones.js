import { $ } from "./dom.js";
import { videoCoverSize } from "./geometry.js";

const ZONES_CANVAS_HANDLE = 10;

/** Editor y overlay de zonas de seguridad. */
export function createZonesController({ api, els, settings, getAppMode }) {
  let zonesCache = [];
  let selectedZoneIndex = -1;
  let zonesCanvasRaf = 0;
  let zonesCanvasDrag = null;

function drawZonesOverlay(ctx, frameW, frameH, cover, hits) {
  if (!settings.showZones || !zonesCache.length) return;
  const sx = cover.w / frameW;
  const sy = cover.h / frameH;
  for (const z of zonesCache) {
    if (!z.enabled) continue;
    const rx = cover.ox + z.x * frameW * sx;
    const ry = cover.oy + z.y * frameH * sy;
    const rw = z.w * frameW * sx;
    const rh = z.h * frameH * sy;
    const hit = (hits || []).some((h) => h.zone_id === z.id);
    ctx.fillStyle = hit ? "rgba(214,40,40,0.18)" : "rgba(232,93,4,0.08)";
    ctx.strokeStyle = hit ? "rgba(214,40,40,0.85)" : (z.color || "rgba(232,93,4,0.7)");
    ctx.lineWidth = hit ? 2 : 1.25;
    ctx.setLineDash(z.type === "vehicle_lane" ? [6, 4] : []);
    ctx.fillRect(rx, ry, rw, rh);
    ctx.strokeRect(rx, ry, rw, rh);
    ctx.setLineDash([]);
    ctx.font = "600 11px Source Sans 3, sans-serif";
    ctx.fillStyle = "rgba(238,243,239,0.9)";
    const label =
      z.type === "vehicle_lane"
        ? `Vía · ${z.name}`
        : z.type === "machinery"
          ? `Máquina · ${z.name}`
          : `Zona · ${z.name}`;
    ctx.fillText(label, rx + 6, ry + 14);
  }
}

function syncZonesCanvasSize() {
  const canvas = els.zonesCanvas;
  if (!canvas) return;
  const frame = canvas.parentElement;
  if (!frame) return;
  const rect = frame.getBoundingClientRect();
  canvas.width = Math.max(1, Math.round(rect.width));
  canvas.height = Math.max(1, Math.round(rect.height));
}

function zoneCanvasRect(z, cw, ch) {
  return {
    x: (z.x || 0) * cw,
    y: (z.y || 0) * ch,
    w: (z.w || 0.2) * cw,
    h: (z.h || 0.2) * ch,
  };
}

function clampZoneNorm(z) {
  const min = 0.05;
  z.w = Math.max(min, Math.min(0.95, z.w || min));
  z.h = Math.max(min, Math.min(0.95, z.h || min));
  z.x = Math.max(0, Math.min(1 - z.w, z.x || 0));
  z.y = Math.max(0, Math.min(1 - z.h, z.y || 0));
}

function drawZonesEditorCanvas() {
  const canvas = els.zonesCanvas;
  if (!canvas) return;
  syncZonesCanvasSize();
  const ctx = canvas.getContext("2d");
  const cw = canvas.width;
  const ch = canvas.height;
  ctx.clearRect(0, 0, cw, ch);

  const video = els.liveVideo;
  if (video && video.videoWidth > 0 && !video.hidden) {
    const cover = videoCoverSize(video.videoWidth, video.videoHeight, cw, ch);
    ctx.drawImage(
      video,
      cover.ox,
      cover.oy,
      cover.w,
      cover.h
    );
  } else {
    ctx.fillStyle = "#0a0e0c";
    ctx.fillRect(0, 0, cw, ch);
    ctx.strokeStyle = "rgba(255,255,255,0.04)";
    ctx.lineWidth = 1;
    for (let x = 0; x <= cw; x += cw / 8) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, ch);
      ctx.stroke();
    }
    for (let y = 0; y <= ch; y += ch / 8) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(cw, y);
      ctx.stroke();
    }
    ctx.font = "500 11px Source Sans 3, sans-serif";
    ctx.fillStyle = "rgba(238,243,239,0.45)";
    ctx.textAlign = "center";
    ctx.fillText("Iniciá la cámara en Monitoreo para ver la vista previa", cw / 2, ch / 2);
    ctx.textAlign = "left";
  }

  const zones = zonesCache || [];
  for (let i = 0; i < zones.length; i++) {
    const z = zones[i];
    if (!z.enabled) continue;
    const { x, y, w, h } = zoneCanvasRect(z, cw, ch);
    const selected = i === selectedZoneIndex;
    ctx.fillStyle = selected ? "rgba(232,93,4,0.22)" : "rgba(232,93,4,0.1)";
    ctx.strokeStyle = selected ? "rgba(232,93,4,0.95)" : (z.color || "rgba(232,93,4,0.75)");
    ctx.lineWidth = selected ? 2 : 1.25;
    ctx.setLineDash(z.type === "vehicle_lane" ? [6, 4] : []);
    ctx.fillRect(x, y, w, h);
    ctx.strokeRect(x, y, w, h);
    ctx.setLineDash([]);
    ctx.font = "600 10px Source Sans 3, sans-serif";
    ctx.fillStyle = "rgba(238,243,239,0.92)";
    const label = z.name || `Zona ${i + 1}`;
    ctx.fillText(label, x + 5, y + 12);
    if (selected) {
      const hs = ZONES_CANVAS_HANDLE;
      ctx.fillStyle = "rgba(232,93,4,0.95)";
      for (const hx of [x, x + w]) {
        for (const hy of [y, y + h]) {
          ctx.fillRect(hx - hs / 2, hy - hs / 2, hs, hs);
        }
      }
    }
  }

  if (els.zonesPreviewHint) {
    const hasVideo = video && video.videoWidth > 0 && !video.hidden;
    els.zonesPreviewHint.textContent = hasVideo
      ? "Tocá una zona · arrastrá para mover · esquinas para tamaño"
      : "Sin cámara: ajustá con el lienzo o los deslizadores abajo";
  }
}

function zonesCanvasPoint(ev) {
  const canvas = els.zonesCanvas;
  const rect = canvas.getBoundingClientRect();
  const clientX = ev.touches?.[0]?.clientX ?? ev.clientX;
  const clientY = ev.touches?.[0]?.clientY ?? ev.clientY;
  const px = ((clientX - rect.left) / rect.width) * canvas.width;
  const py = ((clientY - rect.top) / rect.height) * canvas.height;
  return { px, py, nx: px / canvas.width, ny: py / canvas.height };
}

function zonesCanvasHit(px, py) {
  const canvas = els.zonesCanvas;
  const cw = canvas.width;
  const ch = canvas.height;
  const hs = ZONES_CANVAS_HANDLE;
  for (let i = zonesCache.length - 1; i >= 0; i--) {
    const z = zonesCache[i];
    if (!z.enabled) continue;
    const r = zoneCanvasRect(z, cw, ch);
    if (i === selectedZoneIndex) {
      const corners = [
        { edge: "nw", cx: r.x, cy: r.y },
        { edge: "ne", cx: r.x + r.w, cy: r.y },
        { edge: "sw", cx: r.x, cy: r.y + r.h },
        { edge: "se", cx: r.x + r.w, cy: r.y + r.h },
      ];
      for (const c of corners) {
        if (Math.abs(px - c.cx) <= hs && Math.abs(py - c.cy) <= hs) {
          return { index: i, mode: "resize", edge: c.edge };
        }
      }
    }
    if (px >= r.x && px <= r.x + r.w && py >= r.y && py <= r.y + r.h) {
      return { index: i, mode: "move" };
    }
  }
  return null;
}

function syncZoneSlidersFromCache(index) {
  const row = els.zonesList?.querySelector(`[data-zi="${index}"]`);
  if (!row) return;
  const z = zonesCache[index];
  if (!z) return;
  const set = (attr, val) => {
    const el = row.querySelector(`[data-z="${attr}"]`);
    if (el) el.value = String(Math.round(val * 100));
  };
  set("x", z.x || 0);
  set("y", z.y || 0);
  set("w", z.w || 0.2);
  set("h", z.h || 0.2);
}

function startZonesCanvasLoop() {
  stopZonesCanvasLoop();
  const tick = () => {
    if (getAppMode() !== "config" || document.querySelector("[data-cfg-section='zones']:not(.hidden)") == null) {
      zonesCanvasRaf = 0;
      return;
    }
    drawZonesEditorCanvas();
    zonesCanvasRaf = requestAnimationFrame(tick);
  };
  zonesCanvasRaf = requestAnimationFrame(tick);
}

function stopZonesCanvasLoop() {
  if (zonesCanvasRaf) {
    cancelAnimationFrame(zonesCanvasRaf);
    zonesCanvasRaf = 0;
  }
}

function bindZonesCanvasEvents() {
  const canvas = els.zonesCanvas;
  if (!canvas || canvas.dataset.bound) return;
  canvas.dataset.bound = "1";

  const onDown = (ev) => {
    if (ev.button !== undefined && ev.button !== 0) return;
    ev.preventDefault();
    zonesCache = readZonesFromEditor();
    const { px, py } = zonesCanvasPoint(ev);
    const hit = zonesCanvasHit(px, py);
    if (!hit) {
      selectedZoneIndex = -1;
      drawZonesEditorCanvas();
      return;
    }
    selectedZoneIndex = hit.index;
    const z = zonesCache[hit.index];
    zonesCanvasDrag = {
      mode: hit.mode,
      edge: hit.edge,
      index: hit.index,
      startX: z.x,
      startY: z.y,
      startW: z.w,
      startH: z.h,
      originPx: px,
      originPy: py,
    };
    drawZonesEditorCanvas();
  };

  const onMove = (ev) => {
    if (!zonesCanvasDrag) return;
    ev.preventDefault();
    const { px, py } = zonesCanvasPoint(ev);
    const canvasEl = els.zonesCanvas;
    const cw = canvasEl.width;
    const ch = canvasEl.height;
    const dx = (px - zonesCanvasDrag.originPx) / cw;
    const dy = (py - zonesCanvasDrag.originPy) / ch;
    const z = zonesCache[zonesCanvasDrag.index];
    if (!z) return;

    if (zonesCanvasDrag.mode === "move") {
      z.x = zonesCanvasDrag.startX + dx;
      z.y = zonesCanvasDrag.startY + dy;
    } else {
      const edge = zonesCanvasDrag.edge;
      let x1 = zonesCanvasDrag.startX;
      let y1 = zonesCanvasDrag.startY;
      let x2 = zonesCanvasDrag.startX + zonesCanvasDrag.startW;
      let y2 = zonesCanvasDrag.startY + zonesCanvasDrag.startH;
      if (edge.includes("n")) y1 = zonesCanvasDrag.startY + dy;
      if (edge.includes("s")) y2 = zonesCanvasDrag.startY + zonesCanvasDrag.startH + dy;
      if (edge.includes("w")) x1 = zonesCanvasDrag.startX + dx;
      if (edge.includes("e")) x2 = zonesCanvasDrag.startX + zonesCanvasDrag.startW + dx;
      if (x2 - x1 < 0.05) {
        if (edge.includes("w")) x1 = x2 - 0.05;
        else x2 = x1 + 0.05;
      }
      if (y2 - y1 < 0.05) {
        if (edge.includes("n")) y1 = y2 - 0.05;
        else y2 = y1 + 0.05;
      }
      z.x = x1;
      z.y = y1;
      z.w = x2 - x1;
      z.h = y2 - y1;
    }
    clampZoneNorm(z);
    syncZoneSlidersFromCache(zonesCanvasDrag.index);
    drawZonesEditorCanvas();
  };

  const onUp = () => {
    zonesCanvasDrag = null;
  };

  canvas.addEventListener("mousedown", onDown);
  canvas.addEventListener("mousemove", onMove);
  window.addEventListener("mouseup", onUp);
  canvas.addEventListener("touchstart", onDown, { passive: false });
  canvas.addEventListener("touchmove", onMove, { passive: false });
  window.addEventListener("touchend", onUp);
}

async function loadZones() {
  try {
    const data = await api("/api/zones");
    zonesCache = data.zones || [];
    renderZonesEditor();
  } catch (err) {
    if (els.zonesHint) els.zonesHint.textContent = err.message;
  }
}

function renderZonesEditor() {
  if (!els.zonesList) return;
  els.zonesList.innerHTML = (zonesCache || [])
    .map(
      (z, i) => `<div class="zone-row" data-zi="${i}">
        <label class="check"><input type="checkbox" data-z="en" ${z.enabled ? "checked" : ""}/> On</label>
        <input data-z="name" value="${String(z.name || "").replace(/"/g, "&quot;")}" placeholder="Nombre"/>
        <select data-z="type">
          <option value="restricted" ${z.type === "restricted" || !z.type ? "selected" : ""}>Restringida</option>
          <option value="vehicle_lane" ${z.type === "vehicle_lane" ? "selected" : ""}>Vía vehículos</option>
          <option value="machinery" ${z.type === "machinery" ? "selected" : ""}>Maquinaria</option>
        </select>
        <span class="zone-sliders">
          x<input data-z="x" type="range" min="0" max="90" value="${Math.round((z.x || 0) * 100)}"/>
          y<input data-z="y" type="range" min="0" max="90" value="${Math.round((z.y || 0) * 100)}"/>
          w<input data-z="w" type="range" min="10" max="90" value="${Math.round((z.w || 0.2) * 100)}"/>
          h<input data-z="h" type="range" min="10" max="90" value="${Math.round((z.h || 0.2) * 100)}"/>
        </span>
        <button type="button" class="btn-mini danger" data-z-del="${i}">X</button>
      </div>`
    )
    .join("") || "<p class='muted'>Sin zonas</p>";
  bindZonesCanvasEvents();
  requestAnimationFrame(() => drawZonesEditorCanvas());
}

function readZonesFromEditor() {
  if (!els.zonesList) return zonesCache;
  return [...els.zonesList.querySelectorAll(".zone-row")].map((row, i) => {
    const prev = zonesCache[i] || {};
    return {
      id: prev.id || `zona-${Date.now()}-${i}`,
      name: row.querySelector('[data-z="name"]')?.value || "Zona",
      type: row.querySelector('[data-z="type"]')?.value || "restricted",
      enabled: !!row.querySelector('[data-z="en"]')?.checked,
      x: (Number(row.querySelector('[data-z="x"]')?.value) || 0) / 100,
      y: (Number(row.querySelector('[data-z="y"]')?.value) || 0) / 100,
      w: (Number(row.querySelector('[data-z="w"]')?.value) || 20) / 100,
      h: (Number(row.querySelector('[data-z="h"]')?.value) || 20) / 100,
      color: prev.color || "#e85d04",
    };
  });
}

  return {
    get zonesCache() { return zonesCache; },
    set zonesCache(v) { zonesCache = v; },
    get selectedZoneIndex() { return selectedZoneIndex; },
    set selectedZoneIndex(v) { selectedZoneIndex = v; },
    loadZones, renderZonesEditor, readZonesFromEditor, drawZonesOverlay,
    drawZonesEditorCanvas, bindZonesCanvasEvents, startZonesCanvasLoop, stopZonesCanvasLoop,
    syncZonesCanvasSize,
  };
}
