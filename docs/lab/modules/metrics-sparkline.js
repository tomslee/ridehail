/**
 * A small line chart of the fleet's time split (P1 / P2 / P3) and riders'
 * wait fraction, drawn straight onto a canvas. Shared by the lab map's
 * metrics overlay (modules/map.js) and the Game tab's sidebar chart
 * (game-tab.js).
 */

// Spread label y-positions so adjacent labels keep at least `gap` apart, then
// keep the whole stack within [gap/2, H - gap/2]. Mutates and returns `labels`.
function spreadLabels(labels, H, gap) {
  labels.sort((a, b) => a.y - b.y);
  for (let i = 1; i < labels.length; i++) {
    if (labels[i].y - labels[i - 1].y < gap) {
      labels[i].y = labels[i - 1].y + gap;
    }
  }
  const overflow = labels[labels.length - 1].y - (H - gap / 2);
  if (overflow > 0) for (const l of labels) l.y -= overflow;
  const underflow = gap / 2 - labels[0].y;
  if (underflow > 0) for (const l of labels) l.y += underflow;
  return labels;
}

/**
 * Draw the chart.
 * @param {CanvasRenderingContext2D} ctx - drawn over its whole canvas
 * @param {Array<{p1, p2, p3, wait, x?}>} history - oldest first
 * @param {Object} options
 * @param {Array<{key, label, color}>} options.solidLines - P1 / P2 / P3
 * @param {Array<{key, label, color}>} options.dashedLines - the wait line
 * @param {boolean} options.labels - end-of-line value labels in a right gutter
 * @param {number} options.labelFont - label size in canvas pixels
 * @param {number} options.gutter - width of the label gutter in canvas pixels
 * @param {number} options.lineWidth
 * @param {number} [options.xMax] - if set, each point sits at x / xMax across
 *   the plot (a fixed time axis that fills as it goes); otherwise the points
 *   are spread evenly across the whole width
 * @param {number} [options.scale] - device pixels per CSS pixel, for dashes
 * @param {boolean} [options.inset] - keep half a line width clear at the top
 *   and bottom, so lines at 0% and 100% aren't cut in half
 */
export function drawMetricsSparkline(ctx, history, options) {
  if (!ctx || history.length < 2) return;
  const {
    solidLines,
    dashedLines,
    labels = false,
    labelFont = 13,
    gutter = 0,
    lineWidth = 1.5,
    xMax = null,
    scale = 1,
    inset = false,
  } = options;
  const W = ctx.canvas.width;
  const H = ctx.canvas.height;
  ctx.clearRect(0, 0, W, H);

  const PW = Math.max(W - (labels ? gutter : 0), 10);
  const n = history.length;
  const xOf =
    xMax != null
      ? (i) => (PW * history[i].x) / Math.max(xMax, 1)
      : (i) => (PW * i) / Math.max(n - 1, 1);
  const pad = inset ? lineWidth / 2 : 0;
  const yOf = (v) => pad + (H - 2 * pad) * (1 - v);

  // Subtle reference lines at 25 / 50 / 75% on taller charts
  if (H >= 80) {
    ctx.strokeStyle = "rgba(0,0,0,0.07)";
    ctx.lineWidth = 0.5 * scale;
    for (const v of [0.25, 0.5, 0.75]) {
      ctx.beginPath();
      ctx.moveTo(0, yOf(v));
      ctx.lineTo(W, yOf(v));
      ctx.stroke();
    }
  }

  ctx.lineJoin = "round";
  const drawSeries = (lines, dash) => {
    ctx.setLineDash(dash.map((d) => d * scale));
    ctx.lineWidth = lineWidth;
    for (const line of lines) {
      ctx.beginPath();
      for (let i = 0; i < n; i++) {
        const y = yOf(history[i][line.key]);
        i === 0 ? ctx.moveTo(xOf(i), y) : ctx.lineTo(xOf(i), y);
      }
      ctx.strokeStyle = line.color;
      ctx.stroke();
    }
  };
  drawSeries(solidLines, []);
  drawSeries(dashedLines, [4, 3]);
  ctx.setLineDash([]);

  if (!labels || gutter <= 0) return;
  // End-of-line labels with the current values, joined to the line ends
  const last = history[n - 1];
  const xLast = xOf(n - 1);
  const pct = (v) => Math.round(v * 100) + "%";
  const placed = [...solidLines, ...dashedLines].map((line) => {
    const y = yOf(last[line.key]);
    return {
      text: `${line.label} ${pct(last[line.key])}`,
      color: line.color,
      origY: y,
      y,
    };
  });
  spreadLabels(placed, H, labelFont + 3 * scale);

  ctx.font = `${labelFont}px monospace`;
  ctx.textBaseline = "middle";
  ctx.textAlign = "left";
  const lx = PW + 6 * scale;
  for (const lab of placed) {
    ctx.strokeStyle = lab.color;
    ctx.lineWidth = scale;
    ctx.beginPath();
    ctx.moveTo(xLast, lab.origY);
    ctx.lineTo(lx - 2 * scale, lab.y);
    ctx.stroke();
    ctx.fillStyle = lab.color;
    ctx.fillText(lab.text, lx, lab.y);
  }
}
