// Apex — dev sessions list + launch modal.

(function(){

  function elapsedSince(iso){
    if (!iso) return 0;
    const t = new Date(iso.includes('Z') || iso.includes('+') ? iso : iso + 'Z');
    return Math.max(0, (Date.now() - t.getTime()) / 1000);
  }

  function fmtDuration(seconds) {
    seconds = Math.max(0, Math.floor(seconds));
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (h) return `${h}h ${String(m).padStart(2,'0')}m`;
    return `${m}m`;
  }

  function renderSessions(sessions){
    const targets = document.querySelectorAll('[data-role="sess-list"]');
    const html = sessions.length
      ? sessions.map(s => `
        <div class="sess-row" data-id="${s.id}">
          <div class="sess-dot on"></div>
          <div style="flex:1">
            <div class="sess-name">${R.escape(s.user)}</div>
            <div class="sess-img">${R.escape(s.image)} · ${fmtDuration(elapsedSince(s.created_at))}</div>
          </div>
          <div class="sess-port">:${s.port}</div>
          <a class="open-ico" href="http://localhost:${s.port}" target="_blank" rel="noopener" title="Open VSCode">↗</a>
          <button class="row-btn danger" data-stop="${s.id}" title="Stop session">✕</button>
        </div>
      `).join('')
      : '<div class="empty-state">No active sessions. Click "+ New" to launch one.</div>';
    targets.forEach(el => { el.innerHTML = html; });
    // Wire stop buttons
    document.querySelectorAll('button[data-stop]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = parseInt(btn.dataset.stop, 10);
        if (!confirm('Stop session #' + id + '?')) return;
        try {
          await R.api('/sessions/' + id, { method: 'DELETE' });
          await refreshSessions();
        } catch (err) {
          alert('Stop failed: ' + err.message);
        }
      });
    });
    const nav = document.getElementById('nav-sess-count');
    if (nav) nav.textContent = sessions.length;
  }

  async function refreshSessions(){
    try {
      const sessions = await R.api('/sessions');
      R.state.sessions = sessions;
      renderSessions(sessions);
    } catch (e) {
      console.warn('session refresh failed', e);
    }
  }

  function openSessionModal(){
    document.getElementById('sessModal').classList.add('open');
    const nameInput = document.getElementById('sess-user');
    if (R.state.me && R.state.me.display_name) nameInput.value = R.state.me.display_name;
    else if (!nameInput.value) nameInput.value = 'Dev';
    nameInput.focus();
  }

  function closeSessionModal(){
    document.getElementById('sessModal').classList.remove('open');
  }
  window.closeSessionModal = closeSessionModal;

  async function launchSession(){
    const image = document.getElementById('sess-image').value;
    const user = document.getElementById('sess-user').value.trim() || 'Dev';
    if (!image) { alert('Pick an image first.'); return; }
    const btn = document.getElementById('sess-launch');
    btn.disabled = true;
    const orig = btn.textContent;
    btn.textContent = 'Launching…';
    try {
      const s = await R.api('/sessions', { method: 'POST', body: JSON.stringify({ image, user }) });
      closeSessionModal();
      await refreshSessions();
      if (s.url) window.open(s.url, '_blank');
    } catch (e) {
      alert('Launch failed: ' + e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = orig;
    }
  }

  window.R.refreshSessions = refreshSessions;

  document.addEventListener('DOMContentLoaded', () => {
    refreshSessions();
    setInterval(refreshSessions, R.cfg.sessionsPollMs);
    const btn = document.getElementById('btn-new-session');
    if (btn) btn.addEventListener('click', openSessionModal);
    const bigBtn = document.getElementById('btn-new-session-big');
    if (bigBtn) bigBtn.addEventListener('click', openSessionModal);
    const launchBtn = document.getElementById('sess-launch');
    if (launchBtn) launchBtn.addEventListener('click', launchSession);
    const backdrop = document.getElementById('sessModal');
    if (backdrop) backdrop.addEventListener('click', (e) => { if (e.target === backdrop) closeSessionModal(); });
  });
})();
