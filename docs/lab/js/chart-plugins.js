import { MAP_LAND_TOP, MAP_LAND_BOTTOM } from "./constants.js";

// Paints a vertical gradient from MAP_LAND_TOP to MAP_LAND_BOTTOM behind a
// chart's data area, matching the map's land colour. Shared by the map,
// statistics, and What If? bar charts so all animated charts have a
// consistent background. Drawn as a Chart.js plugin rather than a CSS canvas
// background so it also appears in full-screen and downloaded chart views.
export const chartBackgroundPlugin = {
  id: "chartBackground",
  beforeDraw(chart) {
    const { ctx, chartArea } = chart;
    if (!chartArea) return;
    const { left, top, width, height } = chartArea;
    ctx.save();
    const gradient = ctx.createLinearGradient(0, top, 0, top + height);
    gradient.addColorStop(0, MAP_LAND_TOP);
    gradient.addColorStop(1, MAP_LAND_BOTTOM);
    ctx.fillStyle = gradient;
    ctx.fillRect(left, top, width, height);
    ctx.restore();
  },
};
