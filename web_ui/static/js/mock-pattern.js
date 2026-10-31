/* ==========================================================================
   MOCK PATTERN  (frontend placeholder only)
   --------------------------------------------------------------------------
   The real SVG comes from the backend (pattern_generator.py). This file only
   draws a *rough stand-in* in the same visual language so the Results screen
   can be built and tested before the backend is connected.

   It is NOT drafting logic. Delete it (and the script tag in index.html)
   once the real API is wired in.

   Visual language used (matches the project doc):
     black solid  = stitching line     red dashed = cutting line
     red dashed arrow = grainline      blue arrows = dimensions
   ========================================================================== */
(function () {
  'use strict';

  const SEAM = 1.5; // cm, matches the reference output "Seam allowance: 1.5cm"

  /* ---------- tiny geometry helpers (all in cm) ---------- */
  function sampleQuad(p0, c, p1, n = 14) {
    const out = [];
    for (let i = 1; i <= n; i++) {
      const t = i / n, u = 1 - t;
      out.push([u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0], u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1]]);
    }
    return out;
  }

  /** points: [{x,y,c?:[cx,cy]}]  c means "edge INTO this point is a quad curve" */
  function toPolyline(points) {
    const poly = [[points[0].x, points[0].y]];
    for (let i = 1; i < points.length; i++) {
      const p = points[i], prev = points[i - 1];
      if (p.c) poly.push(...sampleQuad([prev.x, prev.y], p.c, [p.x, p.y]));
      else poly.push([p.x, p.y]);
    }
    return poly;
  }

  function offsetPolygon(poly, d) {
    let area = 0;
    for (let i = 0; i < poly.length; i++) {
      const [x1, y1] = poly[i], [x2, y2] = poly[(i + 1) % poly.length];
      area += x1 * y2 - x2 * y1;
    }
    const sign = area > 0 ? 1 : -1; // outward normal direction depends on winding
    const norm = (a, b) => {
      const dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy) || 1;
      return [sign * dy / len, -sign * dx / len];
    };
    return poly.map((p, i) => {
      const prev = poly[(i - 1 + poly.length) % poly.length], next = poly[(i + 1) % poly.length];
      const n1 = norm(prev, p), n2 = norm(p, next);
      const k = 1 + (n1[0] * n2[0] + n1[1] * n2[1]);
      let mx = (n1[0] + n2[0]) / (k < 0.25 ? 0.25 : k), my = (n1[1] + n2[1]) / (k < 0.25 ? 0.25 : k);
      const m = Math.hypot(mx, my); if (m > 2) { mx *= 2 / m; my *= 2 / m; }
      return [p[0] + mx * d, p[1] + my * d];
    });
  }

  const fmt = (n) => (Math.round(n * 100) / 100).toString();
  const num = (n) => (Math.round(n * 10) / 10).toString().replace(/\.0$/, '');

  function pathFromPoints(points) {
    let d = `M${fmt(points[0].x)} ${fmt(points[0].y)}`;
    for (let i = 1; i < points.length; i++) {
      const p = points[i];
      d += p.c ? ` Q${fmt(p.c[0])} ${fmt(p.c[1])} ${fmt(p.x)} ${fmt(p.y)}` : ` L${fmt(p.x)} ${fmt(p.y)}`;
    }
    return d + ' Z';
  }

  /* ---------- piece outlines (very rough, for display only) ---------- */
  function bodicePoints(spec, m, isBack) {
    const neckline = spec.neckline;
    const loose = ['loose', 'oversized', 'boxy'].includes(spec.silhouette);
    const w = m.bust / 4 + 2;                                   // chest half-width
    const armholeDepth = m.bust / 10 + 9;
    const waistW = loose ? w - 0.5 : m.waist / 4 + 2;
    const hemW = loose ? w + 0.5 : Math.max(m.hips / 4 + 2, waistW);
    const len = m.length;
    const waistY = Math.min(len * 0.62, armholeDepth + 18);
    const shX = Math.min(m.shoulder / 2, w - 2);
    const shY = 4;

    let neck;
    switch (neckline) {
      case 'v_neck':
        neck = [{ x: 0, y: isBack ? 3 : 16 }, { x: 7, y: 0 }, { x: shX, y: shY }]; break;
      case 'square':
        neck = isBack
          ? [{ x: 0, y: 3 }, { x: 7, y: 0 }, { x: shX, y: shY }]
          : [{ x: 0, y: 10 }, { x: 6.5, y: 10 }, { x: 6.5, y: 0 }, { x: shX, y: shY }]; break;
      case 'halter':
        neck = [{ x: 0, y: isBack ? 5 : 7 }, { x: 3.5, y: 0 }, { x: 8.5, y: 1.5 }]; break;
      case 'off_shoulder':
        neck = [{ x: 0, y: 5 }, { x: shX * 0.6, y: 7 }, { x: shX + 2, y: 11 }]; break;
      default: // round
        neck = [{ x: 0, y: isBack ? 3 : 9 }, { x: 7, y: 0, c: [isBack ? 3 : 5.5, isBack ? 2 : 8] }, { x: shX, y: shY }];
    }
    const last = neck[neck.length - 1];
    const armX = neckline === 'halter' ? w - 1.5 : w;
    return [
      ...neck,
      { x: armX, y: armholeDepth, c: [last.x + (armX - last.x) * 0.1, last.y + (armholeDepth - last.y) * 0.8] },
      { x: waistW, y: waistY },
      { x: hemW, y: len },
      { x: 0, y: len },
    ];
  }

  function skirtPoints(spec, m) {
    const flare = ['a_line', 'circle', 'flared'].includes(spec.silhouette) ? 8 : 1;
    const wW = m.waist / 4 + 2, hipY = 20, hipW = m.hips / 4 + 2;
    return [{ x: 0, y: 0 }, { x: wW, y: 0 }, { x: hipW, y: hipY }, { x: hipW + flare, y: m.length }, { x: 0, y: m.length }];
  }

  function pantsPoints(spec, m, isBack) {
    const hipW = m.hips / 4 + 2, wW = m.waist / 4 + 2, crotchY = 27, inseam = m.length;
    const thigh = hipW + (isBack ? 4 : 2.5), kneeY = crotchY + (inseam - crotchY) * 0.5, hem = 11;
    return [
      { x: 0, y: 0 }, { x: wW, y: 0 }, { x: hipW, y: 20 }, { x: hipW + 0.5, y: kneeY }, { x: hipW - 1, y: inseam },
      { x: hipW - 1 - hem, y: inseam }, { x: hipW - 7, y: kneeY },
      { x: thigh - 5, y: crotchY + 2, c: [thigh - 3, kneeY - 6] }, { x: 0, y: crotchY - 3, c: [-2, crotchY + 4] },
    ];
  }

  /* ---------- piece -> SVG group ---------- */
  function pieceGroup(title, points, ox, oy, extra) {
    const poly = toPolyline(points);
    const cut = offsetPolygon(poly, SEAM);
    const xs = poly.map(p => p[0]), ys = poly.map(p => p[1]);
    const maxX = Math.max(...xs), maxY = Math.max(...ys), minX = Math.min(...xs);
    const width = maxX - minX, height = maxY;
    const grainX = Math.max(minX + 4, width * 0.3);
    const grainTop = Math.min(height * 0.45, height - 22), grainBot = height - 8;

    const dimW = `<g class="dim"><line x1="${fmt(minX)}" y1="${fmt(height + 2.6)}" x2="${fmt(maxX)}" y2="${fmt(height + 2.6)}" marker-start="url(#pp-arr)" marker-end="url(#pp-arr)"/>
      <text x="${fmt((minX + maxX) / 2)}" y="${fmt(height + 3.9)}" text-anchor="middle">${num(width)} cm</text></g>`;
    const dimH = `<g class="dim"><line x1="${fmt(maxX + 2.6)}" y1="0" x2="${fmt(maxX + 2.6)}" y2="${fmt(height)}" marker-start="url(#pp-arr)" marker-end="url(#pp-arr)"/>
      <text x="${fmt(maxX + 3.3)}" y="${fmt(height / 2)}">${num(height)} cm</text></g>`;
    const notch = (x, y) => `<path class="notch" d="M${fmt(x)} ${fmt(y)} l-0.5 -0.8 M${fmt(x)} ${fmt(y)} l0.5 -0.8" transform="translate(0 0)"/>`;
    const notches = points.length > 5 ? notch(points[points.length - 4].x, points[points.length - 4].y) : '';

    return `
    <g transform="translate(${fmt(ox)} ${fmt(oy)})">
      <text class="title" x="${fmt(minX)}" y="-2.4">${title}</text>
      <polygon class="cut" points="${cut.map(p => fmt(p[0]) + ',' + fmt(p[1])).join(' ')}"/>
      <path class="fill" d="${pathFromPoints(points)}"/>
      <path class="stitch" d="${pathFromPoints(points)}"/>
      ${notches}
      <line class="grain" x1="${fmt(grainX)}" y1="${fmt(grainTop)}" x2="${fmt(grainX)}" y2="${fmt(grainBot)}" marker-start="url(#pp-arr-r)" marker-end="url(#pp-arr-r)"/>
      <text class="grain-t" x="${fmt(grainX + 0.7)}" y="${fmt((grainTop + grainBot) / 2)}">grainline</text>
      ${dimW}${dimH}
      <text class="foot" x="${fmt(minX)}" y="${fmt(height + 6.6)}">✂ Cut ${extra.cut} | Seam allowance: ${SEAM}cm</text>
    </g>`;
  }

  /* ---------- public: build a full SVG string ---------- */
  function buildPatternSVG(spec, m, method) {
    const type = spec.garment_type;
    let pieces;
    if (type === 'skirt') {
      pieces = [['Front Skirt', skirtPoints(spec, m), 1], ['Back Skirt', skirtPoints(spec, m), 1]];
    } else if (type === 'jeans' || type === 'pants') {
      pieces = [['Front Leg', pantsPoints(spec, m, false), 2], ['Back Leg', pantsPoints(spec, m, true), 2]];
    } else {
      pieces = [['Front Bodice', bodicePoints(spec, m, false), 2], ['Back Bodice', bodicePoints(spec, m, true), 2]];
    }

    const gap = 12, padL = 3, padT = 5, padR = 9;
    let x = padL, maxH = 0, body = '';
    pieces.forEach(([title, pts, cut]) => {
      const poly = toPolyline(pts);
      const w = Math.max(...poly.map(p => p[0])) - Math.min(...poly.map(p => p[0]));
      const h = Math.max(...poly.map(p => p[1]));
      body += pieceGroup(title, pts, x - Math.min(...poly.map(p => p[0])), padT + 3, { cut });
      x += w + gap + 5; maxH = Math.max(maxH, h);
    });
    const W = (x - gap + padR) * 10, H = (padT + 6 + maxH + 9) * 10; // mm
    const label = (method || 'Aldrich').replace(/[<>&"]/g, '');

    return `<svg xmlns="http://www.w3.org/2000/svg" width="${fmt(W)}mm" height="${fmt(H)}mm" viewBox="0 0 ${fmt(W / 10)} ${fmt(H / 10)}" role="img" aria-label="Sewing pattern preview">
  <title>Pattern Pilot · ${label} · placeholder preview</title>
  <defs>
    <marker id="pp-arr" viewBox="0 0 6 6" refX="3" refY="3" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M0 0 6 3 0 6z" fill="#1c7ed6"/></marker>
    <marker id="pp-arr-r" viewBox="0 0 6 6" refX="3" refY="3" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M0 0 6 3 0 6z" fill="#e03131"/></marker>
    <style>
      .stitch{fill:none;stroke:#1b1b1b;stroke-width:.09;stroke-linejoin:round}
      .fill{fill:#ececec;stroke:none}
      .cut{fill:none;stroke:#e03131;stroke-width:.07;stroke-dasharray:.45 .3}
      .grain{stroke:#e03131;stroke-width:.07;stroke-dasharray:.45 .3}
      .grain-t{fill:#e03131;font:.95px sans-serif}
      .dim line{stroke:#1c7ed6;stroke-width:.06}
      .dim text{fill:#1c7ed6;font:1.05px sans-serif}
      .notch{stroke:#1b1b1b;stroke-width:.09;fill:none}
      .title{font:bold 1.5px sans-serif;fill:#111}
      .foot{font:1px sans-serif;fill:#222}
    </style>
  </defs>
  <rect width="100%" height="100%" fill="#fff"/>
  ${body}
</svg>`;
  }

  window.MockPattern = { buildPatternSVG };
})();
