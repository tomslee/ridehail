/**
 * Game tab: the end-of-shift debrief. Renders the results from
 * worker.py GameSimulation.game_results() (ridehail.game.GameController.results)
 * into #game-debrief. See claude/game-mode.md section 1.7.
 */

import { colors } from "../js/constants.js";

const MARKET_LABELS = { busy: "Busy Friday", normal: "Normal", slow: "Slow Tuesday" };
// Only non-default difficulties are named: "Pro" is dormant (no longer
// offered on the setup screen, reachable only with difficulty=pro in a link)
const DIFFICULTY_LABELS = { rookie: "", pro: "Pro" };
const BEST_KEY_PREFIX = "ridehail.game.best";

function money(value) {
  const sign = value < 0 ? "−" : "";
  return `${sign}$${Math.abs(value).toFixed(2)}`;
}

function ordinal(n) {
  return `${n}${["st", "nd", "rd"][n - 1] || "th"}`;
}

function pct(value) {
  return `${Math.round(value * 100)}%`;
}

function escapeHtml(text) {
  return String(text).replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );
}

function solid(phase) {
  return colors.get(phase).replace("0.5)", "0.9)");
}

/** Personal best net $/hr for a market + difficulty, kept in localStorage. */
function updatePersonalBest(market, difficulty, netPerHour) {
  const key = `${BEST_KEY_PREFIX}.${market}.${difficulty}`;
  let previous = null;
  try {
    const stored = localStorage.getItem(key);
    previous = stored === null ? null : Number(stored);
    if (previous === null || netPerHour > previous) {
      localStorage.setItem(key, String(netPerHour));
    }
  } catch {
    // Storage unavailable (private window, blocked): no personal bests
  }
  return previous;
}

/**
 * Pick up to three insights, most telling first, from the results' insight
 * inputs.
 */
function chooseInsights(results) {
  const i = results.insights;
  const player = results.player;
  const out = [];
  if (i.pickup_share != null && i.pickup_share >= 0.15) {
    out.push(
      `Driving to pickups took ${pct(i.pickup_share)} of your shift, all of it unpaid.`,
    );
  }
  if (i.declined_above_rate_card > 0) {
    out.push(
      `You declined ${i.declined_above_rate_card} offer${i.declined_above_rate_card > 1 ? "s" : ""} that paid at or above the rate card.`,
    );
  }
  if (i.accepted_below_rate_card > 0 && player.accepts > 0) {
    out.push(
      `${i.accepted_below_rate_card} of the ${player.accepts} trips you accepted paid below the rate card.`,
    );
  }
  if (i.idle_minutes_per_offer != null && player.offers > 0) {
    out.push(
      `You spent ${i.idle_minutes_per_offer.toFixed(1)} idle minutes per offer. The longer the wait for the next offer, the more a decline costs you.`,
    );
  }
  if (i.best_per_min != null && i.worst_per_min != null && player.accepts > 1) {
    out.push(
      `Your best trip paid ${money(i.best_per_min * 60)} an hour, pickup included; your worst paid ${money(i.worst_per_min * 60)}.`,
    );
  }
  if (i.unpaid_share != null) {
    out.push(`You had no rider for ${pct(i.unpaid_share)} of your shift.`);
  }
  return out.slice(0, 3);
}

function timeSplitHtml(minutes) {
  const total = minutes.P1 + minutes.P2 + minutes.P3 || 1;
  const parts = [
    ["P1", "Idle", minutes.P1],
    ["P2", "To pickups", minutes.P2],
    ["P3", "With a rider", minutes.P3],
  ];
  const segments = parts
    .filter(([, , m]) => m > 0)
    .map(
      ([phase, label, m]) =>
        `<div class="game-split-seg" style="flex:${m};background:${solid(phase)}" title="${label}: ${Math.round(m)} min"></div>`,
    )
    .join("");
  const legend = parts
    .map(
      ([phase, label, m]) =>
        `<li><span class="game-legend-swatch" data-phase="${phase}"></span>${label}: ${Math.round(m)} min (${pct(m / total)})</li>`,
    )
    .join("");
  return `<div class="game-split-bar">${segments}</div><ul class="game-split-legend">${legend}</ul>`;
}

function rankTableHtml(results) {
  const rows = [
    {
      name: "You",
      rule: "",
      you: true,
      ...results.player,
    },
    ...results.bots,
  ].sort((a, b) => b.net_per_hour - a.net_per_hour);
  const body = rows
    .map(
      (row, index) => `
      <tr class="${row.you ? "is-you" : ""}">
        <td>${index + 1}</td>
        <td><strong>${escapeHtml(row.name)}</strong>${row.rule ? `<div class="game-rule">${escapeHtml(row.rule)}</div>` : ""}</td>
        <td class="num">${row.accepts} of ${row.offers}</td>
        <td class="num">${money(row.earnings)}</td>
        <td class="num">${money(row.costs)}</td>
        <td class="num"><strong>${money(row.net_per_hour)}</strong></td>
      </tr>`,
    )
    .join("");
  return `
    <table class="game-table game-rank-table">
      <thead><tr><th></th><th>Driver</th><th class="num">Offers accepted</th>
      <th class="num">Earned</th><th class="num">Costs</th><th class="num">Net per hour</th></tr></thead>
      <tbody>${body}</tbody>
    </table>`;
}

function offerLogHtml(log) {
  if (!log.length) {
    return "<p>You didn't receive any offers this shift.</p>";
  }
  const rows = log
    .map((e) => {
      const vs = Math.round(e.vs_rate_card * 100);
      let outcome = "";
      if (e.decision !== "accept") {
        outcome =
          e.taken_after_minutes != null
            ? `Another driver took it ${e.taken_after_minutes} min later`
            : "No other driver took it";
      }
      const decision =
        e.decision === "accept" ? "Accepted" : e.decision === "timeout" ? "Timed out" : "Declined";
      const clock = `${Math.floor(e.block / 60)}:${String(e.block % 60).padStart(2, "0")}`;
      return `
      <tr class="is-${e.decision}">
        <td class="num">${clock}</td>
        <td class="num">${money(e.offer)}</td>
        <td class="num ${vs >= 0 ? "is-up" : "is-down"}">${vs > 0 ? "+" : vs < 0 ? "−" : "±"}${Math.abs(vs)}%</td>
        <td class="num">${Math.round(e.pickup_minutes)} min</td>
        <td class="num">${Math.round(e.trip_minutes)} min</td>
        <td class="num">${money(e.per_min * 60)}</td>
        <td>${decision}</td>
        <td>${outcome}</td>
      </tr>`;
    })
    .join("");
  return `
    <div class="game-table-scroll">
    <table class="game-table game-log-table">
      <thead><tr><th class="num">Time</th><th class="num">Offer</th><th class="num">vs rate card</th>
      <th class="num">Pickup</th><th class="num">Trip</th><th class="num">Per hour*</th>
      <th>Decision</th><th>What happened next</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    </div>
    <p class="game-footnote">
      “vs rate card” is what the offer card didn't tell you: how the upfront
      price compared with the published rate card for the same trip. Drivers
      receiving upfront offers don't see this either.<br />
      * The offer divided by pickup plus trip time, in dollars an hour.
    </p>`;
}

/**
 * @param {HTMLElement} container - #game-debrief
 * @param {object} results - GameController.results()
 * @param {object} shift - {market, difficulty, code, endedEarly, pausedOnOffer, link}
 * @returns {string} the share line
 */
export function renderDebrief(container, results, shift) {
  const player = results.player;
  const fleetCount = results.fleet_net_per_hour.length;
  const beat = results.fleet_percentile;
  const place =
    [results.player, ...results.bots].filter((r) => r.net_per_hour > player.net_per_hour)
      .length + 1;
  const previousBest = shift.endedEarly
    ? null
    : updatePersonalBest(shift.market, shift.difficulty, player.net_per_hour);
  const isBest = !shift.endedEarly && (previousBest === null || player.net_per_hour > previousBest);
  const labels = [MARKET_LABELS[shift.market], DIFFICULTY_LABELS[shift.difficulty]]
    .filter(Boolean)
    .join(" · ");
  const shiftLabel = `${labels} · shift “${escapeHtml(shift.code)}”`;
  const kicker = [
    shift.endedEarly ? "Shift ended early" : "Shift over",
    shift.pausedOnOffer ? "offers paused" : "",
  ]
    .filter(Boolean)
    .join(" · ");
  const shareLine = `Ridehail One Shift “${shift.code}” · ${labels}: ${money(player.net_per_hour)}/hr net, ${ordinal(place)} of 5, beat ${pct(beat ?? 0)} of drivers. Play the same shift: ${shift.link}`;
  const hours = player.minutes.P1 + player.minutes.P2 + player.minutes.P3;
  const insights = chooseInsights(results)
    .map((text) => `<li>${escapeHtml(text)}</li>`)
    .join("");

  container.innerHTML = `
  <div class="game-card game-card--wide">
    <p class="game-kicker">${kicker} · ${shiftLabel}</p>
    <div class="game-score">
      <div>
        <div class="game-score-value">${money(player.net_per_hour)}<span>/hr net</span></div>
        <div class="game-score-sub">
          ${money(player.net)} over ${Math.floor(hours / 60)} h ${Math.round(hours % 60)} min:
          ${money(player.earnings)} earned, ${money(player.costs)} running costs (${player.km.toFixed(1)} km).
        </div>
      </div>
      <div class="game-score-badges">
        <div class="game-badge"><strong>${ordinal(place)}</strong><span>of the 5 drivers below</span></div>
        <div class="game-badge"><strong>${beat == null ? "–" : pct(beat)}</strong><span>of all ${fleetCount} drivers out-earned</span></div>
        ${isBest ? '<div class="game-badge game-badge--best"><strong>New</strong><span>personal best</span></div>' : previousBest !== null ? `<div class="game-badge"><strong>${money(previousBest)}</strong><span>your best here</span></div>` : ""}
      </div>
    </div>

    <h3>How you compare</h3>
    ${rankTableHtml(results)}
    <p class="game-note">
      Apart from the four drivers above, everyone on the road accepts every
      offer. Across all ${fleetCount} other drivers the average was
      ${money(results.fleet_mean_net_per_hour)} an hour. Each result is one shift, so luck
      plays a part: a lucky run of long trips can beat any strategy. Try the same
      shift code again, or another market, and see whether the ranking holds.
    </p>

    <!-- Filled by game-leaderboard.js; stays hidden where there is no server -->
    <section id="game-leaderboard" class="game-board" hidden></section>

    <h3>Where your time went</h3>
    ${timeSplitHtml(player.minutes)}
    <p class="game-note">
      You were paid only while a rider was on board. Per <em>engaged</em> hour
      (driving to a pickup or carrying a rider) you grossed
      ${money(player.gross_per_engaged_hour)}; per hour of your whole shift you
      netted ${money(player.net_per_hour)}. Some minimum-pay rules for platform
      workers, such as Ontario's, count only engaged time.
    </p>

    ${insights ? `<h3>Three things about your shift</h3><ul class="game-insights">${insights}</ul>` : ""}

    <h3>Your offers</h3>
    ${offerLogHtml(results.offer_log)}
    ${results.insights.rider_extra_wait > 0 ? `<p class="game-note">Your declines added about ${Math.round(results.insights.rider_extra_wait)} minutes of waiting, in total, for riders who were then picked up by someone else.</p>` : ""}

    <div class="game-share">
      <input id="game-share-line" type="text" readonly value="${escapeHtml(shareLine)}" />
      <button id="game-share-copy" class="game-button" type="button">Copy</button>
    </div>

    <div class="game-actions">
      <button id="game-again" class="game-button game-button--primary" type="button">Same shift again</button>
      <button id="game-new" class="game-button" type="button">New shift</button>
    </div>

    <p class="game-footnote">
      About the prices: each offer is a rate card
      (${money(results.params.rate_base)} + ${money(results.params.rate_per_km)}/km +
      ${money(results.params.rate_per_min)}/min for the trip) times a random factor. The
      rate card and the spread of that factor were calibrated with the aid of about
      19,000 real offer cards shown to Toronto drivers (Uber, Lyft and Hopp), from the
      Rideshare Offer Economics Study.
      Running costs are ${money(results.params.ops_cost_per_km)} per km. The city is a
      simplified 12 km square grid with no traffic.
    </p>
  </div>`;
  return shareLine;
}
