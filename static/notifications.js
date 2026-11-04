'use strict';
// A single request at a time; quietly refresh closed inboxes every 30 seconds.
(() => {
  const container = document.createElement('aside');
  container.id = 'ncet-alerts';
  container.hidden = true;
  container.innerHTML = '<button id="alert-toggle" type="button" aria-expanded="false" aria-controls="alert-list">Notifications <span id="alert-count"></span></button><section id="alert-list" role="region" aria-label="In-app notifications" hidden><header><div><h2>Notifications</h2><p id="alert-summary" role="status" aria-live="polite"></p></div><button id="alert-close" type="button" aria-label="Close notifications">×</button></header><div class="alert-tools"><button id="alert-read-all" type="button">Mark all as read</button><button id="alert-retry" type="button">Refresh</button></div><div id="alert-items">Loading…</div></section>';
  document.body.append(container);
  const toggle = container.querySelector('#alert-toggle'), panel = container.querySelector('#alert-list');
  const list = container.querySelector('#alert-items'), badge = container.querySelector('#alert-count');
  const summary = container.querySelector('#alert-summary'), markAll = container.querySelector('#alert-read-all');
  let csrf = '', timer = null, request = null, signature = '', generation = 0, failures = 0;
  let unread = 0, opener = null, lastRefresh = 0;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const localLink = value => typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') && !value.includes('\\') ? value : '/app';
  function updateBadge() {
    badge.textContent = unread ? `(${unread} new)` : '';
    summary.textContent = unread ? `${unread} unread updates` : 'You’re all caught up';
    markAll.disabled = unread === 0;
    document.querySelectorAll('[data-notification-toggle]').forEach(button => {
      button.setAttribute('aria-expanded', String(!panel.hidden));
      button.setAttribute('aria-controls', 'alert-list');
      button.setAttribute('aria-label', unread ? `Notifications, ${unread} unread` : 'Notifications');
      button.classList.toggle('has-unread', unread > 0);
    });
  }
  function schedule() {
    clearTimeout(timer);
    if (document.hidden) return;
    const interval = failures ? Math.min(120000, 15000 * 2 ** Math.min(failures, 3)) : !csrf ? 60000 : panel.hidden ? 30000 : 10000;
    timer = setTimeout(refresh, interval);
  }
  function open(show, source) {
    panel.hidden = !show;
    toggle.setAttribute('aria-expanded', String(show));
    if (show) { opener = source || toggle; container.hidden = false; refresh(); container.querySelector('#alert-close').focus(); }
    else opener?.focus?.();
    updateBadge(); schedule();
  }
  async function refresh(force = false) {
    if (document.hidden) return;
    if (request) return request;
    if (!force && Date.now() - lastRefresh < 1500) { schedule(); return; }
    const currentGeneration = generation;
    request = (async () => {
      try {
        if (!csrf) {
          const auth = await fetch('/api/auth/me', { credentials:'same-origin', cache:'no-store' });
          if (currentGeneration !== generation) return;
          if (!auth.ok) { container.hidden = true; return; }
          csrf = (await auth.json()).csrf || '';
          if (!csrf) throw Error('Session unavailable');
        }
        const response = await fetch('/api/alerts/inbox', { credentials:'same-origin', cache:'no-store' });
        if (currentGeneration !== generation) return;
        if ([401,403].includes(response.status)) { csrf = ''; container.hidden = true; panel.hidden = true; signature = ''; list.replaceChildren(); return; }
        if (!response.ok) throw Error('Inbox unavailable');
        const result = await response.json();
        if (currentGeneration !== generation) return;
        unread = Number(result.unread) || 0; failures = 0; container.hidden = false;
        const next = JSON.stringify(result.items);
        if (next !== signature) {
          const focused = document.activeElement?.dataset?.notice;
          list.innerHTML = result.items.length ? result.items.map(n => `<a class="alert-entry ${n.seen ? '' : 'alert-unread'}" href="${esc(localLink(n.link))}" data-notice="${esc(n.id)}"><span>${esc(n.category)}</span><strong>${esc(n.text)}</strong><time datetime="${esc(n.at)}">${esc(new Date(n.at).toLocaleString())}</time></a>`).join('') : '<div class="alert-empty"><strong>No updates yet</strong><p>Assignments, requests and replies will appear here.</p></div>';
          signature = next;
          if (focused) [...list.querySelectorAll('[data-notice]')].find(n => n.dataset.notice === focused)?.focus();
        }
        updateBadge();
      } catch (_) { failures++; if (!container.hidden) summary.textContent = 'Connection interrupted. Your updates are kept here.'; }
      finally { lastRefresh = Date.now(); request = null; schedule(); }
    })();
    return request;
  }
  document.addEventListener('click', event => {
    const source = event.target.closest('[data-notification-toggle],#alert-toggle');
    if (source) { open(panel.hidden, source); return; }
    if (!panel.hidden && !container.contains(event.target)) open(false);
  });
  container.querySelector('#alert-close').addEventListener('click', () => open(false));
  container.querySelector('#alert-retry').addEventListener('click', () => refresh(true));
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !panel.hidden) open(false); });
  markAll.addEventListener('click', async () => {
    markAll.disabled = true;
    try {
      const response = await fetch('/api/alerts/read-all', { method:'POST', credentials:'same-origin', headers:{'X-CSRF-Token':csrf} });
      if (!response.ok) throw Error('Unable to mark notifications');
      await refresh(true); window.dispatchEvent(new Event('ncet:notifications-read'));
    } catch (_) { summary.textContent = 'Could not mark updates as read. Please retry.'; markAll.disabled = false; }
  });
  container.addEventListener('click', async event => {
    const link = event.target.closest('[data-notice]');
    if (!link || !csrf) return;
    const normal = event.button === 0 && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey;
    if (normal) event.preventDefault();
    try { await fetch(`/api/alerts/${encodeURIComponent(link.dataset.notice)}/read`, { method:'POST', credentials:'same-origin', keepalive:true, headers:{'X-CSRF-Token':csrf} }); }
    finally { if (normal) location.assign(link.getAttribute('href')); }
  });
  window.addEventListener('ncet:session-changed', async () => {
    generation++; csrf = ''; signature = ''; unread = 0; container.hidden = true; panel.hidden = true; list.replaceChildren();
    if (request) await request;
    refresh(true);
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) clearTimeout(timer); else refresh(true); });
  window.addEventListener('ncet:notifications-refresh', () => refresh(true));
  window.addEventListener('focus', () => refresh());
  const app = document.getElementById('app');
  if (app) new MutationObserver(updateBadge).observe(app, { childList:true, subtree:true });
  refresh();
})();
