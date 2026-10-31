/* ==========================================================================
   LIQUID LOGO · WebGL "liquid metal" effect for the Pattern Pilot logo
   --------------------------------------------------------------------------
   Inspired by the liquid-logo idea (a logo shape rendered as flowing liquid
   metal). This is our own small implementation tuned to the pink/mauve theme:

     1. The logo shape (mark + wordmark) is drawn into a hidden 2D canvas = a mask.
     2. A fragment shader blurs the mask to get a soft "height", derives a normal
        from it, and maps that through animated bands of mauve / rose / pale pink.
     3. The light follows the pointer, so the metal ripples when you move.

   If WebGL isn't available, the plain SVG/text fallback in the HTML stays visible.

   Use:  <div class="logo" data-liquid data-h="64"> <span class="logo-fallback">…</span> </div>
   data-h = logo height in CSS px · data-text="false" for the mark only.

   Want to use the ORIGINAL liquid-logo library instead? Replace drawMask()'s output
   with your own logo image and swap the shader — the mount() wiring can stay.
   ========================================================================== */
(function () {
  'use strict';

  const VS = `attribute vec2 p; varying vec2 uv; void main(){ uv = p*.5+.5; gl_Position = vec4(p,0.,1.); }`;
  const FS = `
  precision mediump float;
  varying vec2 uv;
  uniform sampler2D mask;     // crisp logo shape (alpha)
  uniform sampler2D height;   // blurred logo shape = soft "bump"
  uniform vec2 px;            // 1 / texture size
  uniform float e;            // normal sample distance in texels
  uniform float t;
  uniform vec2 mouse;
  uniform vec3 c1, c2, c3;
  void main(){
    float m = texture2D(mask, uv).a;
    if (m < 0.003) { gl_FragColor = vec4(0.0); return; }
    vec2 d = px * e;
    float h  = texture2D(height, uv).a;
    vec2 g = vec2(texture2D(height, uv + vec2(d.x, 0.)).a - texture2D(height, uv - vec2(d.x, 0.)).a,
                  texture2D(height, uv + vec2(0., d.y)).a - texture2D(height, uv - vec2(0., d.y)).a);
    // slow flowing distortion so the metal keeps moving
    float flow = sin(uv.x * 5.0 + t * 0.7 + sin(uv.y * 4.0 - t * 0.5) * 1.2) * 0.30
               + cos(uv.y * 5.0 - t * 0.6 + uv.x * 2.0) * 0.20;
    // light direction follows the pointer
    vec2 L = normalize(mouse - uv + vec2(0.0001));
    float lit = dot(g, L) * 9.0;
    float band = h * 2.4 + lit + flow + t * 0.05;
    float b  = 0.5 + 0.5 * sin(band * 4.6);
    float b2 = 0.5 + 0.5 * sin(band * 8.0 + 1.3);
    vec3 col = mix(c1, c2, smoothstep(0.05, 0.95, b));
    col = mix(col, c3, smoothstep(0.7, 1.0, b2) * 0.38);
    // crisp specular streak
    col += vec3(1.0) * pow(max(0.0, 1.0 - abs(b - 0.5) * 3.0), 10.0) * 0.18;
    // darken the very edge slightly so the shape stays readable on pale pink
    col *= 0.82 + 0.18 * smoothstep(0.0, 0.5, h + 0.2);
    gl_FragColor = vec4(col * m, m);
  }`;

  const instances = [];
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const hex = (h) => [parseInt(h.slice(1, 3), 16) / 255, parseInt(h.slice(3, 5), 16) / 255, parseInt(h.slice(5, 7), 16) / 255];

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath(); ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }

  /** Draw the logo shape (alpha only) and return its CSS size. */
  function drawMask(canvas, h, withText, dpr) {
    const ctx = canvas.getContext('2d');
    const pad = h * 0.08, s = h - pad * 2;
    const fontPx = h * 0.56;
    ctx.font = `700 ${fontPx * dpr}px "Playfair Display", Georgia, serif`;
    const textW = withText ? ctx.measureText('Pattern Pilot').width / dpr : 0;
    const gap = h * 0.22;
    const cssW = Math.ceil(pad * 2 + s + (withText ? gap + textW : 0));
    canvas.width = Math.round(cssW * dpr); canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, h);
    ctx.fillStyle = '#000';

    // mark: rounded tile with a needle + thread cut out of it
    roundRect(ctx, pad, pad, s, s, s * 0.3); ctx.fill();
    ctx.save(); ctx.globalCompositeOperation = 'destination-out';
    const u = s / 48, ox = pad, oy = pad;
    ctx.lineCap = 'round'; ctx.strokeStyle = '#000'; ctx.lineWidth = 3.2 * u;
    ctx.beginPath(); ctx.moveTo(ox + 15 * u, oy + 35 * u); ctx.lineTo(ox + 35 * u, oy + 12 * u); ctx.stroke();
    ctx.lineWidth = 2.1 * u; ctx.setLineDash([0.1 * u, 4.6 * u]);
    ctx.beginPath(); ctx.moveTo(ox + 13 * u, oy + 36 * u);
    ctx.bezierCurveTo(ox + 14 * u, oy + 27 * u, ox + 23 * u, oy + 31 * u, ox + 25 * u, oy + 24 * u);
    ctx.bezierCurveTo(ox + 27 * u, oy + 17 * u, ox + 34 * u, oy + 20 * u, ox + 36 * u, oy + 13 * u); ctx.stroke();
    ctx.restore();

    if (withText) {
      ctx.font = `700 ${fontPx}px "Playfair Display", Georgia, serif`;
      ctx.textBaseline = 'middle'; ctx.fillStyle = '#000';
      ctx.fillText('Pattern Pilot', pad * 2 + s + gap - pad, h / 2 + h * 0.03);
    }
    return cssW;
  }

  /** Blurred copy of the mask. Uses ctx.filter when available, else stacked offsets. */
  function makeHeight(mask, blurPx) {
    const c = document.createElement('canvas'); c.width = mask.width; c.height = mask.height;
    const x = c.getContext('2d');
    if ('filter' in x) { x.filter = `blur(${blurPx}px)`; x.drawImage(mask, 0, 0); x.filter = 'none'; }
    else {
      const n = 5, r = blurPx * 0.9; x.globalAlpha = 1 / (n * n);
      for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) x.drawImage(mask, (i - 2) * r / 2, (j - 2) * r / 2);
    }
    return c;
  }

  function upload(gl, unit, canvas) {
    const tex = gl.createTexture();
    gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, canvas);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  }

  function compile(gl, type, src) {
    const sh = gl.createShader(type); gl.shaderSource(sh, src); gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh));
    return sh;
  }

  function mount(el) {
    const h = parseFloat(el.dataset.h) || 56;
    const withText = el.dataset.text !== 'false';
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    try {
      const mask = document.createElement('canvas');
      const cssW = drawMask(mask, h, withText, dpr);

      const cv = document.createElement('canvas');
      cv.className = 'liquid-canvas'; cv.width = mask.width; cv.height = mask.height;
      cv.style.width = cssW + 'px'; cv.style.height = h + 'px';
      cv.setAttribute('aria-hidden', 'true');
      const gl = cv.getContext('webgl', { premultipliedAlpha: true, alpha: true, antialias: true });
      if (!gl) throw new Error('no webgl');

      const prog = gl.createProgram();
      gl.attachShader(prog, compile(gl, gl.VERTEX_SHADER, VS));
      gl.attachShader(prog, compile(gl, gl.FRAGMENT_SHADER, FS));
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error('link failed');
      gl.useProgram(prog);

      const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
      const loc = gl.getAttribLocation(prog, 'p'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

      upload(gl, 0, mask);
      upload(gl, 1, makeHeight(mask, h * 0.16 * dpr));

      const U = (n) => gl.getUniformLocation(prog, n);
      gl.uniform1i(U('mask'), 0);
      gl.uniform1i(U('height'), 1);
      gl.uniform2f(U('px'), 1 / cv.width, 1 / cv.height);
      gl.uniform1f(U('e'), Math.max(1.5, cv.height * 0.035));
      gl.uniform3fv(U('c1'), hex('#4A2340'));   // deep mauve
      gl.uniform3fv(U('c2'), hex('#C85E8C'));   // rose
      gl.uniform3fv(U('c3'), hex('#F4B9D0'));   // soft pink highlight (kept mid-tone so text stays legible)
      gl.viewport(0, 0, cv.width, cv.height);
      gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);

      const inst = { el, cv, gl, U, mouse: [0.5, 0.5], target: [0.5, 0.5], t: Math.random() * 10 };
      el.classList.add('is-liquid');
      el.appendChild(cv);
      instances.push(inst);
      renderOne(inst, 0);
    } catch (e) {
      // keep the SVG/text fallback
      el.classList.remove('is-liquid');
    }
  }

  function renderOne(inst, dt) {
    const { gl, U } = inst;
    inst.t += dt;
    inst.mouse[0] += (inst.target[0] - inst.mouse[0]) * 0.08;
    inst.mouse[1] += (inst.target[1] - inst.mouse[1]) * 0.08;
    gl.uniform1f(U('t'), inst.t);
    gl.uniform2f(U('mouse'), inst.mouse[0], inst.mouse[1]);
    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }

  let running = false, last = 0;
  function loop(now) {
    if (!running) return;
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    instances.forEach((inst) => { if (inst.el.offsetParent !== null) renderOne(inst, dt * 0.9); });
    requestAnimationFrame(loop);
  }
  function start() { if (reduce || running || document.hidden) return; running = true; last = performance.now(); requestAnimationFrame(loop); }
  document.addEventListener('visibilitychange', () => { running = false; start(); });

  window.addEventListener('pointermove', (e) => {
    instances.forEach((inst) => {
      const r = inst.cv.getBoundingClientRect(); if (!r.width) return;
      inst.target = [(e.clientX - r.left) / r.width, 1 - (e.clientY - r.top) / r.height];
    });
  }, { passive: true });

  function mountAll() {
    document.querySelectorAll('[data-liquid]:not(.is-liquid)').forEach(mount);
    start();
  }

  // wait for the serif font so the wordmark is drawn correctly
  const ready = document.fonts && document.fonts.load ? document.fonts.load('700 40px "Playfair Display"').catch(() => {}) : Promise.resolve();
  Promise.race([ready, new Promise((r) => setTimeout(r, 1500))]).then(mountAll);

  window.LiquidLogo = { mountAll };
})();
