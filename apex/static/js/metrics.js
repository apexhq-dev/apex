// Apex — metrics SSE consumer + chart renderer.

(function(){
  const BUF = 60;
  const gpuData = new Array(BUF).fill(0);
  const cpuData = new Array(BUF).fill(0);

  function drawOne(c) {
    if (!c || !c.isConnected) return;
    const rect = c.getBoundingClientRect();
    if (rect.width === 0) return; // hidden route, skip
    const dpr = window.devicePixelRatio || 1;
    const W = Math.max(1, rect.width * dpr);
    const H = Math.max(1, rect.height * dpr);
    c.width = W; c.height = H;
    const ctx = c.getContext('2d');
    ctx.clearRect(0, 0, W, H);

    function series(data, color){
      const sy = v => (1 - (v/100)) * (H - 6*dpr) + 3*dpr;
      const sx = i => i * (W / (data.length - 1));
      const grad = ctx.createLinearGradient(0, 0, 0, H);
      grad.addColorStop(0, color + '33');
      grad.addColorStop(1, color + '00');
      ctx.beginPath();
      data.forEach((v, i) => { i === 0 ? ctx.moveTo(sx(i), sy(v)) : ctx.lineTo(sx(i), sy(v)); });
      ctx.lineTo(sx(data.length - 1), H);
      ctx.lineTo(0, H);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.beginPath();
      data.forEach((v, i) => { i === 0 ? ctx.moveTo(sx(i), sy(v)) : ctx.lineTo(sx(i), sy(v)); });
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5 * dpr;
      ctx.lineJoin = 'round';
      ctx.stroke();
    }

    series(cpuData, '#8B5CF6');
    series(gpuData, '#00D9F5');
  }

  function drawChart(){
    document.querySelectorAll('canvas.metric-canvas').forEach(drawOne);
  }

  // Exposed so the router can force a redraw when a metrics-route pane becomes visible.
  window.redrawCharts = drawChart;

  function fmtPct(v){
    if (v == null || isNaN(v)) return '—';
    return Math.round(v) + '<span style="font-size:12px;color:var(--text2)">%</span>';
  }
  function fmtTemp(v){
    if (v == null || isNaN(v)) return '—';
    return Math.round(v) + '<span style="font-size:12px;color:var(--text2)">°C</span>';
  }
  function setWidth(id, pct){
    const el = document.getElementById(id);
    if (el) el.style.width = Math.max(0, Math.min(100, pct || 0)) + '%';
  }
  function setText(id, text){
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }
  function setHTML(id, html){
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  function onMetrics(m){
    R.state.metrics = m;

    const gpu = m.gpu_util;
    const cpu = m.cpu_util;
    const temp = m.gpu_temp;

    // Shift buffers, push new values (null → 0 for chart purposes)
    gpuData.shift(); gpuData.push(gpu == null ? 0 : gpu);
    cpuData.shift(); cpuData.push(cpu == null ? 0 : cpu);
    drawChart();

    // Topbar
    setWidth('tb-gpu', gpu || 0);
    setText('tb-gpu-v', gpu == null ? '—' : Math.round(gpu) + '%');
    setWidth('tb-cpu', cpu || 0);
    setText('tb-cpu-v', cpu == null ? '—' : Math.round(cpu) + '%');
    setText('tb-temp', temp == null ? '—' : Math.round(temp) + '°C');

    const vramUsed = m.vram_used_gb, vramTot = m.vram_total_gb;
    setText('tb-vram', (vramUsed == null || vramTot == null) ? '— / — GB' : `${vramUsed} / ${vramTot} GB`);

    // Sidebar GPU card
    setText('sb-gpu-name', m.gpu_name || 'No GPU detected');
    setText('sb-gpu-sub', vramTot == null ? '— GB · — CUDA' : `${vramTot} GB VRAM`);
    setText('sb-gpu', gpu == null ? '—' : Math.round(gpu) + '%');
    setWidth('sb-gpu-b', gpu || 0);
    setText('sb-pwr', m.gpu_power_w == null ? '—' : Math.round(m.gpu_power_w) + 'W');
    setText('sb-temp', temp == null ? '—' : Math.round(temp) + '°C');

    // Mini metrics
    setHTML('mm-gpu', fmtPct(gpu));
    setWidth('mm-gpu-b', gpu || 0);
    setHTML('mm-cpu', fmtPct(cpu));
    setWidth('mm-cpu-b', cpu || 0);
    setHTML('mm-temp', fmtTemp(temp));
    setWidth('mm-temp-b', temp == null ? 0 : (temp / 90) * 100);

    if (m.cpu_count) setText('mm-cpu-sub', `${m.cpu_count} cores`);

    // Also refresh the page sub-header (GPU name + online status) so it updates
    // immediately instead of waiting for the 30s timer.
    if (window.R && R.updatePageSub) R.updatePageSub();

    // Populate any [data-metric="key"] cells (used by the Metrics + Settings routes).
    document.querySelectorAll('[data-metric]').forEach(el => {
      const key = el.getAttribute('data-metric');
      const v = m[key];
      if (v == null) { el.textContent = '—'; return; }
      if (key === 'gpu_util' || key === 'cpu_util') el.textContent = Math.round(v) + '%';
      else if (key === 'gpu_temp') el.textContent = Math.round(v) + '°C';
      else if (key === 'gpu_power_w') el.textContent = Math.round(v) + 'W';
      else if (key === 'vram_used_gb' || key === 'vram_total_gb' || key === 'ram_used_gb' || key === 'ram_total_gb') el.textContent = v + ' GB';
      else el.textContent = String(v);
    });
  }

  function connect(){
    try {
      const es = new EventSource('/api/metrics/stream');
      es.addEventListener('metrics', ev => {
        try { onMetrics(JSON.parse(ev.data)); } catch (e) { console.warn('bad metrics payload', e); }
      });
      es.addEventListener('error', () => {
        // Auto-reconnect happens via EventSource, but fall back to /current poll if SSE broken.
      });
    } catch (e) {
      console.warn('SSE unavailable, falling back to polling', e);
      setInterval(async () => {
        try { onMetrics(await R.api('/metrics/current')); } catch {}
      }, 2000);
    }
  }

  window.addEventListener('resize', drawChart);
  document.addEventListener('DOMContentLoaded', () => {
    drawChart();
    connect();
  });
})();
