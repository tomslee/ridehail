/**
 * Game tab: the end-of-shift debrief. Renders the results from
 * worker.py GameSimulation.game_results() (ridehail.game.GameController.results)
 * into #game-debrief. See claude/game-mode.md section 1.7.
 */

import { colors } from "../js/constants.js";

const MARKET_LABELS = {
  busy: "Busy Friday",
  normal: "Normal",
  slow: "Slow Tuesday",
};
// The offer screens (ridehail.game.CARDS), named in the kicker and share line
const CARD_LABELS = { helper: "Rate helper", platform: "Platform only" };
const BEST_KEY_PREFIX = "ridehail.game.best";
// Ontario's minimum pay for digital platform workers: the general minimum
// wage for engaged time, before expenses (from October 1, 2026)
const ONTARIO_MINIMUM_WAGE = 17.95;
const ONTARIO_PLATFORM_URL =
  "https://www.ontario.ca/page/rights-and-protections-digital-platform-workers";
const ONTARIO_MINIMUM_WAGE_URL =
  "https://www.ontario.ca/document/your-guide-employment-standards-act-0/minimum-wage#section-0";
// The City of Toronto's ridehail trip data (open data), whose mix of trip
// lengths the offer model is weighted to
const TORONTO_TRIPS_URL =
  "https://open.toronto.ca/dataset/private-transportation-companies-summary-and-trip-data/";
// Source of the running cost per km (ridehail.game.GameParams.ops_cost_per_km)
const COSTS_REPORT_URL =
  "https://www.toronto.ca/legdocs/mmis/2024/ex/bgrd/backgroundfile-251343.pdf";

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

/**
 * Where the player stands in the fleet, from the share of other drivers they
 * out-earned: "Top 15%" above the median, "Bottom 30%" below it. Never 0%.
 */
function fleetStanding(beat) {
  if (beat >= 0.5) return `Top ${Math.max(1, Math.round((1 - beat) * 100))}%`;
  return `Bottom ${Math.max(1, Math.round(beat * 100))}%`;
}

/** A driver count to two significant figures (5999 -> "6,000", 213 -> "210"). */
function roundedCount(n) {
  return Number(n.toPrecision(2)).toLocaleString("en-CA");
}

function escapeHtml(text) {
  return String(text).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
}

function solid(phase) {
  return colors.get(phase).replace("0.5)", "0.9)");
}

/** Personal best net $/hr for a market + offer screen, kept in localStorage. */
function updatePersonalBest(market, card, netPerHour) {
  const key = `${BEST_KEY_PREFIX}.${market}.${card}`;
  let previous = null;
  try {
    // Bests from before the offer-screen choice were saved as "rookie",
    // which had the rate helper
    const stored =
      localStorage.getItem(key) ??
      (card === "helper"
        ? localStorage.getItem(`${BEST_KEY_PREFIX}.${market}.rookie`)
        : null);
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
      `Driving to pickups took ${pct(i.pickup_share)} of your shift. Pickup time isn't paid by the minute: only a long pickup raises the offer, and only a little.`,
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

/**
 * An info button explaining the running costs, like the one in the play
 * screen's sidebar. Its panel opens below the whole line (see
 * .game-info--below), so it stays on screen wherever the line wraps.
 */
function costsInfoHtml(player, costPerKm) {
  const hours =
    (player.minutes.P1 + player.minutes.P2 + player.minutes.P3) / 60;
  const perHour = hours > 0 ? player.costs / hours : 0;
  return `<details class="app-info-popover game-info game-info--below">
      <summary class="app-info-popover__trigger" title="About running costs"
               aria-label="About running costs"><i class="material-icons">info_outline</i></summary>
      <div class="app-info-popover__panel">
        Your car cost ${money(costPerKm)} for every km it drove, with or without a
        rider: ${money(player.costs)} for ${player.km.toFixed(1)} km, or
        ${money(perHour)} an hour. Idle cars keep cruising, so this cost is much
        the same whatever you decide. ${money(costPerKm)} is the median cost per km
        driven in a
        <a href="${COSTS_REPORT_URL}" target="_blank" rel="noopener">2024 report to
        the City of Toronto</a> (page 26). It includes both fixed and variable
        expenses, though the report notes that most of the cost is variable.
      </div>
    </details>`;
}

/**
 * Pay per hour in three steps, each changing one thing: fares per engaged
 * hour (what Ontario's minimum for platform workers counts), then idle time
 * added to the hours, then running costs taken off (the score).
 */
function hourlyStepsHtml(player) {
  const m = player.minutes;
  const shiftHours = (m.P1 + m.P2 + m.P3) / 60;
  const engaged = m.P2 + m.P3 > 0;
  const perShiftHour = shiftHours > 0 ? player.earnings / shiftHours : 0;
  const rows = [
    [
      "Fares per engaged hour",
      "Driving to a pickup or with a rider",
      engaged ? money(player.gross_per_engaged_hour) : "–",
    ],
    ["Fares per hour of your shift", "Idle time included", money(perShiftHour)],
    [
      "After running costs",
      "Per hour of your shift: your score",
      money(player.net_per_hour),
    ],
  ];
  const body = rows
    .map(
      ([label, detail, value], i) => `
      <tr class="${i === rows.length - 1 ? "is-you" : ""}">
        <td><strong>${label}</strong><div class="game-rule">${detail}</div></td>
        <td class="num">${i === rows.length - 1 ? `<strong>${value}</strong>` : value}</td>
      </tr>`,
    )
    .join("");
  let comparison = "";
  if (engaged) {
    const above = player.gross_per_engaged_hour >= ONTARIO_MINIMUM_WAGE;
    comparison = ` Your fares per engaged hour were ${above ? "above" : "below"} that
      minimum${above && player.net_per_hour < ONTARIO_MINIMUM_WAGE ? ", but after idle time and running costs you netted less than it" : ""}.`;
  }
  return `
    <table class="game-table game-hourly-table">
      <tbody>${body}</tbody>
    </table>
    <p class="game-note">
      Each offer paid a fixed price for its pickup and trip together, however
      long they took, and idle time was never paid. In Ontario,
      <a href="${ONTARIO_PLATFORM_URL}" target="_blank" rel="noopener">platform
      drivers are entitled</a> to the
      <a href="${ONTARIO_MINIMUM_WAGE_URL}" target="_blank" rel="noopener">general
      minimum wage</a>, ${money(ONTARIO_MINIMUM_WAGE)} an hour, but only for
      engaged time and before expenses: the first row. The steps below it are
      what that minimum doesn't count: idle time and running costs.${comparison}
    </p>`;
}

/** "2026-01 to 2026-07" as "January to July 2026". */
function monthRange(range) {
  const name = (ym) =>
    new Date(`${ym}-15T12:00:00`).toLocaleString("en-CA", { month: "long" });
  const [from, to] = range.split(" to ");
  const [fromYear, toYear] = [from.slice(0, 4), to.slice(0, 4)];
  return fromYear === toYear
    ? `${name(from)} to ${name(to)} ${toYear}`
    : `${name(from)} ${fromYear} to ${name(to)} ${toYear}`;
}

/**
 * What the player's riders probably paid, and how much of it the player got.
 * Totals over the shift: a single trip's rider fare is only a typical value
 * for its length, but the totals even out.
 */
function riderFaresHtml(player) {
  if (!(player.rider_fares > 0)) return "";
  const trips = player.trips_completed;
  const preHst = player.rider_fares - player.rider_hst;
  const tripsText =
    trips === 0
      ? "the trip you were on when the shift ended"
      : `your ${trips} trip${trips === 1 ? "" : "s"}`;
  return `
    <h3>What your riders paid</h3>
    <p class="game-note">
      Riders on ${tripsText} probably paid about ${money(player.rider_fares)} in
      total, including about ${money(player.rider_hst)} in HST. You received
      ${money(player.earnings)}: ${pct(player.driver_share)} of the
      ${money(preHst)} they paid before HST. The rest went to the platform,
      apart from the City of Toronto's per-trip fees. Riders' fares are
      estimates (see “About the prices” below).
    </p>`;
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
  const fleetCount = results.fleet_net_per_hour.length;
  const rows = [
    {
      name: "You",
      you: true,
      ...results.player,
    },
    ...results.bots,
  ];
  // Everyone else on the road, for orientation: placed by its net per hour
  // but not ranked (it's an average, not a driver). Its drivers were on
  // shift for different lengths of time, so only rates are shown.
  if (fleetCount) {
    rows.push({
      name: "Average of other drivers",
      average: true,
      driver_share: results.fleet_driver_share,
      net_per_hour: results.fleet_mean_net_per_hour,
    });
  }
  rows.sort((a, b) => b.net_per_hour - a.net_per_hour);
  let place = 0;
  const body = rows
    .map((row) => {
      if (row.average) {
        return `
      <tr class="is-average">
        <td></td>
        <td class="game-driver"><strong>${row.name}</strong></td>
        <td class="num">–</td>
        <td class="num">–</td>
        <td class="num">–</td>
        <td class="num">${row.driver_share == null ? "–" : pct(row.driver_share)}</td>
        <td class="num"><strong>${money(row.net_per_hour)}</strong></td>
      </tr>`;
      }
      place += 1;
      return `
      <tr class="${row.you ? "is-you" : ""}">
        <td>${place}</td>
        <td class="game-driver"><strong>${escapeHtml(row.name)}</strong></td>
        <td class="num">${row.accepts} of ${row.offers}</td>
        <td class="num">${money(row.earnings)}</td>
        <td class="num">${money(row.costs)}</td>
        <td class="num">${row.driver_share == null ? "–" : pct(row.driver_share)}</td>
        <td class="num"><strong>${money(row.net_per_hour)}</strong></td>
      </tr>`;
    })
    .join("");
  return `
    <div class="game-table-scroll">
    <table class="game-table game-rank-table">
      <thead><tr><th></th><th>Driver</th><th class="num">Offers accepted</th>
      <th class="num">Earned</th><th class="num">Costs</th><th class="num">Share of fares</th>
      <th class="num">Net per hour</th></tr></thead>
      <tbody>${body}</tbody>
    </table>
    </div>`;
}

function offerLogHtml(log, card) {
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
        e.decision === "accept"
          ? "Accepted"
          : e.decision === "timeout"
            ? "Timed out"
            : "Declined";
      const clock = `${Math.floor(e.block / 60)}:${String(e.block % 60).padStart(2, "0")}`;
      return `
      <tr class="is-${e.decision}">
        <td class="num">${clock}</td>
        <td class="num">${money(e.offer)}</td>
        <td class="num ${vs >= 0 ? "is-up" : "is-down"}">${vs > 0 ? "+" : vs < 0 ? "−" : "±"}${Math.abs(vs)}%</td>
        <td class="num">${money(e.rider_fare)}</td>
        <td class="num">${Math.round(e.pickup_minutes)} min</td>
        <td class="num">${Math.round(e.trip_minutes)} min</td>
        <td class="num">${money(e.per_min * 60)}</td>
        <td>${decision}</td>
        <td>${outcome}</td>
      </tr>`;
    })
    .join("");
  // Played without the rate helper: show where its numbers were all along
  const helperNote =
    card === "platform"
      ? `<p class="game-note">You played with the platform's card only. The
      “Per hour*” column is what a rate helper app would have shown you on
      each offer.</p>`
      : "";
  return `${helperNote}
    <div class="game-table-scroll">
    <table class="game-table game-log-table">
      <thead><tr><th class="num">Time</th><th class="num">Offer</th><th class="num">vs rate card</th>
      <th class="num">Rider paid†</th><th class="num">Pickup</th><th class="num">Trip</th><th class="num">Per hour*</th>
      <th>Decision</th><th>What happened next</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    </div>
    <p class="game-footnote">
      “vs rate card” is what the offer card didn't tell you: how the upfront
      price compared with the rate card for the same trip (see “About the
      prices” below). Drivers receiving upfront offers don't see this
      either.<br />
      † An estimate of what the rider paid for the trip, including HST and
      City fees (see “About the prices” below).<br />
      * The offer divided by pickup plus trip time, in dollars an hour.
    </p>`;
}

/**
 * @param {HTMLElement} container - #game-debrief
 * @param {object} results - GameController.results()
 * @param {object} shift - {market, card, code, city, endedEarly, pausedOnOffer, link}
 * @returns {string} the share line
 */
export function renderDebrief(container, results, shift) {
  const player = results.player;
  const cityKm = Math.round(results.params.city_km ?? 12);
  const fleetCount = results.fleet_net_per_hour.length;
  const beat = results.fleet_percentile;
  // The player and the bots, as in the "How you compare" table
  const drivers = results.bots.length + 1;
  const standing = beat == null ? "–" : fleetStanding(beat);
  const place =
    [results.player, ...results.bots].filter(
      (r) => r.net_per_hour > player.net_per_hour,
    ).length + 1;
  const previousBest = shift.endedEarly
    ? null
    : updatePersonalBest(
        shift.city === "big" ? `${shift.market}.big` : shift.market,
        shift.card,
        player.net_per_hour,
      );
  const isBest =
    !shift.endedEarly &&
    (previousBest === null || player.net_per_hour > previousBest);
  const labels = [
    shift.city === "big" ? "Big city" : null,
    MARKET_LABELS[shift.market],
    CARD_LABELS[shift.card],
  ]
    .filter(Boolean)
    .join(" · ");
  const shiftLabel = `${labels} · shift “${escapeHtml(shift.code)}”`;
  const kicker = [
    shift.endedEarly ? "Shift ended early" : "Shift over",
    shift.pausedOnOffer ? "offers paused" : "",
  ]
    .filter(Boolean)
    .join(" · ");
  const shareLine = `Ridehail: Just One More Shift… “${shift.code}” · ${labels}: ${money(player.net_per_hour)}/hr net, ${ordinal(place)} of ${drivers}${beat == null ? "" : `, ${standing.toLowerCase()} of drivers`}. Play the same shift: ${shift.link}`;
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
          You took in ${money(player.earnings)} over ${Math.floor(hours / 60)} h ${Math.round(hours % 60)} min.
          After ${money(player.costs)} running costs (${player.km.toFixed(1)} km)${costsInfoHtml(player, results.params.ops_cost_per_km)} you earned ${money(player.net)}.
        </div>
      </div>
      <div class="game-score-badges">
        <div class="game-badge"><strong>${ordinal(place)}</strong><span>of the ${drivers} drivers below</span></div>
        <div class="game-badge"><strong>${standing}</strong><span>of about ${roundedCount(fleetCount)} drivers</span></div>
        ${isBest ? '<div class="game-badge game-badge--best"><strong>New</strong><span>personal best</span></div>' : previousBest !== null ? `<div class="game-badge"><strong>${money(previousBest)}</strong><span>your best here</span></div>` : ""}
      </div>
    </div>

    <h3>How you compare</h3>
    <p class="game-note">
    Remember that luck plays a part for any one shift: a lucky run of long trips can 
    beat any strategy. </p>
    
    <p class="game-note">
      “Share of fares” is what each driver was paid, as a share of what their
      riders probably paid before HST. </p>
    ${
      shift.card === "platform"
        ? `<p class="game-note">The automated drivers that go by $/hr see
      what a rate helper would show you.</p>`
        : ""
    }

    
    ${rankTableHtml(results)}

    <!-- Filled by game-leaderboard.js; stays hidden where there is no server -->
    <section id="game-leaderboard" class="game-board" hidden></section>

    <h3>Where your time went</h3>
    ${timeSplitHtml(player.minutes)}
    ${hourlyStepsHtml(player)}

    ${riderFaresHtml(player)}

    ${insights ? `<h3>Three things about your shift</h3><ul class="game-insights">${insights}</ul>` : ""}

    <h3>Your offers</h3>
    ${offerLogHtml(results.offer_log, shift.card)}
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
      About the prices: offers follow a model fitted to
      ${results.params.offer_study_offers.toLocaleString("en-CA")} real Uber offer cards
      shown to Toronto drivers. Trips to or from Pearson airport are left out because of
      game limitations. The offers are
      weighted to match the mix of trip lengths in the City of Toronto's
      <a href="${TORONTO_TRIPS_URL}" target="_blank" rel="noopener">ridehail trip
      records</a>. As in the real offers, pay per km falls as trips get longer, and long pickups
      raise the offer a little.
      ${
        cityKm > 12
          ? `The offer cards are for trips of up to 15 km, so offers for this
      ${cityKm} km city's longest trips extend the model beyond them.`
          : `Trips longer than ${cityKm} km, the size of the game's city, are left out.`
      } The rate card
      (${money(results.params.rate_base)} + ${money(results.params.rate_per_km)}/km +
      ${money(results.params.rate_per_min)}/min for the trip) is for comparison only.
      What riders paid is estimated from the same City of Toronto records for
      ${monthRange(results.params.rider_fare_months)}: about
      ${money(results.params.rider_fare_base)} + ${money(results.params.rider_fare_per_km)}
      per km for a trip within Toronto, including HST and City fees but not tips,
      for all platforms and services together. Each trip's estimate is that typical
      fare, raised or lowered in step with the driver's offer: on real trips the
      platform's share varies much less than prices do, so a trip that pays the
      driver well usually cost the rider more too.
      Running costs are ${money(results.params.ops_cost_per_km)} per km, the median
      cost per km driven in a
      <a href="${COSTS_REPORT_URL}" target="_blank" rel="noopener">2024
      report to the City of Toronto</a> (page 26). The city is a
      simplified ${cityKm} km square grid, and every car travels at 22 km/h, a typical
      average speed for Toronto ridehail trips of these lengths.
    </p>
  </div>`;
  return shareLine;
}
