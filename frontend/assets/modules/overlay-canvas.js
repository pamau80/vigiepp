import { videoCoverSize } from "./geometry.js";

/** Canvas overlay: cajas EPP, rostros, anonimización y zonas. */
export function createOverlayCanvasController({
  els,
  settings,
  enrollState,
  getAppMode,
  getLastFaceBox,
  syncCanvasSize,
  evaluateAlignment,
  drawZonesOverlay,
}) {
  function drawFaceBox(ctx, faceBox, frameW, frameH, cover) {
    if (!faceBox || faceBox.length < 4) return;
    const [x1, y1, x2, y2] = faceBox;
    const sx = cover.w / frameW;
    const sy = cover.h / frameH;
    const cx = cover.ox + ((x1 + x2) / 2) * sx;
    const cy = cover.oy + ((y1 + y2) / 2) * sy;
    const rx = Math.max(12, ((x2 - x1) * sx) / 2);
    const ry = Math.max(16, ((y2 - y1) * sy) / 2);
    ctx.save();
    ctx.strokeStyle = "rgba(238, 243, 239, 0.45)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx * 1.05, ry * 1.15, 0, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }

  function blurFaceOnCanvas(ctx, faceBox, frameW, frameH, cover) {
    if (!faceBox || !settings.anonymizeFaces) return;
    const [x1, y1, x2, y2] = faceBox;
    const sx = cover.w / frameW;
    const sy = cover.h / frameH;
    const rx = cover.ox + x1 * sx;
    const ry = cover.oy + y1 * sy;
    const rw = Math.max(8, (x2 - x1) * sx);
    const rh = Math.max(8, (y2 - y1) * sy);
    ctx.fillStyle = "rgba(12, 16, 14, 0.72)";
    ctx.fillRect(rx, ry, rw, rh);
    ctx.strokeStyle = "rgba(255,255,255,0.18)";
    ctx.strokeRect(rx + 0.5, ry + 0.5, rw, rh);
    ctx.font = "600 10px Source Sans 3, sans-serif";
    ctx.fillStyle = "rgba(238,243,239,0.75)";
    ctx.fillText("Privado", rx + 6, ry + Math.min(14, rh - 4));
  }

  function drawDetections(detections, frameW, frameH, identity, zoneHits) {
    syncCanvasSize();
    const canvas = els.overlayCanvas;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const cover = videoCoverSize(frameW, frameH, canvas.width, canvas.height);
    const sx = cover.w / frameW;
    const sy = cover.h / frameH;

    evaluateAlignment(detections, frameW, frameH);
    drawZonesOverlay(ctx, frameW, frameH, cover, zoneHits || []);

    const drawBoxes = settings.showPpeBoxes && getAppMode() === "live";
    if (drawBoxes) {
      const badOnly = (detections || [])
        .filter((d) => {
          const l = String(d.label_es || d.label).toLowerCase();
          return l.startsWith("sin") || l.startsWith("no") || l.includes("fall");
        })
        .sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
        .slice(0, 1);

      for (const d of badOnly) {
        const [x1, y1, x2, y2] = d.box;
        const rx = cover.ox + x1 * sx;
        const ry = cover.oy + y1 * sy;
        const rw = (x2 - x1) * sx;
        const rh = (y2 - y1) * sy;
        ctx.strokeStyle = "rgba(214, 90, 70, 0.45)";
        ctx.lineWidth = 1.25;
        ctx.strokeRect(rx + 0.5, ry + 0.5, rw, rh);
        let label = String(d.label_es || d.label).replace(/\s+/g, " ").trim();
        if (label.length > 18) label = `${label.slice(0, 16)}…`;
        ctx.font = "600 11px Source Sans 3, sans-serif";
        const tw = ctx.measureText(label).width + 10;
        ctx.fillStyle = "rgba(10, 14, 12, 0.65)";
        ctx.fillRect(rx, Math.max(0, ry - 16), tw, 16);
        ctx.fillStyle = "rgba(240, 210, 200, 0.9)";
        ctx.fillText(label, rx + 5, Math.max(11, ry - 4));
      }
    }

    const faceBox = identity?.face_box || getLastFaceBox();
    if (
      faceBox &&
      settings.anonymizeFaces &&
      getAppMode() === "live" &&
      !(identity && identity.known)
    ) {
      blurFaceOnCanvas(ctx, faceBox, frameW, frameH, cover);
    }
    if (faceBox && (enrollState.enrolling || getAppMode() === "identity")) {
      drawFaceBox(ctx, faceBox, frameW, frameH, cover);
    }
  }

  return { drawDetections };
}
