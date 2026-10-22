'use strict';
// Poll the authenticated inbox every 1.5 seconds while the page is visible.
(() => {
  const container = document.createElement('aside');
  container.id = 'ncet-alerts';
  container.hidden = true;
  container.innerHTML = '<button id="alert-toggle" type="button" aria-expanded="false" aria-controls="alert-list">Notifications <span id="alert-count"></span></button><section id="alert-list" role="region" aria-label="In-app notifications" hidden><h2>Notifications</h2><div id="alert-items">Loading…</div><button id="alert-close" type="button">Close</button></section>';
  document.body.append(container);

  const toggle = container.querySelector('#alert-toggle');
  const panel = container.querySelector('#alert-list');
  const list = container.querySelector('#alert-items');
  const badge = container.querySelector('#alert-count');
  const signedOutInterval = 12000;
  const signedInInterval = 1500;
  let csrf = '';
  let running = false;
  let pollTimer = null;
  let pollInterval = 0;

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[character]);

  function open(show) {
    panel.hidden = !show;
    toggle.setAttribute('aria-expanded', String(show));
  }

  function schedule(interval) {
    if (document.visibilityState === 'hidden') interval = 0;
    if (pollInterval === interval) return;
    if (pollTimer !== null) clearInterval(pollTimer);
    pollTimer = null;
    pollInterval = interval;
    if (interval) pollTimer = setInterval(refresh, interval);
  }

  async function refresh() {
    if (running || document.visibilityState === 'hidden') return;
    running = true;
    try {
      if (!csrf) {
        const auth = await fetch('/api/auth/me', { credentials: 'same-origin', cache: 'no-store' });
        if (!auth.ok) {
          container.hidden = true;
          schedule(signedOutInterval);
          return;
        }
        const session = await auth.json();
        csrf = session.csrf || '';
        if (!csrf) throw Error('The signed-in session did not provide a CSRF token');
        schedule(signedInInterval);
      }

      const response = await fetch('/api/alerts/inbox', { credentials: 'same-origin', cache: 'no-store' });
      if (response.status === 401 || response.status === 403) {
        csrf = '';
        container.hidden = true;
        schedule(signedOutInterval);
        return;
      }
      if (!response.ok) throw Error('Unable to refresh notifications');
      const result = await response.json();
      container.hidden = false;
      badge.textContent = result.unread ? `(${result.unread} new)` : '';
      list.innerHTML = result.items.length
        ? result.items.map((notice) => `<a class="alert-entry ${notice.seen ? '' : 'alert-unread'}" href="${esc(notice.link)}" data-notice="${esc(notice.id)}"><span>${esc(notice.category)}</span><strong>${esc(notice.text)}</strong><small>${esc(new Date(notice.at).toLocaleString())}</small></a>`).join('')
        : '<p>No new activity yet.</p>';
      schedule(signedInInterval);
    } catch (error) {
      schedule(signedOutInterval);
      if (!container.hidden) list.textContent = 'Notifications could not be refreshed.';
    } finally {
      running = false;
    }
  }

  toggle.addEventListener('click', () => {
    open(panel.hidden);
    if (!panel.hidden) refresh();
  });
  container.querySelector('#alert-close').addEventListener('click', () => open(false));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') open(false);
  });
  container.addEventListener('click', (event) => {
    const link = event.target.closest('[data-notice]');
    if (!link || !csrf) return;
    fetch(`/api/alerts/${encodeURIComponent(link.dataset.notice)}/read`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRF-Token': csrf }
    }).catch(() => {});
  });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') schedule(0);
    else {
      schedule(csrf ? signedInInterval : signedOutInterval);
      refresh();
    }
  });
  window.addEventListener('ncet:notifications-refresh', refresh);
  window.addEventListener('focus', refresh);
  schedule(signedOutInterval);
  refresh();
})();
