/* ==========================================================================
   FLOW BG · animated sheer-fabric ribbons (original canvas animation)
   Inspired by flowing pink chiffon. Pure canvas 2D, no libraries.
   - Drifts on its own, and also "billows" a little as the page scrolls.
   - Softer inside the app (body.in-app) so it never fights the forms.
   - Respects prefers-reduced-motion (draws one still frame).
   - Tweak the look in RIBBONS below (position, size, speed, opacity).
   ========================================================================== */
(function () {
  'use strict';
  const cvs = document.getElementById('flow-bg');
  if (!cvs || !cvs.getContext) return;
  const ctx = cvs.getContext('2d');
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const TAU = Math.PI * 2;

  // y = vertical position (0..1), amp = wave height, k = waves across the screen,
  // w = ribbon half-width, speed = drift, a = opacity, tint = [r,g,b]
  const RIBBONS = [
    { y: .30, amp: .10, k: 1.1, w: .12, speed: .035, phase: 0.0, a: .34, tint: [244, 160, 188] },
    { y: .42, amp: .13, k: 1.5, w: .10, speed: -.028, phase: 1.7, a: .28, tint: [250, 186, 206] },
    { y: .55, amp: .09, k: 0.9, w: .15, speed: .022, phase: 3.1, a: .26, tint: [238, 140, 176] },
    { y: .66, amp: .12, k: 1.8, w: .08, speed: -.040, phase: 4.4, a: .30, tint: [246, 172, 198] },
    { y: .24, amp: .08, k: 2.1, w: .06, speed: .045, phase: 5.2, a: .22, tint: [252, 205, 220] },
    { y: .78, amp: .10, k: 1.3, w: .11, speed: .030, phase: 2.4, a: .24, tint: [236, 150, 184] },
  ];

  let W = 0, H = 0, dpr = 1, running = false, last = 0, clock = 0;

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    W = window.innerWidth; H = window.innerHeight;
    cvs.width = Math.round(W * dpr); cvs.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (!running) draw(clock);
  }

  function ribbonPath(r, t, scroll) {
    const n = 70, top = [], bot = [];
    const drift = t * r.speed * TAU + r.phase + scroll * 0.0016;
    for (let i = 0; i <= n; i++) {
      const u = i / n;
      const x = -W * 0.1 + u * W * 1.2;
      const cy = H * (r.y
        + r.amp * Math.sin(u * r.k * TAU + drift)
        + r.amp * 0.55 * Math.sin(u * r.k * 2.3 * TAU - drift * 1.3 + r.phase));
      // fabric "pinch": width swells and narrows along the length
      const pinch = 0.22 + 0.78 * Math.pow(Math.sin(u * Math.PI * (r.k + 0.6) + drift * 0.7), 2);
      const hw = H * r.w * pinch;
      top.push([x, cy - hw]); bot.push([x, cy + hw]);
    }
    return { top, bot };
  }

  function draw(t) {
    const intensity = document.body.classList.contains('in-app') ? 0.55 : 1;
    const scroll = window.scrollY || 0;

    const bg = ctx.createLinearGradient(0, 0, W, H);
    bg.addColorStop(0, '#FFFEFE'); bg.addColorStop(0.5, '#FEF3F7'); bg.addColorStop(1, '#FBE1EB');
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

    RIBBONS.forEach((r) => {
      const { top, bot } = ribbonPath(r, t, scroll);
      const [R, G, B] = r.tint, a = r.a * intensity;

      // body of the ribbon: clear at the ends, denser in the middle (like sheer chiffon)
      const g = ctx.createLinearGradient(0, 0, W, 0);
      g.addColorStop(0, `rgba(${R},${G},${B},0)`);
      g.addColorStop(0.25, `rgba(${R},${G},${B},${a})`);
      g.addColorStop(0.7, `rgba(${R},${G},${B},${a * 0.85})`);
      g.addColorStop(1, `rgba(${R},${G},${B},${a * 0.15})`);

      ctx.beginPath();
      top.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
      for (let i = bot.length - 1; i >= 0; i--) ctx.lineTo(bot[i][0], bot[i][1]);
      ctx.closePath();
      ctx.fillStyle = g; ctx.fill();

      // light catching the top edge, soft shadow along the bottom edge
      ctx.lineWidth = 1.2;
      ctx.strokeStyle = `rgba(255,255,255,${0.75 * intensity})`;
      ctx.beginPath(); top.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]))); ctx.stroke();
      ctx.strokeStyle = `rgba(${R - 14},${G - 30},${B - 20},${0.20 * intensity})`;
      ctx.beginPath(); bot.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]))); ctx.stroke();
    });
  }

  function frame(now) {
    if (!running) return;
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    clock += dt;
    draw(clock);
    requestAnimationFrame(frame);
  }
  function start() { if (reduce || running || document.hidden) return; running = true; last = performance.now(); requestAnimationFrame(frame); }
  function stop() { running = false; }

  window.addEventListener('resize', resize);
  document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
  if (reduce) window.addEventListener('scroll', () => draw(clock), { passive: true });
  resize(); start();
})();
