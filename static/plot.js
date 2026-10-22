(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const state = { lcp: null, inp: null, cls: 0, clsWindowStart: null, clsLastShift: null, clsCurrentWindow: 0 };
  const bytes = (value) => value < 1024 ? `${value} B` : value < 1024 * 1024 ? `${(value / 1024).toFixed(1)} KB` : `${(value / 1024 / 1024).toFixed(2)} MB`;
  const ms = (value) => value == null ? '—' : value < 1000 ? `${Math.round(value)} ms` : `${(value / 1000).toFixed(2)} s`;

  function showMetric(key, value, verdict, label) {
    $( `metric-${key}` ).textContent = value;
    $(`state-${key}`).textContent = label;
    const card = document.querySelector(`[data-metric="${key}"]`);
    if (card) card.dataset.state = verdict || '';
  }

  function observe(type, callback, options = { buffered: true }) {
    if (!('PerformanceObserver' in window) || !PerformanceObserver.supportedEntryTypes?.includes(type)) return false;
    try { const observer = new PerformanceObserver(callback); observer.observe({ type, ...options }); return true; }
    catch { return false; }
  }

  const hasLcp = observe('largest-contentful-paint', (list) => {
    const entries = list.getEntries();
    if (entries.length) state.lcp = entries[entries.length - 1].startTime;
    showMetric('lcp', ms(state.lcp), state.lcp == null ? '' : state.lcp <= 2500 ? 'good' : state.lcp <= 4000 ? 'attention' : 'poor', state.lcp == null ? 'Good target ≤2.5 s · waiting' : state.lcp <= 2500 ? 'Good target ≤2.5 s · good sample' : state.lcp <= 4000 ? 'Good target ≤2.5 s · needs improvement' : 'Good target ≤2.5 s · slow sample');
  });
  if (!hasLcp) showMetric('lcp', 'Not supported', '', 'Browser does not expose LCP');

  const hasCls = observe('layout-shift', (list) => {
    for (const entry of list.getEntries()) {
      if (entry.hadRecentInput) continue;
      const newWindow = state.clsWindowStart === null
        || entry.startTime - state.clsLastShift >= 1000
        || entry.startTime - state.clsWindowStart >= 5000;
      if (newWindow) {
        state.clsWindowStart = entry.startTime;
        state.clsCurrentWindow = 0;
      }
      state.clsCurrentWindow += entry.value;
      state.clsLastShift = entry.startTime;
      state.cls = Math.max(state.cls, state.clsCurrentWindow);
    }
    const verdict = state.cls <= 0.1 ? 'good' : state.cls <= 0.25 ? 'attention' : 'poor';
    showMetric('cls', state.cls.toFixed(3), verdict, verdict === 'good' ? 'Target ≤0.1 · stable sample' : verdict === 'attention' ? 'Target ≤0.1 · some movement' : 'Target ≤0.1 · unexpected movement');
  });
  if (!hasCls) showMetric('cls', 'Not supported', '', 'Browser does not expose CLS');

  const hasInp = observe('event', (list) => {
    for (const entry of list.getEntries()) {
      if (entry.interactionId > 0) state.inp = Math.max(state.inp || 0, entry.duration);
    }
    if (state.inp != null) {
      const verdict = state.inp <= 200 ? 'good' : state.inp <= 500 ? 'attention' : 'poor';
      showMetric('inp', ms(state.inp), verdict, verdict === 'good' ? 'Target ≤200 ms · good sample' : verdict === 'attention' ? 'Target ≤200 ms · some delay' : 'Target ≤200 ms · needs work');
    }
  }, { buffered: true, durationThreshold: 40 });
  if (!hasInp) showMetric('inp', 'Not supported', '', 'Browser does not expose INP');

  function summarizeLoad() {
    const navigation = performance.getEntriesByType('navigation')[0];
    if (navigation) {
      const ttfb = navigation.responseStart - navigation.startTime;
      showMetric('ttfb', ms(ttfb), ttfb <= 800 ? 'good' : ttfb <= 1800 ? 'attention' : 'poor', '800 ms reference · one response');
    }
    const groups = { Scripts: 0, Styles: 0, Images: 0, Fonts: 0, Other: 0 };
    for (const entry of performance.getEntriesByType('resource')) {
      const name = entry.name.split('?')[0].toLowerCase();
      const group = /\.(m?js)$/.test(name) ? 'Scripts' : /\.css$/.test(name) ? 'Styles' : /\.(png|jpe?g|webp|gif|svg|avif)$/.test(name) ? 'Images' : /\.(woff2?|ttf|otf)$/.test(name) ? 'Fonts' : 'Other';
      // transferSize is the browser-reported network transfer. Encoded body
      // size is not a valid fallback because cached resources transfer 0 bytes.
      groups[group] += Math.max(0, entry.transferSize || 0);
    }
    const total = Object.values(groups).reduce((sum, n) => sum + n, 0);
    $('resource-total').textContent = bytes(total);
    const max = Math.max(1, ...Object.values(groups));
    $('resource-bars').replaceChildren(...Object.entries(groups).map(([name, size]) => {
      const row = document.createElement('div'); row.className = 'resource-row';
      const label = document.createElement('label'); label.textContent = name;
      const bar = document.createElement('progress'); bar.max = max; bar.value = size; bar.setAttribute('aria-label', `${name}: ${bytes(size)}`);
      const value = document.createElement('output'); value.textContent = bytes(size);
      row.append(label, bar, value); return row;
    }));
    $('sample-time').textContent = `Sampled ${new Date().toLocaleTimeString()} · ${innerWidth} px wide`;
  }

  async function checkHealth() {
    const button = $('check-health'); button.disabled = true;
    $('health-status').textContent = 'Checking'; $('health-detail').textContent = 'Requesting the read-only health endpoint…';
    const started = performance.now();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch('/healthz', { cache: 'no-store', credentials: 'omit', signal: controller.signal, headers: { Accept: 'application/json' } });
      const elapsed = performance.now() - started;
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (data.ok !== true) throw new Error('Health response was not ready');
      $('health-dot').className = 'dot up'; $('health-status').textContent = 'Healthy'; $('health-latency').textContent = ms(elapsed);
      $('health-detail').textContent = 'The app returned a successful readiness response. This one check is not an uptime guarantee.';
    } catch (error) {
      $('health-dot').className = 'dot down'; $('health-status').textContent = 'Unavailable'; $('health-latency').textContent = '—';
      const reason=error.name==='AbortError'?'timed out after 8 seconds':String(error.message || 'network error').slice(0, 80);
      $('health-detail').textContent = `The health check did not complete (${reason}).`;
    } finally { clearTimeout(timeout); button.disabled = false; }
  }

  summarizeLoad();
  requestAnimationFrame(summarizeLoad);
  window.addEventListener('load', summarizeLoad, { once: true });
  $('check-health').addEventListener('click', checkHealth);
  checkHealth();
})();
