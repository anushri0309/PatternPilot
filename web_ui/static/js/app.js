/* ==========================================================================
   PATTERN PILOT · app.js  (UI behaviour only — no backend logic here)
   Sections:  0 helpers · 1 state · 2 motion · 3 auth · 4 navigation
              5 upload · 6 review · 7 measurements · 8 generate · 9 results
   ========================================================================== */
(function () {
  'use strict';

  const API = window.PatternPilotAPI;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------------------------------------------------------------- 0 helpers */
  function safeStore(op, key, val) {
    try { return op === 'get' ? localStorage.getItem(key) : op === 'set' ? localStorage.setItem(key, val) : localStorage.removeItem(key); }
    catch (e) { return null; }
  }
  function toast(msg) {
    const el = document.createElement('div');
    el.className = 'toast'; el.textContent = msg;
    $('#toasts').appendChild(el);
    setTimeout(() => { el.classList.add('out'); setTimeout(() => el.remove(), 320); }, 3200);
  }
  function setLoading(btn, on) { btn.classList.toggle('is-loading', on); btn.disabled = on; }
  function showError(el, msg) { el.textContent = msg; el.hidden = !msg; }
  const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
  const labelFor = (group, value) => (API.OPTIONS[group].find((o) => o[0] === value) || [value, value])[1];

  /* Strip anything executable from SVG text before putting it in the page */
  function sanitizeSVG(text) {
    const doc = new DOMParser().parseFromString(text, 'image/svg+xml');
    const svg = doc.documentElement;
    if (!svg || svg.nodeName.toLowerCase() !== 'svg' || doc.querySelector('parsererror')) throw new Error('The pattern came back in an unexpected format.');
    $$('script, foreignObject', svg).forEach((n) => n.remove());
    [svg, ...$$('*', svg)].forEach((n) => {
      Array.from(n.attributes).forEach((a) => {
        if (/^on/i.test(a.name) || /^\s*javascript:/i.test(a.value)) n.removeAttribute(a.name);
      });
    });
    return new XMLSerializer().serializeToString(svg);
  }

  /* ---------------------------------------------------------------- 1 state */
  const state = {
    user: null,
    file: null,
    previewUrl: null,
    predictions: null,
    spec: {},
    chosenLength: null,
    unit: 'cm',
    unlocked: 1,         // highest unlocked step
    current: 1,          // step being viewed
    done: new Set(),
    svgText: '',
    zoom: { mode: 'fit', factor: 1 },
  };

  /* ---------------------------------------------------------------- 2 motion */
  let lenis = null;
  function initMotion() {
    if (reduceMotion || !window.Lenis) return;
    try {
      lenis = new window.Lenis({ lerp: 0.1, wheelMultiplier: 1 });
      const raf = (t) => { lenis.raf(t); requestAnimationFrame(raf); };
      requestAnimationFrame(raf);
    } catch (e) { lenis = null; }
  }
  function scrollToEl(el, offset = -24) {
    if (!el) return;
    if (lenis) lenis.scrollTo(el, { offset, duration: 1.1 });
    else el.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
  }
  function reveal(el) {
    el.hidden = false;
    if (reduceMotion) return;
    if (window.gsap) window.gsap.fromTo(el, { y: 32, opacity: 0 }, { y: 0, opacity: 1, duration: .7, ease: 'power3.out', clearProps: 'transform,opacity' });
    else { el.classList.remove('reveal'); void el.offsetWidth; el.classList.add('reveal'); }
  }
  const viewHome = $('#view-home'), viewLogin = $('#view-login'), viewApp = $('#view-app');

  function enter(view) {
    $$('.view').forEach((v) => { v.hidden = v !== view; v.classList.remove('fade-in'); });
    document.body.classList.toggle('in-app', view === viewApp);
    document.body.classList.toggle('in-auth', view === viewLogin);
    void view.offsetWidth; view.classList.add('fade-in');
    window.scrollTo(0, 0);
  }

  /* ---------------------------------------------------------------- 3 auth */
  let authMode = 'login';

  $$('[data-open-login]').forEach((b) => b.addEventListener('click', () => { setAuthMode('login'); enter(viewLogin); }));
  $$('[data-enter-studio]').forEach((b) => b.addEventListener('click', () => {
    if (state.user) { enter(viewApp); }
    else { setAuthMode('login'); enter(viewLogin); }
  }));
  $$('[data-home]').forEach((b) => b.addEventListener('click', (e) => { e.preventDefault(); enter(viewHome); }));
  $$('[data-process]').forEach((b) => b.addEventListener('click', (e) => {
    e.preventDefault(); if (viewHome.hidden) enter(viewHome);
    setTimeout(() => scrollToEl($('#home-process'), -10), 30);
  }));

  function moveThumb(seg) {
    const active = $('.is-active', seg); const thumb = $('.seg-thumb', seg);
    if (!active || !thumb) return;
    thumb.style.width = active.offsetWidth + 'px';
    thumb.style.transform = `translateX(${active.offsetLeft - 4}px)`;
  }

  function setAuthMode(mode) {
    authMode = mode;
    const reg = mode === 'register';
    $$('#auth-tabs .seg-btn').forEach((b) => {
      const on = b.dataset.mode === mode; b.classList.toggle('is-active', on); b.setAttribute('aria-selected', on);
    });
    moveThumb($('#auth-tabs'));
    $$('.only-register', viewLogin).forEach((n) => (n.hidden = !reg));
    $$('.only-login', viewLogin).forEach((n) => (n.hidden = reg));
    $('#auth-submit .btn-label').textContent = reg ? 'Create my account' : 'Sign in';
    $('#auth-password').autocomplete = reg ? 'new-password' : 'current-password';
    showError($('#auth-error'), '');
    $$('#auth-form input').forEach((i) => i.removeAttribute('aria-invalid'));
  }
  $$('#auth-tabs .seg-btn').forEach((b) => b.addEventListener('click', () => setAuthMode(b.dataset.mode)));
  $$('[data-switch]').forEach((b) => b.addEventListener('click', () => setAuthMode(b.dataset.switch)));

  $('.pw-toggle').addEventListener('click', (e) => {
    const btn = e.currentTarget, input = $('#auth-password');
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    btn.setAttribute('aria-pressed', show); btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    $('.i-eye', btn).hidden = show; $('.i-eye-off', btn).hidden = !show;
  });

  $('#auth-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = $('#auth-name').value.trim(), email = $('#auth-email').value.trim();
    const pw = $('#auth-password').value, confirm = $('#auth-confirm').value;
    const err = $('#auth-error');
    $$('#auth-form input').forEach((i) => i.removeAttribute('aria-invalid'));
    const bad = (id, msg) => { $(id).setAttribute('aria-invalid', 'true'); $(id).focus(); showError(err, msg); };

    if (!email) return bad('#auth-email', 'Please enter your email or username.');
    if (pw.length < 6) return bad('#auth-password', 'Your password needs at least 6 characters.');
    if (authMode === 'register' && pw !== confirm) return bad('#auth-confirm', "Those passwords don't match.");
    showError(err, '');

    const btn = $('#auth-submit'); setLoading(btn, true);
    try {
      const res = authMode === 'register' ? await API.register(name, email, pw) : await API.login(email, pw);
      state.user = { name: res.name || name || email.split('@')[0] };
      safeStore('set', 'pp_user', JSON.stringify(state.user));
      startApp();
    } catch (ex) {
      showError(err, ex.message);
      $('#auth-password').setAttribute('aria-invalid', 'true');
    } finally { setLoading(btn, false); }
  });

  $('#logout-btn').addEventListener('click', async () => {
    try { await API.logout(); } catch (e) { /* ignore */ }
    safeStore('del', 'pp_user');
    resetWorkflow();
    state.user = null;
    $('#auth-password').value = ''; $('#auth-confirm').value = '';
    closeMenu(); enter(viewHome); setAuthMode('login');
    toast('You’re logged out. See you soon! 🧵');
  });

  /* ---------------------------------------------------------------- 4 navigation */
  const steps = $$('.step');
  const navItems = $$('#steps-nav li');

  function refreshNav() {
    navItems.forEach((li) => {
      const n = +li.dataset.step;
      li.classList.toggle('is-locked', n > state.unlocked);
      li.classList.toggle('is-done', state.done.has(n));
      li.classList.toggle('is-active', n === state.current);
      $('button', li).disabled = n > state.unlocked;
      if (n === state.current) li.setAttribute('aria-current', 'step'); else li.removeAttribute('aria-current');
    });
    steps.forEach((s) => {
      const n = +s.dataset.step;
      s.classList.toggle('is-active', n === state.current);
      s.classList.toggle('is-locked', n > state.unlocked);
    });
    const pct = (state.done.size / 5) * 100;
    $('#progress-bar').style.width = pct + '%';
    $('#progress-text').textContent = state.done.size === 5 ? 'All done 🎉' : `Step ${Math.min(state.current, 5)} of 5`;
  }

  function goToStep(n, { scroll = true } = {}) {
    const el = $('#step-' + n);
    const wasHidden = el.hidden;
    state.unlocked = Math.max(state.unlocked, n);
    state.current = n;
    if (wasHidden) reveal(el);
    refreshNav();
    if (scroll) setTimeout(() => scrollToEl(el), wasHidden ? 60 : 0);
    closeMenu();
  }
  function completeStep(n) { state.done.add(n); refreshNav(); }

  navItems.forEach((li) => $('button', li).addEventListener('click', () => {
    const n = +li.dataset.step; if (n <= state.unlocked) { state.current = n; refreshNav(); scrollToEl($('#step-' + n)); closeMenu(); }
  }));

  // Highlight the step that's in view while scrolling
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting && !en.target.hidden) { state.current = +en.target.dataset.step; refreshNav(); } });
    }, { rootMargin: '-35% 0px -55% 0px' });
    steps.forEach((s) => io.observe(s));
  }

  // Mobile drawer
  const sidebar = $('#sidebar'), scrim = $('#scrim'), menuBtn = $('#menu-btn');
  function openMenu() { sidebar.classList.add('open'); scrim.hidden = false; menuBtn.setAttribute('aria-expanded', 'true'); }
  function closeMenu() { sidebar.classList.remove('open'); scrim.hidden = true; menuBtn.setAttribute('aria-expanded', 'false'); }
  menuBtn.addEventListener('click', () => (sidebar.classList.contains('open') ? closeMenu() : openMenu()));
  scrim.addEventListener('click', closeMenu);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeMenu(); });

  function resetWorkflow() {
    if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
    Object.assign(state, { file: null, previewUrl: null, predictions: null, spec: {}, unlocked: 1, current: 1, done: new Set(), svgText: '' });
    $('#file-input').value = '';
    $('#preview-img').removeAttribute('src'); $('#detect-thumb').removeAttribute('src'); $('#file-name').textContent = '';
    $('#preview').hidden = true; $('#dropzone').hidden = false;
    $('#analyze-btn').disabled = true;
    $('#analyze-btn .btn-label').textContent = 'Analyze garment ✨';
    $('#detect-chips').innerHTML = ''; $('#review-grid').innerHTML = ''; $('#summary-chips').innerHTML = '';
    $('#picker').hidden = true; $('#detect-alts').innerHTML = ''; $('#detect-alts').hidden = true;
    $('#shoulder-band-wrap').hidden = true; $('#shoulder-band').checked = false;
    showError($('#upload-error'), '');
    steps.forEach((s) => { if (s.dataset.step !== '1') s.hidden = true; });
    $('#viewer-canvas').innerHTML = '';
    $('#gen-error').hidden = true; $('#gen-loading').hidden = true; $('.generate-box').classList.remove('busy');
    refreshNav();
  }

  function startApp() {
    const name = state.user.name || 'friend';
    $('#user-name').textContent = cap(name);
    resetWorkflow();
    enter(viewApp);
    refreshNav();
    toast(`Hi ${cap(name)}! Let’s make something lovely ✨`);
  }

  /* ---------------------------------------------------------------- 5 upload */
  const dz = $('#dropzone'), fileInput = $('#file-input');
  const MAX_MB = 10;

  function handleFile(file) {
    const err = $('#upload-error'); showError(err, '');
    if (!file) return;
    if (!/^image\/(png|jpeg)$/.test(file.type)) return showError(err, 'Please choose a JPG or PNG image.');
    if (file.size > MAX_MB * 1024 * 1024) return showError(err, `That image is over ${MAX_MB} MB. Try a smaller one.`);
    if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
    state.file = file; state.previewUrl = URL.createObjectURL(file);
    $('#preview-img').src = state.previewUrl;
    $('#file-name').textContent = file.name;
    dz.hidden = true; $('#preview').hidden = false;
    $('#analyze-btn').disabled = false;
    // choosing a new photo invalidates everything after it
    state.done.delete(1);
    ['2', '3', '4', '5'].forEach((n) => { $('#step-' + n).hidden = true; state.done.delete(+n); });
    state.predictions = null; state.spec = {}; state.svgText = '';
    state.unlocked = 1; state.current = 1; refreshNav();
    // Start garment detection automatically after a valid image is selected.
    setTimeout(() => { if (state.file === file) $('#analyze-btn').click(); }, 80);
  }
  fileInput.addEventListener('change', () => handleFile(fileInput.files[0]));
  ['dragenter', 'dragover'].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add('is-over'); }));
  ['dragleave', 'drop'].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove('is-over'); }));
  dz.addEventListener('drop', (e) => handleFile(e.dataTransfer.files[0]));
  $('#replace-btn').addEventListener('click', () => { fileInput.value = ''; fileInput.click(); });
  $('#remove-photo-btn').addEventListener('click', () => { resetWorkflow(); toast('Photo removed. Choose another whenever you’re ready.'); });

  $('#analyze-btn').addEventListener('click', async () => {
    const btn = $('#analyze-btn'); showError($('#upload-error'), '');
    const fileBeingAnalyzed = state.file;
    if (!fileBeingAnalyzed) return;
    setLoading(btn, true); $('#scan-overlay').hidden = false;
    try {
      const res = await API.analyzeGarment(fileBeingAnalyzed);
      if (state.file !== fileBeingAnalyzed) return;
      state.predictions = res;
      state.spec = {
        garment_type: res.garment_type, gender: res.gender, silhouette: res.silhouette, neckline: res.neckline,
        sleeve_length: res.sleeve_length, waistline: res.waistline, length: res.length, shoulder_band: false,
      };
      renderReview();
      completeStep(1); goToStep(2);
    } catch (ex) {
      showError($('#upload-error'), ex.message || 'Something went wrong while analysing the photo.');
    } finally { setLoading(btn, false); $('#scan-overlay').hidden = true; }
  });

  /* ---------------------------------------------------------------- 6 review */
  const BOTTOMS = ['jeans', 'pants', 'skirt'];          // garments with no neckline / sleeves
  const isBottom = () => BOTTOMS.includes(state.spec.garment_type);
  const REVIEW_FIELDS = [
    ['silhouette', 'Silhouette'], ['neckline', 'Neckline'], ['sleeve_length', 'Sleeve length'],
    ['waistline', 'Waistline'], ['length', 'Length'],
  ];
  const NA_KEYS = ['neckline', 'sleeve_length'];
  const confClass = (c) => (c >= 0.7 ? 'high' : c >= 0.55 ? 'mid' : 'low');

  const ICON = {
    t_shirt: '<path d="M22 8l-14 8 7 12 7-4v30h28V24l7 4 7-12-14-8c-2 6-7 9-10 9s-8-3-10-9z"/>',
    blouse:  '<path d="M23 8l-13 7 6 12 7-4-2 33h34l-2-33 7 4 6-12-13-7c-2 6-6 10-9 14-3-4-7-8-9-14z"/>',
    jeans:   '<path d="M20 8h24l5 50H36l-4-30-4 30H15z"/><path d="M20 15h24M32 15v13"/>',
    pants:   '<path d="M22 8h20l4 50H35l-3-32-3 32H18z"/><path d="M22 14h20"/>',
    skirt:   '<path d="M22 10h20l11 46H11z"/><path d="M22 17h20"/>',
    dress:   '<path d="M25 6l-7 5 4 13-8 34h42l-8-34 4-13-7-5c-1 4-5 7-8 7s-7-3-8-7z"/><path d="M22 24h20"/>',
  };
  const iconSVG = (k) => `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[k] || ICON.t_shirt}</svg>`;

  function buildTiles() {
    const box = $('#tiles'); box.innerHTML = '';
    API.OPTIONS.garment_type.forEach(([v, l]) => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'tile'; b.dataset.value = v;
      b.setAttribute('role', 'radio'); b.setAttribute('aria-checked', 'false');
      b.innerHTML = `${iconSVG(v)}<span>${l}</span>`;
      b.addEventListener('click', () => chooseGarment(v));
      box.appendChild(b);
    });
  }

  function setPicker(open) {
    $('#picker').hidden = !open;
    const btn = $('#detect-change');
    btn.setAttribute('aria-expanded', open);
    btn.textContent = open ? 'Hide choices' : 'Not right? Choose it myself';
  }
  $('#detect-change').addEventListener('click', () => setPicker($('#picker').hidden));

  function chooseGarment(v) {
    state.spec.garment_type = v;
    if (isBottom()) state.spec.shoulder_band = false;
    paintDetect(); applyRelevance();
    const corrected = v !== state.predictions.garment_type;
    if (corrected) toast(`Got it, using ${labelFor('garment_type', v)}.`);
  }

  function paintDetect() {
    const p = state.predictions, g = state.spec.garment_type;
    const conf = (p.confidence || {}).garment_type;
    const fixed = g !== p.garment_type;
    const box = $('#detect');
    box.classList.toggle('is-fixed', fixed);
    box.classList.toggle('is-low', !fixed && conf != null && conf < 0.55);
    box.classList.toggle('is-mid', !fixed && conf != null && conf >= 0.55 && conf < 0.7);
    $('#detect-kicker').textContent = fixed ? 'You chose' : 'We think this is a';
    $('#detect-label').textContent = labelFor('garment_type', g);
    $('#detect-conf').textContent = fixed ? 'Corrected by you ✓' : conf != null ? `${Math.round(conf * 100)}% sure` : '';
    $('#detect-meter-wrap').hidden = conf == null;
    requestAnimationFrame(() => { $('#detect-meter').style.width = (conf != null ? Math.round(conf * 100) : 0) + '%'; });

    const hint = $('#detect-hint');
    const unsure = !fixed && conf != null && conf < 0.7;
    hint.hidden = !unsure;
    if (unsure) hint.textContent = 'I’m not completely sure about this one. Please check it, and change it if it’s wrong.';

    const alts = $('#detect-alts'); alts.innerHTML = '';
    const list = (p.alternatives || []).filter((a) => a.garment_type !== g);
    if (fixed && p.garment_type !== g) list.unshift({ garment_type: p.garment_type, confidence: conf });
    alts.hidden = !list.length;
    if (list.length) {
      alts.append('Other guesses:');
      list.forEach((a) => {
        const b = document.createElement('button'); b.type = 'button'; b.className = 'alt-chip';
        b.innerHTML = `${labelFor('garment_type', a.garment_type)}${a.confidence != null ? ` <small>${Math.round(a.confidence * 100)}%</small>` : ''}`;
        b.addEventListener('click', () => chooseGarment(a.garment_type));
        alts.appendChild(b);
      });
    }
    $$('.tile', $('#tiles')).forEach((t) => t.setAttribute('aria-checked', t.dataset.value === g));
  }

  function renderReview() {
    const p = state.predictions, conf = p.confidence || {};
    $('#detect-thumb').src = state.previewUrl;
    buildTiles();

    const chips = $('#detect-chips'); chips.innerHTML = '';
    const addChip = (html, cls = '') => { const c = document.createElement('span'); c.className = 'chip ' + cls; c.innerHTML = html; chips.appendChild(c); };
    addChip(`Gender <small>${cap(p.gender || 'unknown')}</small>`);
    const vals = Object.values(conf);
    if (vals.length) {
      const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
      addChip(`Overall confidence <small>${Math.round(avg * 100)}%</small>`, 'conf ' + (avg >= .7 ? '' : avg >= .55 ? 'mid' : 'low'));
    }

    const grid = $('#review-grid'); grid.innerHTML = '';
        REVIEW_FIELDS.forEach(([key, label]) => {
      const field = document.createElement('div'); field.className = 'field'; field.id = 'rf-' + key;
      const c = conf[key];
      const tag = c != null ? `<span class="conf-tag ${confClass(c)}">${Math.round(c * 100)}%</span>` : '';
      field.innerHTML = `<label for="sel-${key}">${label}${tag}</label>`;

      const sel = document.createElement('select'); sel.id = 'sel-' + key;
      API.OPTIONS[key].forEach(([v, l]) => sel.add(new Option(l, v)));
      sel.value = state.spec[key];

            sel.addEventListener('change', () => {
          state.spec[key] = sel.value;
          if (key === 'neckline') syncShoulderBand();
          if (key === 'sleeve_length') syncSleeveField();

          if (key === 'length') {
              // Save the choice to state so we can apply it later
              state.chosenLength = sel.value;

              // Try to update the input if it already exists
              const lenInput = document.getElementById('m-length');
              if (lenInput) {
                  let newLen = 60;
                  if (sel.value.includes('floor')) newLen = 145;
                  else if (sel.value.includes('maxi')) newLen = 120;
                  else if (sel.value.includes('midi')) newLen = 85;
                  else if (sel.value.includes('mini') || sel.value.includes('crop')) newLen = 45;
                  else if (sel.value.includes('hip')) newLen = 40;
                  lenInput.value = newLen;
                  measureValuesCm['length'] = newLen;
              }
          }
      });

      // THESE LINES WERE MISSING:
      field.appendChild(sel);
      if (c != null && c < 0.55) field.insertAdjacentHTML('beforeend', '<p class="hint low-hint">Not very sure about this one. Please double-check.</p>');
      grid.appendChild(field);
    });

    paintDetect();
    setPicker(conf.garment_type != null && conf.garment_type < 0.7);   // open by itself when the AI is unsure
    applyRelevance();
  }

  /* Skirts, jeans and pants have no neckline or sleeves: grey those fields out */
  function applyRelevance() {
    const bottom = isBottom();
    NA_KEYS.forEach((k) => {
      const f = $('#rf-' + k); if (!f) return;
      f.classList.toggle('is-na', bottom);
      $('select', f).disabled = bottom;
      let note = $('.na-note', f);
      if (bottom && !note) { f.insertAdjacentHTML('beforeend', `<p class="hint na-note">Not needed for ${labelFor('garment_type', state.spec.garment_type).toLowerCase()}.</p>`); }
      if (!bottom && note) note.remove();
      const low = $('.low-hint', f); if (low) low.hidden = bottom;
    });
    syncShoulderBand(); syncSleeveField();
  }

  function syncShoulderBand() {
    const show = !isBottom() && state.spec.neckline === 'off_shoulder';
    const wrap = $('#shoulder-band-wrap');
    if (show) wrap.hidden = false;
    else { wrap.hidden = true; state.spec.shoulder_band = false; $('#shoulder-band').checked = false; }
  }
  $('#shoulder-band').addEventListener('change', (e) => { state.spec.shoulder_band = e.target.checked; });
  $('#review-next').addEventListener('click', () => { completeStep(2); buildMeasureForm(); goToStep(3); });

  /* ---------------------------------------------------------------- 7 measurements */
  const MEASURES = [
    { key: 'bust',     label: 'Bust',            def: 91, min: 60, max: 160, hint: 'Around the fullest part of your chest.' },
    { key: 'waist',    label: 'Waist',           def: 71, min: 45, max: 150, hint: 'Around your natural waist.' },
    { key: 'hips',     label: 'Hips',            def: 97, min: 70, max: 170, hint: 'Around the fullest part of your hips.' },
    { key: 'shoulder', label: 'Shoulder width',  def: 38, min: 28, max: 60,  hint: 'Across the back, shoulder point to point.' },
    { key: 'length',   label: 'Garment length',  def: 60, min: 20, max: 160, hint: 'From the top of the shoulder down to the hem.' },
    { key: 'sleeve',   label: 'Sleeve length',   def: 58, min: 5,  max: 80,  hint: 'Shoulder point to wrist. Skipped for sleeveless.' },
  ];
  const cmToIn = (v) => Math.round((v / 2.54) * 10) / 10;
  const inToCm = (v) => Math.round(v * 2.54 * 10) / 10;
  const measureValuesCm = {};      // canonical store, always in cm

    function buildMeasureForm() {
    const grid = $('#measure-grid');
    if (grid.childElementCount) { syncSleeveField(); return; }  // keep user input if already built

    // 1. Create the inputs first
    MEASURES.forEach((m) => {
      measureValuesCm[m.key] = m.def;
      const f = document.createElement('div'); f.className = 'field'; f.id = 'mf-' + m.key;
      f.innerHTML = `
        <label for="m-${m.key}">${m.label}</label>
        <div class="input-unit"><input type="number" id="m-${m.key}" inputmode="decimal" step="0.5" aria-describedby="mh-${m.key}"><span class="unit">cm</span></div>
        <p class="hint" id="mh-${m.key}">${m.hint}</p>`;
      grid.appendChild(f);
      const input = $('input', f);
      input.addEventListener('input', () => validateOne(m, true));
      input.addEventListener('blur', () => validateOne(m, true));
    });

    // 2. Fill them with default values
    paintMeasureInputs();
    syncSleeveField();

    // 3. NOW apply the chosen length (since the inputs exist now)
    if (state.chosenLength) {
        const lenInput = document.getElementById('m-length');
        if (lenInput) {
            let newLen = 60;
            if (state.chosenLength.includes('floor')) newLen = 145;
            else if (state.chosenLength.includes('maxi')) newLen = 120;
            else if (state.chosenLength.includes('midi')) newLen = 85;
            else if (state.chosenLength.includes('mini') || state.chosenLength.includes('crop')) newLen = 45;
            else if (state.chosenLength.includes('hip')) newLen = 40;

            lenInput.value = newLen;
            measureValuesCm['length'] = newLen;
        }
    }
  }


  function paintMeasureInputs() {
    const inch = state.unit === 'in';
    MEASURES.forEach((m) => {
      const input = $('#m-' + m.key);
      input.value = inch ? cmToIn(measureValuesCm[m.key]) : measureValuesCm[m.key];
      input.step = inch ? 0.25 : 0.5;
      $('.unit', input.parentElement).textContent = state.unit;
      clearFieldError(m);
    });
  }

  function syncSleeveField() {
    const f = $('#mf-sleeve'); if (!f) return;
    const none = state.spec.sleeve_length === 'sleeveless' || isBottom();
    const input = $('#m-sleeve'); input.disabled = none;
    f.style.opacity = none ? .55 : 1;
    $('.hint', f).textContent = none ? 'Not needed for this garment.' : MEASURES[5].hint;
    if (none) clearFieldError(MEASURES[5]);
  }

  function clearFieldError(m) {
    const f = $('#mf-' + m.key); const e = $('.field-error', f); if (e) e.remove();
    $('#m-' + m.key).removeAttribute('aria-invalid');
  }

  function validateOne(m, live) {
    const input = $('#m-' + m.key); if (input.disabled) return true;
    const inch = state.unit === 'in';
    const raw = input.value.trim(); const v = parseFloat(raw);
    const lo = inch ? cmToIn(m.min) : m.min, hi = inch ? cmToIn(m.max) : m.max;
    clearFieldError(m);
    let msg = '';
    if (raw === '' || Number.isNaN(v)) msg = `Please enter your ${m.label.toLowerCase()}.`;
    else if (v < lo || v > hi) msg = `${m.label} should be between ${lo} and ${hi} ${state.unit}.`;
    if (msg) {
      input.setAttribute('aria-invalid', 'true');
      const p = document.createElement('p'); p.className = 'field-error'; p.setAttribute('role', 'alert'); p.textContent = msg;
      $('#mf-' + m.key).appendChild(p);
      return false;
    }
    measureValuesCm[m.key] = inch ? inToCm(v) : v;
    return true;
  }

  $$('#unit-toggle .seg-btn').forEach((b) => b.addEventListener('click', () => {
    if (b.dataset.unit === state.unit) return;
    // measureValuesCm is already kept up to date on every valid keystroke, so just re-display (no rounding drift)
    state.unit = b.dataset.unit;
    $$('#unit-toggle .seg-btn').forEach((x) => { const on = x === b; x.classList.toggle('is-active', on); x.setAttribute('aria-pressed', on); });
    moveThumb($('#unit-toggle'));
    paintMeasureInputs();
  }));

  $('#measure-next').addEventListener('click', () => {
    let first = null;
    MEASURES.forEach((m) => { if (!validateOne(m, false) && !first) first = m; });
    if (first) { $('#m-' + first.key).focus(); toast('A couple of measurements need a quick look.'); return; }
    // Gentle sanity hint (not blocking)
    if (measureValuesCm.hips < measureValuesCm.waist) toast('Heads up: hips are smaller than waist. Double-check if that’s right.');
    completeStep(3); renderSummary(); goToStep(4);
  });

  /* ---------------------------------------------------------------- 8 generate */
  function renderSummary() {
    const s = state.spec, box = $('#summary-chips'); box.innerHTML = '';
    const add = (t, v) => { const c = document.createElement('span'); c.className = 'chip'; c.innerHTML = `${t} <small>${v}</small>`; box.appendChild(c); };
    add('Garment', labelFor('garment_type', s.garment_type));
    add('Silhouette', labelFor('silhouette', s.silhouette));
    if (!isBottom()) { add('Neckline', labelFor('neckline', s.neckline)); add('Sleeve', labelFor('sleeve_length', s.sleeve_length)); }
    add('Length', labelFor('length', s.length));
    if (s.shoulder_band) add('Shoulder band', 'Yes');
    add('Bust / Waist / Hips', ['bust', 'waist', 'hips'].map((k) => fmtMeasure(measureValuesCm[k])).join(' / ') + ' ' + state.unit);
  }
  const fmtMeasure = (cm) => (state.unit === 'in' ? cmToIn(cm) : cm);

   function buildPayload(method) {
    const m = {};
    MEASURES.forEach((x) => { m[x.key] = measureValuesCm[x.key]; });

    m.back_length = 40;
    m.neck_depth = 8;
    if (isBottom()) m.sleeve = 0;

    // READ DIRECTLY FROM THE DROPDOWNS ON THE SCREEN
    const getVal = (id) => {
        const el = document.getElementById('sel-' + id);
        return el ? el.value : 'round';
    };

    const rawSpec = {
        garment_type: document.querySelector('.tile[aria-checked="true"]')?.dataset.value || 'dress',
        silhouette: getVal('silhouette'),
        neckline: getVal('neckline'),
        sleeve_length: getVal('sleeve_length'),
        waistline: getVal('waistline'),
        length: getVal('length')
    };

    return {
        spec: rawSpec,
        measurements_cm: m,
        method
    };
  }



    async function runGenerate(method, { fromRedraft = false } = {}) {
    const box = $('.generate-box'), btn = $('#generate-btn'), errBox = $('#gen-error');
    errBox.hidden = true;
    const redraftBtn = $('#redraft-btn');
    if (fromRedraft) setLoading(redraftBtn, true); else { setLoading(btn, true); box.classList.add('busy'); $('#gen-loading').hidden = false; }

    try {
      // 1. Read the values DIRECTLY from the screen
      const selectedTile = document.querySelector('.tile[aria-checked="true"]');
      const garmentVal = selectedTile ? selectedTile.dataset.value : 'dress';

      const lengthSelect = $('#sel-length');
      const lengthVal = lengthSelect ? lengthSelect.value : 'knee';

      const necklineSelect = $('#sel-neckline');
      const neckVal = necklineSelect ? necklineSelect.value : 'round';

      const silhouetteSelect = $('#sel-silhouette');
      const silVal = silhouetteSelect ? silhouetteSelect.value : 'fitted';

      const sleeveSelect = $('#sel-sleeve_length');
      const sleeveVal = sleeveSelect ? sleeveSelect.value : 'sleeveless';

      const waistSelect = $('#sel-waistline');
      const waistVal = waistSelect ? waistSelect.value : 'natural_waist';

      // 2. Build the payload MANUALLY so there is no confusion
      const m = {};
      MEASURES.forEach((x) => { m[x.key] = measureValuesCm[x.key]; });

      const payload = {
          spec: {
              garment_type: garmentVal,
              silhouette: silVal,
              neckline: neckVal,
              sleeve_length: sleeveVal,
              waistline: waistVal,
              length: lengthVal
          },
          measurements_cm: m,
          method: method
      };

      // 3. Send directly to Flask (Bypassing API.generatePattern)
      const response = await fetch('http://127.0.0.1:5000/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
      });

      const data = await response.json();
      if (data.message) throw new Error(data.message);

      state.svgText = sanitizeSVG(data.svg);
      completeStep(4); completeStep(5);
      const wasHidden = $('#step-5').hidden;
      goToStep(5);
      renderPattern();
      celebrate(!fromRedraft || wasHidden);
    } catch (ex) {
      if (fromRedraft) toast(ex.message || 'Could not re-draft the pattern.');
      else { $('#gen-error-msg').textContent = ex.message || 'Something went wrong. Please try again.'; errBox.hidden = false; }
    } finally {
      setLoading(btn, false); setLoading(redraftBtn, false);
      box.classList.remove('busy'); $('#gen-loading').hidden = true;
    }
  }
  $('#generate-btn').addEventListener('click', () => runGenerate($('#method-select').value || 'aldrich'));

  /* ---------------------------------------------------------------- 9 results */
  const viewer = $('#viewer'), canvas = $('#viewer-canvas'), shell = $('#viewer-shell');
  let baseVB = { w: 100, h: 100 };

  function buildMethodSelect() {
    const sel = $('#method-select');
    if (!sel.options.length) API.METHODS.forEach(([v, l]) => sel.add(new Option(l, v)));
    $('#method-wrap').hidden = !API.CONFIG.FEATURES.methodSelector;
  }

  /* Real-world size from the SVG's own width/height (mm, cm, in, px, pt) */
  function physicalSize(text) {
    const root = new DOMParser().parseFromString(text, 'image/svg+xml').documentElement;
    const toMM = (v) => {
      const m = /^\s*([\d.]+)\s*(mm|cm|in|px|pt)?\s*$/.exec(v || ''); if (!m) return null;
      const n = parseFloat(m[1]), u = m[2] || 'px';
      return { mm: n, cm: n * 10, in: n * 25.4, px: (n * 25.4) / 96, pt: (n * 25.4) / 72 }[u];
    };
    return { w: toMM(root.getAttribute('width')), h: toMM(root.getAttribute('height')) };
  }
  function paperFor(w, h) {
    const long = Math.max(w, h) + 10, short = Math.min(w, h) + 10;   // 5 mm margin each side
    const papers = [['A4', 297, 210], ['A3', 420, 297], ['A2', 594, 420], ['A1', 841, 594], ['A0', 1189, 841]];
    const hit = papers.find(([, L, S]) => L >= long && S >= short);
    return hit ? `fits on ${hit[0]}` : 'bigger than A0: print in tiles';
  }
  function paintSizeChip() {
    const { w, h } = physicalSize(state.svgText);
    $('#size-chip').textContent = w && h ? `Real size · ${Math.round(w)} × ${Math.round(h)} mm · ${paperFor(w, h)}` : 'Real size · see SVG';
  }

  function renderPattern() {
    buildMethodSelect();
    canvas.innerHTML = state.svgText;
    const svg = $('svg', canvas);
    const vb = (svg.getAttribute('viewBox') || '').split(/[\s,]+/).map(Number);
    baseVB = vb.length === 4 && vb[2] > 0 ? { w: vb[2], h: vb[3] } : { w: svg.clientWidth || 800, h: svg.clientHeight || 400 };
    svg.removeAttribute('height');
    svg.dataset.physW = svg.getAttribute('width') || '';   // keep the real-world width for "Actual size"
    state.zoom = { mode: 'fit', factor: 1 };
    paintSizeChip();
    applyZoom();
    viewer.scrollTo(0, 0);
  }

  // "Fit" = whole pattern visible at once (limited by viewer width AND height)
  function viewerMaxH() {
    if (document.fullscreenElement === shell) return window.innerHeight - 28;
    return Math.min(window.innerHeight * (window.innerWidth <= 600 ? 0.66 : 0.82), 880);
  }
  function fitWidth() {
    const byW = viewer.clientWidth - 40;
    const byH = (viewerMaxH() - 40) * (baseVB.w / baseVB.h);
    return Math.max(280, Math.min(byW, byH));
  }
  function applyZoom() {
    const svg = $('svg', canvas); if (!svg) return;
    if (state.zoom.mode === 'actual' && svg.dataset.physW) svg.style.width = svg.dataset.physW;
    else svg.style.width = Math.round(fitWidth() * state.zoom.factor) + 'px';
    svg.removeAttribute('width');
  }
  function zoomBy(mult) {
    if (state.zoom.mode === 'actual') { state.zoom.factor = $('svg', canvas).getBoundingClientRect().width / fitWidth(); state.zoom.mode = 'fit'; }
    state.zoom.factor = Math.min(8, Math.max(0.4, state.zoom.factor * mult));
    applyZoom();
  }
  $('#zoom-in').addEventListener('click', () => zoomBy(1.25));
  $('#zoom-out').addEventListener('click', () => zoomBy(0.8));
  $('#zoom-fit').addEventListener('click', () => { state.zoom = { mode: 'fit', factor: 1 }; applyZoom(); viewer.scrollTo({ left: 0, top: 0, behavior: 'smooth' }); });
  $('#zoom-actual').addEventListener('click', () => { state.zoom.mode = 'actual'; applyZoom(); toast('Showing real-world size (at your screen’s 96 dpi).'); });
  window.addEventListener('resize', () => { if (!$('#step-5').hidden) applyZoom(); });

  $('#fullscreen-btn').addEventListener('click', () => {
    if (document.fullscreenElement) document.exitFullscreen();
    else if (shell.requestFullscreen) shell.requestFullscreen().catch(() => toast('Full screen isn’t available here.'));
    else toast('Full screen isn’t available in this browser.');
  });
  document.addEventListener('fullscreenchange', () => setTimeout(applyZoom, 60));

  // Drag-to-pan
  let pan = null;
  viewer.addEventListener('pointerdown', (e) => { if (e.pointerType === 'mouse' && e.button === 0) { pan = { x: e.clientX, y: e.clientY, l: viewer.scrollLeft, t: viewer.scrollTop }; viewer.setPointerCapture(e.pointerId); } });
  viewer.addEventListener('pointermove', (e) => { if (pan) { viewer.scrollLeft = pan.l - (e.clientX - pan.x); viewer.scrollTop = pan.t - (e.clientY - pan.y); } });
  ['pointerup', 'pointercancel'].forEach((ev) => viewer.addEventListener(ev, () => { pan = null; }));

  /* The saved/printed copy always uses the ORIGINAL svg text (real-world size intact),
     never the on-screen copy whose width was changed for zooming. */
  function cleanSVGText() {
    let txt = state.svgText;
    if (!/xmlns=/.test(txt.slice(0, 300))) txt = txt.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"');
    return txt;
  }

  $('#download-btn').addEventListener('click', () => {
    if (!state.svgText) return;
    const blob = new Blob([cleanSVGText()], { type: 'image/svg+xml' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `pattern-pilot-${(state.spec.garment_type || 'pattern')}-${new Date().toISOString().slice(0, 10)}.svg`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    toast('Downloaded! Remember to print at 100% scale ✂️');
  });

  $('#print-btn').addEventListener('click', () => {
    if (!state.svgText) return;
    const { w } = physicalSize(state.svgText);
    const frame = document.createElement('iframe');
    frame.setAttribute('aria-hidden', 'true'); frame.title = 'Print pattern';
    frame.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;visibility:hidden';
    document.body.appendChild(frame);
    const doc = frame.contentDocument;
    doc.open();
    doc.write(`<!doctype html><html><head><meta charset="utf-8"><title>Pattern Pilot pattern</title>
      <style>@page{margin:5mm}html,body{margin:0;background:#fff}svg{display:block;height:auto;width:${w ? w + 'mm' : '100%'}}</style></head>
      <body>${cleanSVGText()}</body></html>`);
    doc.close();
    setTimeout(() => {
      try { frame.contentWindow.focus(); frame.contentWindow.print(); } catch (e) { toast('Couldn’t open the print dialog. Download the SVG and print it from there.'); }
      setTimeout(() => frame.remove(), 4000);
    }, 350);
    toast('In the print dialog, set Scale to 100%.');
  });

  $('#redraft-btn').addEventListener('click', () => runGenerate($('#method-select').value, { fromRedraft: true }));

  function celebrate(full) {
    const banner = $('#success-banner');
    $('#success-msg').textContent = `Your ${labelFor('garment_type', state.spec.garment_type).toLowerCase()} pieces are drafted and ready to print.`;
    banner.classList.remove('celebrate'); void banner.offsetWidth;
    if (reduceMotion) return;
    banner.classList.add('celebrate');
    if (!full) return;
    const box = $('#sparkles'); box.innerHTML = '';
    for (let i = 0; i < 16; i++) {
      const s = document.createElement('i'); s.className = 'spark';
      const ang = (Math.PI * 2 * i) / 16, dist = 50 + Math.random() * 50;
      s.style.setProperty('--dx', Math.cos(ang) * dist + 'px'); s.style.setProperty('--dy', Math.sin(ang) * dist + 'px');
      s.style.animationDelay = Math.random() * 0.15 + 's';
      box.appendChild(s);
    }
    setTimeout(() => (box.innerHTML = ''), 1600);
  }

  /* ---------------------------------------------------------------- boot */
  initMotion();
  setAuthMode('login');
  window.addEventListener('load', () => moveThumb($('#auth-tabs')));
  window.addEventListener('resize', () => { moveThumb($('#auth-tabs')); if (!viewApp.hidden) moveThumb($('#unit-toggle')); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => moveThumb($('#auth-tabs')));

  // Restore a previous session (demo only: stores just the display name)
  try {
    const saved = JSON.parse(safeStore('get', 'pp_user') || 'null');
    if (saved && saved.name) { state.user = saved; startApp(); }
  } catch (e) { /* ignore */ }
  // Seg thumb for unit toggle needs the section to be visible once
  const unitObs = new MutationObserver(() => { if (!$('#step-3').hidden) setTimeout(() => moveThumb($('#unit-toggle')), 50); });
  unitObs.observe($('#step-3'), { attributes: true, attributeFilter: ['hidden'] });
})();
