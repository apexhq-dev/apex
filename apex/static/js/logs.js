// Apex — log drawer, WebSocket tail.

(function(){
  let ws = null;
  let currentJobId = null;

  function fmtTs(iso){
    try { return new Date(iso).toLocaleTimeString('en-GB', { hour12: false }); }
    catch { return ''; }
  }

  function classify(line){
    if (/^\s*✓|\[ok\]|SUCCESS/i.test(line)) return 'ok';
    if (/^\s*→|\[info\]/i.test(line)) return 'info';
    if (/^\s*⚠|WARN/i.test(line)) return 'warn';
    if (/ERROR|Traceback|FAIL/i.test(line)) return 'err';
    return '';
  }

  function appendLine(line, ts){
    const body = document.getElementById('logBody');
    if (!body) return;
    const cls = classify(line);
    const div = document.createElement('div');
    div.className = 'log-line';
    const span = cls ? `<span class="${cls}">${R.escape(line)}</span>` : R.escape(line);
    div.innerHTML = `<span class="ts">[${fmtTs(ts)}] </span>${span}`;
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
  }

  function setBadge(status){
    const el = document.getElementById('drawerBadge');
    if (!el) return;
    const map = {
      running: { cls: 'sb-run', label: 'RUNNING', pulse: true },
      queued:  { cls: 'sb-q',   label: 'QUEUED',  pulse: false },
      done:    { cls: 'sb-done',label: 'DONE',    pulse: false },
      failed:  { cls: 'sb-fail',label: 'FAILED',  pulse: false },
    };
    const s = map[status] || map.queued;
    el.className = 'sbadge ' + s.cls;
    el.innerHTML = `<div class="sdot${s.pulse ? ' pulse' : ''}"></div>${s.label}`;
  }

  function closeLog(){
    if (ws) {
      try { ws.close(); } catch {}
      ws = null;
    }
    document.getElementById('logDrawer').classList.remove('open');
    currentJobId = null;
  }
  window.closeLog = closeLog;

  async function openLog(displayId, name, rawId){
    // displayId like "#0047"; rawId is integer
    if (rawId == null && displayId) {
      rawId = parseInt(String(displayId).replace(/[^0-9]/g, ''), 10);
    }
    if (!rawId) { console.warn('openLog: no id'); return; }

    currentJobId = rawId;
    document.getElementById('drawerTitle').textContent = `logs · ${displayId} · ${name || ''}`;
    const body = document.getElementById('logBody');
    body.innerHTML = '';
    document.getElementById('logDrawer').classList.add('open');

    let job = null;
    try { job = await R.api('/jobs/' + rawId); setBadge(job.status); } catch {}

    if (ws) { try { ws.close(); } catch {} ws = null; }

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${window.location.host}/api/jobs/${rawId}/logs`;
    try {
      ws = new WebSocket(url);
    } catch (e) {
      appendLine(`[apex] cannot open WebSocket: ${e}`, new Date().toISOString());
      return;
    }
    ws.onmessage = (ev) => {
      try {
        const frame = JSON.parse(ev.data);
        if (frame.error) { appendLine(`[apex] ${frame.error}`, new Date().toISOString()); return; }
        if (frame.line) appendLine(frame.line, frame.ts || new Date().toISOString());
      } catch (e) {
        appendLine(String(ev.data), new Date().toISOString());
      }
    };
    ws.onclose = () => {
      if (currentJobId === rawId) appendLine('[apex] log stream closed', new Date().toISOString());
    };
    ws.onerror = () => {
      appendLine('[apex] WebSocket error', new Date().toISOString());
    };
  }
  window.openLog = openLog;

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('btn-view-logs');
    if (btn) btn.addEventListener('click', () => {
      const running = (R.state.jobs || []).find(j => j.status === 'running');
      if (running) openLog('#' + String(running.id).padStart(4, '0'), running.name, running.id);
      else alert('No running jobs.');
    });
  });
})();
