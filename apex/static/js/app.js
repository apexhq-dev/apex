// Apex — app shell: hash router, global state, shared utilities.

const R = window.R = {
  state: {
    jobs: [],
    sessions: [],
    images: [],
    metrics: null,
    activity: [],      // derived from job diffs
    me: null,
  },
  cfg: {
    jobsPollMs: 5000,
    sessionsPollMs: 8000,
    imagesPollMs: 30000,
  },
};

// ---- Auth state ----
R.loggedOut = false;

R.showLogin = function() {
  R.loggedOut = true;
  const m = document.getElementById('loginModal');
  if (m) m.classList.add('open');
  const err = document.getElementById('login-error');
  if (err) err.style.display = 'none';
  const pw = document.getElementById('login-password');
  if (pw) { pw.value = ''; setTimeout(() => pw.focus(), 0); }
};

R.handleAuthFailure = function() {
  localStorage.removeItem('apex_token');
  R.showLogin();
};

// ---- API helper ----
R.api = async function(path, opts = {}) {
  // Short-circuit once we know we're logged out — stops poll loops from
  // hammering the backend with 401s while the login modal is up.
  if (R.loggedOut) throw new Error('unauthorized');

  const token = localStorage.getItem('apex_token');
  const headers = Object.assign(
    { 'Content-Type': 'application/json' },
    opts.headers || {},
    token ? { Authorization: `Bearer ${token}` } : {}
  );
  const res = await fetch('/api' + path, { ...opts, headers });
  if (res.status === 401) {
    R.handleAuthFailure();
    throw new Error('unauthorized');
  }
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try { const j = await res.json(); msg = j.detail || msg; } catch {}
    throw new Error(msg);
  }
  if (res.status === 204) return null;
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res.text();
};

// ---- Format helpers ----
R.fmtDuration = function(seconds) {
  if (seconds == null || isNaN(seconds)) return '—';
  seconds = Math.max(0, Math.floor(seconds));
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h) return `${h}h ${String(m).padStart(2,'0')}m`;
  if (m) return `${m}m ${String(s).padStart(2,'0')}s`;
  return `${s}s`;
};

R.fmtRelative = function(isoString) {
  if (!isoString) return '—';
  const t = new Date(isoString.includes('Z') || isoString.includes('+') ? isoString : isoString + 'Z');
  const diff = (Date.now() - t.getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff/60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff/3600)}h ${Math.floor((diff%3600)/60).toString().padStart(2,'0')}m ago`;
  return `${Math.floor(diff/86400)}d ago`;
};

R.escape = function(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
};

// ---- Router ----
//
// Each hash maps to a top-level route-view pane. A few of the overview sub-tabs
// (Jobs, Members) reuse the overview view and just activate the corresponding
// page tab — they're functionally a deep-link into the dashboard.
R.ROUTE_MAP = {
  '#/':         { view: 'overview', tab: 'dashboard', title: 'Overview' },
  '#/jobs':     { view: 'overview', tab: 'history',   title: 'Jobs' },
  '#/members':  { view: 'overview', tab: 'team',      title: 'Team members' },
  '#/sessions': { view: 'sessions',                    title: 'Dev sessions' },
  '#/metrics':  { view: 'metrics',                     title: 'Metrics' },
  '#/images':   { view: 'images',                      title: 'Docker images' },
  '#/audit':    { view: 'audit',                       title: 'Audit log' },
  '#/secrets':  { view: 'secrets',                     title: 'Secrets' },
  '#/settings': { view: 'settings',                    title: 'Settings' },
};

R.onRoute = function() {
  const hash = window.location.hash || '#/';
  const entry = R.ROUTE_MAP[hash] || R.ROUTE_MAP['#/'];

  // 1. Sidebar active state
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.route === hash);
  });

  // 2. Page title
  const t = document.getElementById('page-title');
  if (t) t.textContent = entry.title;

  // 3. Route-view visibility
  document.querySelectorAll('.route-view').forEach(el => {
    el.classList.toggle('active', el.id === 'route-' + entry.view);
  });

  // 4. Page-tabs only make sense on the overview view
  document.body.classList.toggle('non-overview', entry.view !== 'overview');

  // 5. If the route maps to a specific page tab, activate it
  if (entry.tab && window.R && R.switchTab) {
    R.switchTab(entry.tab);
  }

  // 6. Lazy-load route-specific data
  if (entry.view === 'images' && window.renderImages) window.renderImages();
  if (entry.view === 'sessions' && window.R && R.refreshSessions) R.refreshSessions();
  if (entry.view === 'metrics' && window.redrawCharts) window.redrawCharts();
  if (entry.view === 'settings') {
    const api = document.getElementById('settings-api-base');
    if (api) api.textContent = window.location.origin + '/api';
  }
};

window.addEventListener('hashchange', R.onRoute);

// ---- Page sub header (date + GPU) ----
R.updatePageSub = function() {
  const el = document.getElementById('page-sub');
  if (!el) return;
  const d = new Date();
  const opts = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' };
  const dateStr = d.toLocaleDateString(undefined, opts);
  const m = R.state.metrics || {};
  const gpuName = m.gpu_name || 'No GPU';
  const gpuStatus = m.gpu_util != null ? '1 GPU online' : '0 GPUs';
  el.textContent = `${dateStr} · ${gpuName} · ${gpuStatus}`;
};

// ---- Avatar from /api/users/me ----
R.loadMe = async function() {
  try {
    const me = await R.api('/users/me');
    R.state.me = me;
    const av = document.getElementById('avatar');
    const name = me.display_name || me.email || 'RW';
    const initials = name.split(/\s+/).map(s=>s[0]).filter(Boolean).slice(0,2).join('').toUpperCase() || 'RW';
    av.textContent = initials;
    document.getElementById('user-menu-name').textContent = me.display_name || me.email || '—';
    document.getElementById('user-menu-email').textContent = me.email || '—';
    if (R.activeTab === 'team' && window.renderTeam) window.renderTeam();
  } catch {}
};

// ---- User menu (avatar dropdown) ----
(function() {
  const av = document.getElementById('avatar');
  const menu = document.getElementById('user-menu');

  av.addEventListener('click', function(e) {
    e.stopPropagation();
    menu.classList.toggle('open');
  });

  document.addEventListener('click', function() {
    menu.classList.remove('open');
  });

  document.getElementById('user-menu-signout').addEventListener('click', function() {
    menu.classList.remove('open');
    R.handleAuthFailure();
  });
})();

// ---- Login form ----
(function() {
  const submit = document.getElementById('login-submit');
  if (!submit) return;
  const emailEl = document.getElementById('login-email');
  const pwEl    = document.getElementById('login-password');
  const errEl   = document.getElementById('login-error');

  async function doLogin() {
    errEl.style.display = 'none';
    submit.disabled = true;
    const origText = submit.textContent;
    submit.textContent = 'Signing in…';
    try {
      const res = await fetch('/api/users/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: (emailEl.value || '').trim(),
          password: pwEl.value || '',
        }),
      });
      if (!res.ok) {
        let msg = `HTTP ${res.status}`;
        try { const j = await res.json(); msg = j.detail || msg; } catch {}
        throw new Error(msg);
      }
      const data = await res.json();
      localStorage.setItem('apex_token', data.access_token);
      // Full reload gives us a clean state — pollers restart, stale UI clears.
      location.reload();
    } catch (e) {
      errEl.textContent = e.message || 'Sign-in failed';
      errEl.style.display = 'block';
      submit.disabled = false;
      submit.textContent = origText;
    }
  }

  submit.addEventListener('click', doLogin);
  [emailEl, pwEl].forEach(el => {
    el.addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); doLogin(); }
    });
  });
})();

// ---- Page tabs (Dashboard / Job history / Model registry / Team) ----
R.activeTab = 'dashboard';

R.switchTab = function(tab) {
  R.activeTab = tab;
  document.querySelectorAll('.ptab').forEach(el => {
    el.classList.toggle('active', el.dataset.tab === tab);
  });
  document.querySelectorAll('.tab-pane').forEach(el => {
    el.classList.toggle('active', el.id === 'tab-' + tab);
  });
  // Lazy-load each tab's content when it's first shown.
  if (tab === 'history' && window.renderHistory) window.renderHistory();
  if (tab === 'team' && window.renderTeam) window.renderTeam();
};

// ---- Boot ----
document.addEventListener('DOMContentLoaded', () => {
  // No token → skip all authenticated calls and show the login modal. This
  // also short-circuits pollers set up in jobs.js / sessions.js via R.api's
  // loggedOut check.
  if (!localStorage.getItem('apex_token')) {
    R.showLogin();
    return;
  }
  R.onRoute();
  R.loadMe();
  R.updatePageSub();
  setInterval(R.updatePageSub, 30000);

  document.querySelectorAll('.ptab').forEach(el => {
    el.addEventListener('click', () => R.switchTab(el.dataset.tab));
  });

  // Sidebar navigation — clicking a nav-item updates the hash, which fires
  // onRoute via the hashchange listener above.
  document.querySelectorAll('.nav-item[data-route]').forEach(el => {
    el.addEventListener('click', () => {
      const target = el.dataset.route;
      if (window.location.hash === target) {
        // Already on this route — re-run the handler anyway so lazy-loaders fire.
        R.onRoute();
      } else {
        window.location.hash = target;
      }
    });
  });

  // Sidebar plan card — clicking anywhere on the card jumps to Settings so
  // the user can see their plan/version/workspace config. The "Invite members"
  // button nested inside opens the invite prompt without bubbling up to the
  // card's navigation.
  const planCard = document.getElementById('sidebar-plan');
  if (planCard) {
    planCard.addEventListener('click', () => {
      window.location.hash = '#/settings';
    });
  }
  const planInvite = document.getElementById('btn-plan-invite');
  if (planInvite) {
    planInvite.addEventListener('click', (e) => {
      e.stopPropagation();  // don't trigger the card's navigation
      if (window.R && R.openInvitePrompt) R.openInvitePrompt();
    });
  }

  // Fetch plan info and update sidebar card dynamically
  R.api('/users/plan').then(plan => {
    const tierEl = document.getElementById('plan-tier-label');
    const descEl = document.getElementById('plan-desc-label');
    const btnEl  = document.getElementById('btn-plan-invite');
    if (!tierEl) return;
    tierEl.textContent = (plan.name || 'Free').toUpperCase() + ' PLAN';
    descEl.textContent = plan.seats_used + ' of ' + plan.seats_limit + ' seat' + (plan.seats_limit > 1 ? 's' : '');
    if (plan.plan === 'team') {
      btnEl.textContent = 'Invite members →';
    } else {
      btnEl.textContent = plan.seats_used >= plan.seats_limit ? 'Upgrade →' : 'Invite members →';
    }
  }).catch(() => {});
});
