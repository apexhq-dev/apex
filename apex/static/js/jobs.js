// Apex — jobs list, submit form, stat cards, activity feed (derived from job diffs).

(function(){

  const JOB_STATUS = {
    running: { cls: 'sb-run', label: 'RUNNING', pulse: true,  iconBg: 'var(--green-dim)', icon: '▶' },
    queued:  { cls: 'sb-q',   label: 'QUEUED',  pulse: false, iconBg: 'var(--amber-dim)', icon: '⏳' },
    done:    { cls: 'sb-done',label: 'DONE',    pulse: false, iconBg: 'var(--bg5)',       icon: '✓' },
    failed:  { cls: 'sb-fail',label: 'FAILED',  pulse: false, iconBg: 'var(--red-dim)',   icon: '✗' },
  };

  function shortImage(img){
    if (!img) return '—';
    // e.g. pytorch/pytorch:2.2-cuda12 → pytorch:2.2
    const parts = img.split('/');
    const last = parts[parts.length - 1];
    return last.length > 28 ? last.slice(0, 26) + '…' : last;
  }

  function elapsedSince(iso){
    if (!iso) return 0;
    const t = new Date(iso.includes('Z') || iso.includes('+') ? iso : iso + 'Z');
    return Math.max(0, (Date.now() - t.getTime()) / 1000);
  }

  function renderJobs(jobs){
    const list = document.getElementById('jobList');
    if (!list) return;
    if (!jobs.length) {
      list.innerHTML = '<div class="empty-state">No jobs yet — submit one on the left.</div>';
      return;
    }
    const rows = jobs.slice(0, 6).map((j, idx) => {
      const s = JOB_STATUS[j.status] || JOB_STATUS.queued;
      let meta;
      if (j.status === 'running') {
        meta = `#${String(j.id).padStart(4,'0')} · ${R.escape(shortImage(j.image))} · ${R.fmtDuration(elapsedSince(j.started_at))}`;
      } else if (j.status === 'queued') {
        meta = `#${String(j.id).padStart(4,'0')} · ${R.escape(shortImage(j.image))} · queued`;
      } else {
        meta = `#${String(j.id).padStart(4,'0')} · ${R.escape(shortImage(j.image))} · ${j.error_msg ? R.escape(j.error_msg.slice(0,30)) : R.fmtDuration(j.duration_s)}`;
      }
      const dur = j.status === 'running' ? `GPU ${R.state.metrics?.gpu_util != null ? Math.round(R.state.metrics.gpu_util)+'%' : '—'}`
                 : j.status === 'queued' ? '—'
                 : R.fmtDuration(j.duration_s);
      const dot = s.pulse ? '<div class="sdot pulse"></div>' : '<div class="sdot"></div>';
      const highlight = idx === 0 && j.status === 'running' ? 'highlight' : '';
      return `
        <div class="job-card ${highlight}" data-id="${j.id}" data-name="${R.escape(j.name)}">
          <div class="job-icon" style="background:${s.iconBg}">${s.icon}</div>
          <div class="job-info">
            <div class="job-name">${R.escape(j.name)}</div>
            <div class="job-meta">${meta}</div>
          </div>
          <div class="job-right">
            <div class="sbadge ${s.cls}">${dot}${s.label}</div>
            <div class="job-dur">${R.escape(dur)}</div>
          </div>
        </div>`;
    }).join('');
    list.innerHTML = rows;
    list.querySelectorAll('.job-card').forEach(el => {
      el.addEventListener('click', () => {
        window.openLog && window.openLog('#' + String(el.dataset.id).padStart(4,'0'), el.dataset.name, parseInt(el.dataset.id, 10));
      });
    });
  }

  function renderStatCards(jobs){
    const today = new Date();
    const todayStr = today.toISOString().slice(0, 10);
    const isToday = j => (j.submitted_at || '').slice(0, 10) === todayStr;

    const todays = jobs.filter(isToday);
    const running = jobs.filter(j => j.status === 'running');
    const queued = jobs.filter(j => j.status === 'queued');
    const finishedToday = todays.filter(j => j.status === 'done' || j.status === 'failed');
    const failedToday = todays.filter(j => j.status === 'failed').length;
    const successRate = finishedToday.length
      ? Math.round((finishedToday.filter(j => j.status === 'done').length / finishedToday.length) * 100)
      : null;

    const totalGpuSec = jobs.reduce((acc, j) => {
      if ((j.status === 'done' || j.status === 'failed') && j.duration_s) return acc + j.duration_s * (j.gpu_count || 0);
      if (j.status === 'running' && j.started_at) return acc + elapsedSince(j.started_at) * (j.gpu_count || 0);
      return acc;
    }, 0);
    const gpuHours = (totalGpuSec / 3600).toFixed(1);

    document.getElementById('sc-jobs').textContent = todays.length;
    document.getElementById('sc-jobs-meta').innerHTML = `<b style="color:var(--green)">${running.length}</b> running`;
    document.getElementById('sc-gpuh').textContent = gpuHours;
    document.getElementById('sc-gpuh-meta').innerHTML = `<b style="color:var(--accent)">${running.length}</b> jobs active`;
    document.getElementById('sc-queue').textContent = queued.length;
    document.getElementById('sc-queue-meta').textContent = queued.length ? `${queued.length} waiting` : 'idle';
    document.getElementById('sc-success').textContent = successRate == null ? '—' : successRate;
    document.getElementById('sc-success-meta').innerHTML = `<b style="color:var(--red)">${failedToday}</b> failed today`;

    const nav = document.getElementById('nav-jobs-count');
    if (nav) nav.textContent = running.length + queued.length;
  }

  // ---- Activity feed: diff jobs by status changes ----
  const lastStatus = new Map();
  function renderActivity(){
    const list = document.getElementById('actList');
    if (!list) return;
    const items = R.state.activity.slice(-6).reverse();
    if (!items.length) {
      list.innerHTML = '<div class="empty-state">Activity will appear here as jobs run.</div>';
      return;
    }
    list.innerHTML = items.map(a => `
      <div class="act-item">
        <div class="act-ico" style="background:${a.iconBg}">${a.icon}</div>
        <div style="flex:1">
          <div class="act-text">${a.html}</div>
          <div class="act-time">${R.fmtRelative(a.ts)}</div>
        </div>
      </div>
    `).join('');
  }

  function diffActivity(newJobs){
    const nowIso = new Date().toISOString();
    for (const j of newJobs) {
      const prev = lastStatus.get(j.id);
      if (prev === undefined) {
        lastStatus.set(j.id, j.status);
        continue;
      }
      if (prev === j.status) continue;
      lastStatus.set(j.id, j.status);
      const user = j.submitted_by || 'anon';
      if (j.status === 'running') {
        R.state.activity.push({ ts: j.started_at || nowIso, iconBg: 'var(--green-dim)', icon: '▶',
          html: `<span class="act-user">${R.escape(user)}</span> started job <b>${R.escape(j.name)}</b>` });
      } else if (j.status === 'done') {
        R.state.activity.push({ ts: j.finished_at || nowIso, iconBg: 'var(--bg5)', icon: '✓',
          html: `<span class="act-user">${R.escape(user)}</span> completed <b>${R.escape(j.name)}</b> in ${R.fmtDuration(j.duration_s)}` });
      } else if (j.status === 'failed') {
        R.state.activity.push({ ts: j.finished_at || nowIso, iconBg: 'var(--red-dim)', icon: '✗',
          html: `<span class="act-user">${R.escape(user)}</span> — <b>${R.escape(j.name)}</b> failed${j.error_msg ? ' · ' + R.escape(j.error_msg) : ''}` });
      }
    }
    if (R.state.activity.length > 50) R.state.activity = R.state.activity.slice(-50);
    renderActivity();
  }

  async function refreshJobs(){
    try {
      const jobs = await R.api('/jobs?limit=100');
      R.state.jobs = jobs;
      renderJobs(jobs);
      renderStatCards(jobs);
      diffActivity(jobs);
    } catch (e) {
      console.warn('job refresh failed', e);
    }
  }

  async function loadImages(){
    try {
      const images = await R.api('/images');
      R.state.images = images;
      const sel = document.getElementById('job-image');
      const sessSel = document.getElementById('sess-image');
      const opts = images.length
        ? images.flatMap(i => i.tags).filter(Boolean)
        : ['pytorch/pytorch:2.2-cuda12', 'huggingface/transformers:latest'];
      const html = opts.map(t => `<option value="${R.escape(t)}">${R.escape(t)}</option>`).join('');
      if (sel) sel.innerHTML = html || '<option value="">No images available</option>';
      if (sessSel) sessSel.innerHTML = html || '<option value="">No images available</option>';
      const nav = document.getElementById('nav-img-count');
      if (nav) nav.textContent = images.length;
    } catch (e) {
      console.warn('images load failed', e);
    }
  }

  async function submitJob(e){
    if (e) e.preventDefault();
    const btn = document.getElementById('job-submit');
    const name = document.getElementById('job-name').value.trim();
    const image = document.getElementById('job-image').value;
    const script = document.getElementById('job-script').value.trim();
    const gpu_count = parseInt(document.getElementById('job-gpu').value, 10);
    const priority = document.getElementById('job-priority').value;
    if (!name || !image || !script) {
      alert('Please fill in name, image and entry script.');
      return;
    }
    btn.disabled = true;
    const origText = btn.textContent;
    btn.textContent = 'Submitting…';
    try {
      await R.api('/jobs', { method: 'POST', body: JSON.stringify({ name, image, script, gpu_count, priority }) });
      document.getElementById('job-name').value = '';
      document.getElementById('job-script').value = '';
      await refreshJobs();
    } catch (err) {
      alert('Submit failed: ' + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = origText;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    loadImages();
    refreshJobs();
    setInterval(refreshJobs, R.cfg.jobsPollMs);
    setInterval(loadImages, R.cfg.imagesPollMs);
    const form = document.getElementById('job-form');
    if (form) form.addEventListener('submit', submitJob);
  });

  window.R.refreshJobs = refreshJobs;

  // ---- Job history table ----
  function fmtSubmitted(iso) {
    if (!iso) return '—';
    const t = new Date(iso.includes('Z') || iso.includes('+') ? iso : iso + 'Z');
    return t.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function renderHistory() {
    const body = document.getElementById('hist-body');
    const countEl = document.getElementById('hist-count');
    if (!body) return;
    const filter = (document.getElementById('hist-filter') || {}).value || '';
    const all = R.state.jobs || [];
    const rows = filter ? all.filter(j => j.status === filter) : all;
    countEl.textContent = `${rows.length} of ${all.length}`;
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="9" class="empty-state">No jobs match this filter.</td></tr>';
      return;
    }
    body.innerHTML = rows.map(j => {
      const s = JOB_STATUS[j.status] || JOB_STATUS.queued;
      const dot = s.pulse ? '<div class="sdot pulse"></div>' : '<div class="sdot"></div>';
      const dur = j.status === 'running'
        ? R.fmtDuration(elapsedSince(j.started_at))
        : R.fmtDuration(j.duration_s);
      return `
        <tr data-id="${j.id}">
          <td class="id-cell">#${String(j.id).padStart(4, '0')}</td>
          <td class="name-cell">${R.escape(j.name)}</td>
          <td class="img-cell" title="${R.escape(j.image)}">${R.escape(j.image)}</td>
          <td><div class="sbadge ${s.cls}">${dot}${s.label}</div></td>
          <td>${j.gpu_count ?? 0}</td>
          <td>${R.escape(j.priority || 'normal')}</td>
          <td class="time-cell">${fmtSubmitted(j.submitted_at)}</td>
          <td>${dur}</td>
          <td class="t-right">
            <button class="row-btn" data-action="logs" data-id="${j.id}" data-name="${R.escape(j.name)}">logs</button>
            <button class="row-btn danger" data-action="cancel" data-id="${j.id}">${j.status === 'running' ? 'cancel' : 'remove'}</button>
          </td>
        </tr>`;
    }).join('');

    body.querySelectorAll('button[data-action]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = parseInt(btn.dataset.id, 10);
        const action = btn.dataset.action;
        if (action === 'logs') {
          window.openLog && window.openLog('#' + String(id).padStart(4, '0'), btn.dataset.name, id);
        } else if (action === 'cancel') {
          if (!confirm('Cancel/remove job #' + id + '?')) return;
          try {
            await R.api('/jobs/' + id, { method: 'DELETE' });
            await refreshJobs();
            renderHistory();
          } catch (err) {
            alert('Failed: ' + err.message);
          }
        }
      });
    });
  }

  window.renderHistory = renderHistory;

  document.addEventListener('DOMContentLoaded', () => {
    const filter = document.getElementById('hist-filter');
    if (filter) filter.addEventListener('change', renderHistory);
  });

  // Re-render history live when job list refreshes (if user is looking at that tab).
  const origRefresh = refreshJobs;
  window.R.refreshJobs = async function() {
    await origRefresh();
    if (R.activeTab === 'history') renderHistory();
  };
})();

// ---- Team pane ----
(function(){
  function initials(name){
    if (!name) return 'RW';
    return name.split(/\s+/).map(s => s[0]).filter(Boolean).slice(0, 2).join('').toUpperCase();
  }

  window.renderTeam = function() {
    const body = document.getElementById('team-body');
    if (!body) return;
    // Fall back to a single-user-mode placeholder when /api/users/me is
    // unauthenticated (the v0.1 dashboard ships without a login page).
    const me = R.state.me || {
      display_name: 'Single-user mode',
      email: 'owner@apex.local',
      role: 'owner',
    };
    const name = me.display_name || me.email || 'Owner';
    const role = (me.role || 'member').toLowerCase();
    const note = R.state.me
      ? `Invite teammates via <span class="mono">POST /api/users/invite</span> or click "+ Invite".`
      : `Apex is running in single-user mode. An owner account was auto-created on first boot; the login page lands in v0.2.`;
    body.innerHTML = `
      <div class="team-row">
        <div class="team-avatar">${R.escape(initials(name))}</div>
        <div class="team-info">
          <div class="team-name">${R.escape(name)} <span style="color:var(--text3);font-weight:400;margin-left:6px">(you)</span></div>
          <div class="team-email">${R.escape(me.email || '—')}</div>
        </div>
        <div class="team-role ${role}">${R.escape(role.toUpperCase())}</div>
      </div>
      <div class="empty-state" style="padding:14px 16px;text-align:left;border-top:1px solid var(--border)">
        ${note}<br/>
        A dedicated members page is in the sidebar under Team → Members.
      </div>
    `;
  };

  // Shared invite prompt — used by the Team tab button, the sidebar plan card
  // button, and anywhere else that wants to add a member.
  R.openInvitePrompt = function() {
    const email = prompt('Email for new member:');
    if (!email) return;
    const pw = prompt('Temporary password (min 6 chars):');
    if (!pw) return;
    R.api('/users/invite', {
      method: 'POST',
      body: JSON.stringify({ email, password: pw, display_name: email.split('@')[0], role: 'member' })
    }).then(() => {
      alert('Invited ' + email);
      window.renderTeam && window.renderTeam();
    }).catch(err => {
      // In single-user mode with an auto-created owner, /api/users/invite
      // requires a bearer token we don't have. Tell the user clearly instead
      // of showing a cryptic 401.
      if (/unauthorized|401|missing bearer/i.test(err.message)) {
        alert('Invites require a signed-in admin. Team member management lands in v0.2.');
      } else {
        alert('Invite failed: ' + err.message);
      }
    });
  };

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('btn-invite');
    if (btn) btn.addEventListener('click', R.openInvitePrompt);
  });
})();

// ---- Images route ----
(function(){
  function shortId(id){
    if (!id) return '';
    const s = String(id);
    const m = s.match(/^sha256:([0-9a-f]+)$/i);
    return (m ? m[1] : s).slice(0, 12);
  }

  window.renderImages = function() {
    const body = document.getElementById('images-body');
    const countEl = document.getElementById('images-count');
    if (!body) return;
    const images = R.state.images || [];
    if (countEl) countEl.textContent = `${images.length} image${images.length === 1 ? '' : 's'}`;
    if (!images.length) {
      body.innerHTML = '<tr><td colspan="3" class="empty-state">No images found. Build one with <span class="mono">docker build</span> and it will appear here.</td></tr>';
      return;
    }
    // Flatten: one row per tag (matches how users think of images).
    const rows = [];
    for (const img of images) {
      const tags = (img.tags && img.tags.length) ? img.tags : ['<untagged>'];
      for (const t of tags) {
        rows.push(`
          <tr>
            <td class="name-cell">${R.escape(t)}</td>
            <td class="id-cell">${shortId(img.id)}</td>
            <td class="t-right">${(img.size_gb || 0).toFixed(2)} GB</td>
          </tr>`);
      }
    }
    body.innerHTML = rows.join('');
  };
})();
