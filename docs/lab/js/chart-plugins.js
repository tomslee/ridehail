import { themeColor } from "./theme.js";

// Paints the map's land colour (THEME_COLORS LAND, for the current theme)
// behind a chart's data area. Shared by the map, statistics, and What If? bar
// charts so all animated charts have a consistent background. Drawn as a Chart.js plugin rather than a CSS canvas
// background so it also appears in full-screen and downloaded chart views.
export const chartBackgroundPlugin = {
  id: "chartBackground",
  beforeDraw(chart) {
    const { ctx, chartArea } = chart;
    if (!chartArea) return;
    const { left, top, width, height } = chartArea;
    ctx.save();
    ctx.fillStyle = themeColor("LAND");
    ctx.fillRect(left, top, width, height);
    ctx.restore();
  },
};
