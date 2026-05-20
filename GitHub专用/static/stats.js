/** 科技风统计图（柱状 + 折线面积），供独立统计界面使用 */
(function (global) {
  function niceMax(values, floor) {
    if (!values.length) return floor;
    return Math.max(Math.max(...values) * 1.15, floor);
  }
  function fmtVal(v, unit) {
    if (unit === '秒') return v < 100 ? v.toFixed(1) : String(Math.round(v));
    return String(Math.round(v));
  }

  function drawTechBar(canvas, values, unit, title) {
    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.clientWidth;
    const h = canvas.height = canvas.clientHeight;
    ctx.clearRect(0, 0, w, h);
    const bg = ctx.createLinearGradient(0, 0, 0, h);
    bg.addColorStop(0, '#0c1e3d');
    bg.addColorStop(1, '#060d1f');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    ctx.strokeRect(1, 1, w - 2, h - 2);

    ctx.fillStyle = '#e0f2fe';
    ctx.font = 'bold 13px "Microsoft YaHei UI", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(title, w / 2, 22);

    if (!values.length) {
      ctx.fillStyle = '#64748b';
      ctx.font = '12px sans-serif';
      ctx.fillText('暂无数据', w / 2, h / 2);
      ctx.fillText('发送消息后将记录各轮', w / 2, h / 2 + 18);
      return;
    }

    const pad = { l: 44, r: 16, t: 36, b: 40 };
    const cw = w - pad.l - pad.r;
    const ch = h - pad.t - pad.b;
    const floor = unit === '秒' ? 2 : 40;
    const vmax = niceMax(values, floor);
    const n = values.length;
    const baseline = pad.t + ch;

    ctx.strokeStyle = '#1e3a5f';
    ctx.fillStyle = '#64748b';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 4; i++) {
      const frac = i / 4;
      const y = pad.t + ch * (1 - frac);
      ctx.beginPath();
      ctx.moveTo(pad.l, y);
      ctx.lineTo(pad.l + cw, y);
      ctx.stroke();
      ctx.fillText(fmtVal(vmax * frac, unit), pad.l - 6, y + 4);
    }

    const barW = Math.min(36, Math.max(10, cw / Math.max(n * 2, 2)));
    const gap = Math.max(4, (cw - barW * n) / (n + 1));
    values.forEach((v, i) => {
      const x0 = pad.l + gap + i * (barW + gap);
      const bh = Math.min(ch, (v / vmax) * ch);
      const y0 = baseline - bh;
      const grad = ctx.createLinearGradient(x0, y0, x0, baseline);
      grad.addColorStop(0, '#60a5fa');
      grad.addColorStop(1, '#2563eb');
      ctx.fillStyle = grad;
      ctx.fillRect(x0, y0, barW, bh);
      ctx.strokeStyle = '#93c5fd';
      ctx.strokeRect(x0, y0, barW, bh);
      const cx = x0 + barW / 2;
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(fmtVal(v, unit), cx, y0 - 8);
      ctx.fillStyle = '#94a3b8';
      ctx.font = '10px sans-serif';
      ctx.fillText('第' + (i + 1) + '轮', cx, baseline + 14);
    });
    ctx.fillStyle = '#94a3b8';
    ctx.fillText(unit, w / 2, h - 8);
  }

  function drawTechLine(canvas, values, unit, title) {
    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.clientWidth;
    const h = canvas.height = canvas.clientHeight;
    ctx.clearRect(0, 0, w, h);
    const bg = ctx.createLinearGradient(0, 0, 0, h);
    bg.addColorStop(0, '#0c1e3d');
    bg.addColorStop(1, '#060d1f');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    ctx.strokeRect(1, 1, w - 2, h - 2);

    ctx.fillStyle = '#e0f2fe';
    ctx.font = 'bold 13px "Microsoft YaHei UI", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(title, w / 2, 22);

    if (!values.length) {
      ctx.fillStyle = '#64748b';
      ctx.font = '12px sans-serif';
      ctx.fillText('暂无数据', w / 2, h / 2);
      return;
    }

    const pad = { l: 44, r: 16, t: 36, b: 40 };
    const cw = w - pad.l - pad.r;
    const ch = h - pad.t - pad.b;
    const floor = unit === '秒' ? 2 : 40;
    const vmax = niceMax(values, floor);
    const n = values.length;
    const baseline = pad.t + ch;

    ctx.strokeStyle = '#1e3a5f';
    ctx.fillStyle = '#64748b';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 4; i++) {
      const frac = i / 4;
      const y = pad.t + ch * (1 - frac);
      ctx.beginPath();
      ctx.moveTo(pad.l, y);
      ctx.lineTo(pad.l + cw, y);
      ctx.stroke();
      ctx.fillText(fmtVal(vmax * frac, unit), pad.l - 6, y + 4);
    }

    const xs = n === 1
      ? [pad.l + cw / 2]
      : values.map((_, i) => pad.l + (cw * i) / (n - 1));
    const pts = values.map((v, i) => ({
      x: xs[i],
      y: baseline - Math.min(ch, (v / vmax) * ch),
      v,
    }));

    if (pts.length >= 2) {
      ctx.beginPath();
      ctx.moveTo(pts[0].x, baseline);
      pts.forEach(p => ctx.lineTo(p.x, p.y));
      ctx.lineTo(pts[pts.length - 1].x, baseline);
      ctx.closePath();
      const area = ctx.createLinearGradient(0, pad.t, 0, baseline);
      area.addColorStop(0, 'rgba(37, 99, 235, 0.55)');
      area.addColorStop(1, 'rgba(37, 99, 235, 0.05)');
      ctx.fillStyle = area;
      ctx.fill();
    }

    if (pts.length >= 2) {
      ctx.strokeStyle = '#60a5fa';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
      ctx.stroke();
    }

    pts.forEach((p, i) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
      ctx.fillStyle = '#fff';
      ctx.fill();
      ctx.strokeStyle = '#3b82f6';
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.fillStyle = '#e0f2fe';
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(fmtVal(p.v, unit), p.x, p.y - 12);
      ctx.fillStyle = '#94a3b8';
      ctx.font = '10px sans-serif';
      ctx.fillText('第' + (i + 1) + '轮', p.x, baseline + 14);
    });
    ctx.fillStyle = '#94a3b8';
    ctx.fillText(unit, w / 2, h - 8);
  }

  global.HiAIStats = {
    refreshAll(stats) {
      const t = stats.thinking || [];
      const w = stats.words || [];
      drawTechBar(document.getElementById('st-think-bar'), t, '秒', '思考时间 · 柱状图');
      drawTechBar(document.getElementById('st-words-bar'), w, '字', '回复字数 · 柱状图');
      drawTechLine(document.getElementById('st-think-line'), t, '秒', '思考时间 · 折线图');
      drawTechLine(document.getElementById('st-words-line'), w, '字', '回复字数 · 折线图');
    },
  };
})(window);
