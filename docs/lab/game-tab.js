/*
 * Game Tab Controller: "Just One More Shift…"
 *
 * The player drives one car for a three-hour shift and accepts or declines
 * the trip offers the dispatcher sends them. All game logic runs in Python
 * (ridehail/game.py, via worker.py GameSimulation); this class shows it:
 * setup screen, map + sidebar, offer card, and the end-of-shift debrief.
 *
 * Worker protocol (see webworker.js):
 *   Play (frameIndex 0, game: true)  start a shift; the worker runs warm-up
 *   frames with results.game         HUD, overlay, and possibly an offer
 *   (offer)                          the worker holds its loop until...
 *   GameDecision {accept, timedOut}  ...the player's answer resumes it
 *   (shift_over)                     the loop stops; we ask for
 *   GetGameResults -> "gameResults"  the debrief data
 *
 * The game shares the worker's single simulation loop with the other tabs,
 * under the settings name "gameSimSettings"; leaving the tab stops it.
 */

import {
  SimulationActions,
  CHART_TYPES,
  MAP_CORE,
  INTERPOLATE_MAX_CITY_SIZE,
} from "./js/constants.js";
import { initMap } from "./modules/map.js";
import { setGameOverlay, pulseGameCar } from "./modules/game-map-overlay.js";
import { OfferCard } from "./modules/game-offer.js";
import { renderDebrief } from "./modules/game-debrief.js";
import { renderBoardPreview, renderLeaderboard } from "./modules/game-leaderboard.js";

// City size in blocks of 0.37 km (ridehail.game CITIES): the standard city
// (MARKET_SHARED, 11.8 km) and the hidden big one (BIG_CITY_SHARED, 17.8 km),
// switched with "+" on the setup screen or city=big in a link. The big
// city's thousands of cars are drawn as a heatmap, with the player's car on
// top (map.js).
const CITY_SIZES = { standard: 32, big: 48 };
const SHIFT_BLOCKS = 180;
// Real time per animation frame while the player is idle, for two frames per
// simulated minute, and the time-warp factors applied by the worker: faster
// while on a trip (nothing to decide) and somewhat faster while idle. Cities
// above INTERPOLATE_MAX_CITY_SIZE draw one frame per minute, so their frames
// take twice as long.
const FRAME_DELAY_MS = 400;
const WARP_BUSY = 0.3;
const WARP_IDLE = 0.75;

const MARKETS = ["busy", "normal", "slow"];
// Offer screens (ridehail.game.CARDS): with the rate helper ($/km and $/hr
// on the card, as a third-party driver app shows them) or the platform's card
// alone. Each has its own leaderboard.
const CARDS = ["helper", "platform"];
// Links from before the offer-screen choice said difficulty=rookie|pro
const LEGACY_CARDS = { rookie: "helper", pro: "platform" };
const CARD_KEY = "ridehail.game.card";
const CARD_LABELS = { helper: "Rate helper", platform: "Platform only" };
const MARKET_LABELS = { busy: "Busy Friday", normal: "Normal", slow: "Slow Tuesday" };

const PHASE_STATUS = {
  P1: "Idle, waiting for an offer",
  P2: "Driving to the pickup",
  P3: "Rider on board",
};

function money(value) {
  const sign = value < 0 ? "−" : "";
  return `${sign}$${Math.abs(value).toFixed(2)}`;
}

function todayCode() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export class GameTab {
  constructor(app) {
    this.app = app;
    // setup | starting | playing | paused | finishing | debrief
    this.state = "setup";
    this.settings = null;
    this.shift = null;
    this.lastGame = null;
    this.shownOfferTrip = null;
    this.offerCard = null;
    this.city = "standard";
  }

  setupEventHandlers() {
    // The Game tab is left out of the PyPI package's copy of the lab (see
    // build.sh): with no markup, stay inert.
    if (!document.getElementById("game-setup")) return;
    // The legend's downtown swatch matches the map's core shading
    document.querySelector(".game-legend-core").style.background = MAP_CORE;
    this.offerCard = new OfferCard((accept, timedOut) =>
      this._sendDecision(accept, timedOut),
    );
    document.getElementById("game-code").value = todayCode();
    this._selectCard(this._loadCard());
    // The setup screen's leaderboard preview follows the market and code
    for (const radio of document.querySelectorAll(
      'input[name="game-market"], input[name="game-card"]',
    )) {
      radio.addEventListener("change", () => this._refreshSetupBoard());
    }
    let codeTimer = null;
    document.getElementById("game-code").addEventListener("input", () => {
      clearTimeout(codeTimer);
      codeTimer = setTimeout(() => this._refreshSetupBoard(), 400);
    });
    document.getElementById("game-start").addEventListener("click", () => this.start());
    document.getElementById("game-pause").addEventListener("click", () => this.togglePause());
    document.getElementById("game-quit").addEventListener("click", () => this.endEarly());
    document.addEventListener("keydown", (event) => {
      if (!this.isActive() || event.repeat) return;
      if (event.key === " " && (this.state === "playing" || this.state === "paused")) {
        event.preventDefault();
        this.togglePause();
      }
      // The hidden big city: "+" on the setup screen, but not while typing
      // in the shift code
      if (
        event.key === "+" &&
        !document.getElementById("game-setup").hidden &&
        !(event.target instanceof HTMLInputElement)
      ) {
        this._setCity(this.city === "big" ? "standard" : "big");
      }
    });
  }

  /**
   * Pre-select the setup screen from a link, e.g.
   * #game?market=busy&card=platform&code=friday. Unknown values are
   * ignored; older links' difficulty=rookie|pro stand for helper|platform.
   * @param {URLSearchParams} params
   */
  applyLinkParams(params) {
    if (!this.offerCard) return; // no Game tab markup (see setupEventHandlers)
    const market = params.get("market");
    if (MARKETS.includes(market)) {
      document.querySelector(`input[name="game-market"][value="${market}"]`).checked = true;
    }
    const card = params.get("card") ?? LEGACY_CARDS[params.get("difficulty")];
    if (CARDS.includes(card)) {
      this._selectCard(card);
    }
    const code = params.get("code");
    if (code) {
      document.getElementById("game-code").value = code.slice(0, 32);
    }
    this._setCity(params.get("city") === "big" ? "big" : "standard", false);
    if (!document.getElementById("game-setup").hidden) {
      this._refreshSetupBoard();
    }
  }

  /**
   * A link that opens this shift's setup screen: same market, offer screen
   * and code, so a friend plays on the same leaderboard (see applyLinkParams).
   */
  shiftLink(shift) {
    const params = new URLSearchParams({
      market: shift.market,
      card: shift.card,
      code: shift.code,
    });
    if (shift.city === "big") params.set("city", "big");
    return `${window.location.origin}${window.location.pathname}#game?${params}`;
  }

  /** True when the Game tab is the visible tab. */
  isActive() {
    return document.getElementById("scroll-tab-game")?.classList.contains("is-active");
  }

  /** Called when the Game tab is selected: back to the setup screen. */
  resetUIAndSimulation() {
    this.stop();
    this._showScreen("setup");
  }

  /** Called when another tab is selected. */
  leave() {
    this.stop();
  }

  _showScreen(name) {
    for (const screen of ["setup", "play", "debrief"]) {
      document.getElementById(`game-${screen}`).hidden = screen !== name;
    }
    if (name === "setup") this._refreshSetupBoard();
  }

  /** The offer screen last played on this browser (default: the helper). */
  _loadCard() {
    try {
      const card = localStorage.getItem(CARD_KEY);
      return CARDS.includes(card) ? card : "helper";
    } catch {
      return "helper";
    }
  }

  _saveCard(card) {
    try {
      localStorage.setItem(CARD_KEY, card);
    } catch {
      // storage unavailable: the choice just isn't remembered
    }
  }

  _selectCard(card) {
    document.querySelector(`input[name="game-card"][value="${card}"]`).checked = true;
  }

  /** Switch between the standard and the big city (see CITY_SIZES). */
  _setCity(city, refresh = true) {
    this.city = city;
    document.getElementById("game-big-city").hidden = city !== "big";
    if (refresh) this._refreshSetupBoard();
  }

  /** The market, offer screen and code chosen on the setup screen. */
  _setupChoice() {
    return {
      market: document.querySelector('input[name="game-market"]:checked').value,
      card: document.querySelector('input[name="game-card"]:checked').value,
      code: document.getElementById("game-code").value.trim() || todayCode(),
      city: this.city,
    };
  }

  _refreshSetupBoard() {
    renderBoardPreview(document.getElementById("game-setup-board"), this._setupChoice());
  }

  _post(message) {
    window.w.postMessage(message);
  }

  start(shift = null) {
    this.stop();
    this.shift = shift || this._setupChoice();
    this._saveCard(this.shift.card);
    document.getElementById("game-shift-label").textContent = [
      this.shift.city === "big" ? "Big city" : null,
      MARKET_LABELS[this.shift.market],
      CARD_LABELS[this.shift.card],
    ]
      .filter(Boolean)
      .join(" · ");
    const citySize = CITY_SIZES[this.shift.city] ?? CITY_SIZES.standard;
    this.shift.endedEarly = false;
    // Set if the player pauses while an offer is up (extra time to decide):
    // such a shift can't go on the leaderboard
    this.shift.pausedOnOffer = false;
    // The address bar names the shift being played, ready to share
    history.replaceState(
      null,
      "",
      this.shiftLink(this.shift).slice(window.location.origin.length),
    );
    this.settings = {
      name: "gameSimSettings",
      game: true,
      market: this.shift.market,
      card: this.shift.card,
      code: this.shift.code,
      city: this.shift.city,
      action: SimulationActions.Play,
      frameIndex: 0,
      chartType: CHART_TYPES.MAP,
      citySize,
      timeBlocks: SHIFT_BLOCKS,
      animationDelay:
        citySize <= INTERPOLATE_MAX_CITY_SIZE ? FRAME_DELAY_MS : 2 * FRAME_DELAY_MS,
      gameWarpBusy: WARP_BUSY,
      gameWarpIdle: WARP_IDLE,
    };
    this.lastGame = null;
    this.shownOfferTrip = null;
    this._showScreen("play");
    document.getElementById("game-loading").hidden = false;
    document.getElementById("game-pause").textContent = "Pause";
    this._setStatusFrozen(false);
    this._renderHud(null);
    initMap(
      { ctxMap: document.getElementById("game-map-canvas").getContext("2d") },
      { citySize },
    );
    this.state = "starting";
    this._post({ ...this.settings });
  }

  /** Stop any running shift and clear the map overlay. */
  stop() {
    if (this.offerCard) this.offerCard.hide();
    if (this.offerCard && this.settings && ["starting", "playing", "paused", "finishing"].includes(this.state)) {
      this.settings.action = SimulationActions.Pause;
      this._post({ ...this.settings });
    }
    setGameOverlay(null);
    this.state = "setup";
  }

  togglePause() {
    if (this.offerCard.visible) {
      this._toggleOfferPause();
      return;
    }
    if (this.state === "playing") {
      this.settings.action = SimulationActions.Pause;
      this._post({ ...this.settings });
      this.state = "paused";
      this._setStatusFrozen(true);
      document.getElementById("game-pause").textContent = "Resume";
    } else if (this.state === "paused") {
      this.settings.action = SimulationActions.Play;
      // A non-zero frameIndex resumes the existing shift instead of starting
      // a new one
      this.settings.frameIndex = 1;
      this._post({ ...this.settings });
      this.state = "playing";
      this._setStatusFrozen(false);
      document.getElementById("game-pause").textContent = "Pause";
    }
  }

  /**
   * Pause with an offer on screen: only the card's countdown stops. The
   * worker is already frozen until the decision arrives, and a Pause message
   * would drop its hold on the offer, so nothing is sent to it.
   */
  _toggleOfferPause() {
    const button = document.getElementById("game-pause");
    if (this.state === "playing") {
      this.offerCard.pause();
      this.shift.pausedOnOffer = true;
      this.state = "paused";
      button.textContent = "Resume";
    } else if (this.state === "paused") {
      this.offerCard.resume();
      this.state = "playing";
      button.textContent = "Pause";
    }
  }

  endEarly() {
    if (!["playing", "paused"].includes(this.state)) return;
    this.offerCard.hide();
    this.settings.action = SimulationActions.Pause;
    this._post({ ...this.settings });
    this.shift.endedEarly = true;
    this._finish();
  }

  _finish() {
    this.state = "finishing";
    setGameOverlay(null);
    this._post({ action: SimulationActions.GetGameResults });
  }

  _sendDecision(accept, timedOut) {
    if (!this.lastGame) return;
    this._setStatusFrozen(false);
    setGameOverlay({ ...this._overlayState(this.lastGame), offer: null });
    window.chart?.draw();
    this._post({ action: SimulationActions.GameDecision, accept, timedOut });
  }

  _overlayState(game) {
    const phase = game.player_phase;
    return {
      player: game.player,
      citySize: this.settings.citySize,
      phase,
      target: phase === "P2" ? game.player_pickup : phase === "P3" ? game.player_dropoff : null,
      offer: null,
    };
  }

  /**
   * Called by the message handler with every game frame, after plotMap.
   * @param {Map} results - the frame (as message-handler's Map)
   */
  onFrame(results) {
    const game = results.get("game");
    if (!game || !["starting", "playing"].includes(this.state)) return;
    // Pulse the player's car when the eye needs to find it: at the start
    // of the shift, and when an offer appears
    let pulse = false;
    if (this.state === "starting") {
      pulse = true;
      this.state = "playing";
      document.getElementById("game-loading").hidden = true;
    }
    this.lastGame = game;
    this._renderHud(game);
    const overlay = this._overlayState(game);
    if (game.offer && game.offer.trip_id !== this.shownOfferTrip) {
      this.shownOfferTrip = game.offer.trip_id;
      overlay.offer = game.offer;
      this._setStatusFrozen(true);
      this.offerCard.show(game.offer, game.offer_seconds, this.shift.card === "helper");
      pulse = true;
    }
    setGameOverlay(overlay);
    window.chart?.draw();
    if (pulse) pulseGameCar();
    if (game.shift_over) {
      this._finish();
    }
  }

  _renderHud(game) {
    const blocks = game ? game.shift_block : 0;
    const total = game ? game.shift_blocks : SHIFT_BLOCKS;
    const left = Math.max(0, total - blocks);
    document.getElementById("game-clock").textContent =
      `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}`;
    document.getElementById("game-clock-fill").style.width = `${(100 * blocks) / total}%`;
    document.getElementById("game-earned").textContent = money(game ? game.earnings : 0);
    document.getElementById("game-costs").textContent = money(game ? game.costs : 0);
    document.getElementById("game-rate").textContent = money(game ? game.net_per_hour : 0);
    document.getElementById("game-accepts").textContent = game
      ? `${game.accepts} of ${game.offers}`
      : "0 of 0";
    this._renderStatus(game);
    const banner = document.getElementById("game-timeout-banner");
    if (game && game.timeout_blocks_left > 0) {
      banner.textContent = `Too many declines: the platform has stopped sending you offers for ${game.timeout_blocks_left} min.`;
      banner.hidden = false;
    } else {
      banner.hidden = true;
    }
  }

  /**
   * The status box: tinted in the phase colour, and filled left to right
   * as a progress bar through a pickup or trip (leg_progress). While idle,
   * where there's no end in sight, the fill sweeps repeatedly instead
   * (style.css).
   */
  _renderStatus(game) {
    const status = document.getElementById("game-status");
    const phase = game ? game.player_phase : "";
    status.textContent = game ? PHASE_STATUS[phase] || "" : "";
    const progress = game?.leg_progress ?? 0;
    if (status.dataset.phase !== phase) {
      // A new leg starts empty: no sliding back from the last one's fill
      status.classList.add("is-new-leg");
      status.style.setProperty("--progress", progress);
      status.dataset.phase = phase;
      void status.offsetWidth;
      status.classList.remove("is-new-leg");
    } else {
      status.style.setProperty("--progress", progress);
    }
  }

  /** Stop or restart the idle sweep while the world is frozen. */
  _setStatusFrozen(frozen) {
    document.getElementById("game-status").classList.toggle("is-frozen", frozen);
  }

  /** Called by the message handler with the end-of-shift results. */
  showDebrief(results) {
    if (this.state !== "finishing") return;
    this.state = "debrief";
    const container = document.getElementById("game-debrief");
    const shareLine = renderDebrief(container, results, {
      ...this.shift,
      link: this.shiftLink(this.shift),
    });
    this._showScreen("debrief");
    container.scrollIntoView({ block: "start" });
    renderLeaderboard(document.getElementById("game-leaderboard"), this.shift, results.player);
    document.getElementById("game-share-copy").addEventListener("click", async (event) => {
      try {
        await navigator.clipboard.writeText(shareLine);
        event.currentTarget.textContent = "Copied";
      } catch {
        document.getElementById("game-share-line").select();
      }
    });
    document.getElementById("game-again").addEventListener("click", () =>
      this.start({ ...this.shift }),
    );
    document.getElementById("game-new").addEventListener("click", () => {
      this.state = "setup";
      this._showScreen("setup");
    });
  }
}
