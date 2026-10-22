/* Small, accessible actions for student-owned public portfolios. */
(() => {
  const status = document.getElementById('resume-action-status');
  const announce = message => {
    if (status) status.textContent = message;
  };
  const share = document.getElementById('resume-share');
  share?.addEventListener('click', async () => {
    const url = share.dataset.shareUrl || window.location.href;
    if (navigator.share) {
      try {
        await navigator.share({ title: document.title, url });
        announce('Portfolio shared.');
        return;
      } catch (error) {
        if (error?.name === 'AbortError') return;
      }
    }
    try {
      await navigator.clipboard.writeText(url);
      announce('Portfolio link copied.');
    } catch {
      announce('Copy the portfolio link from your browser address bar.');
    }
  });
  document.getElementById('resume-print')?.addEventListener('click', () => window.print());
})();
