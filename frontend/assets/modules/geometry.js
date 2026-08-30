/** Cálculo de rectángulos cover/contain para video y canvas. */
export function videoCoverSize(srcW, srcH, dstW, dstH) {
  const scale = Math.max(dstW / srcW, dstH / srcH);
  const w = srcW * scale;
  const h = srcH * scale;
  return { w, h, ox: (dstW - w) / 2, oy: (dstH - h) / 2 };
}

export function videoContainSize(srcW, srcH, dstW, dstH) {
  const scale = Math.min(dstW / srcW, dstH / srcH);
  return { w: srcW * scale, h: srcH * scale };
}
