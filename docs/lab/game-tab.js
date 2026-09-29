/*
 * Game Tab Controller: "One Shift"
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

import { SimulationActions, CHART_TYPES, MAP_CORE } from "./js/constants.js";
import { initMap } from "./modules/map.js";
import { setGameOverlay } from "./modules/game-map-overlay.js";
import { OfferCard } from "./modules/game-offer.js";
import { renderDebrief } from "./modules/game-debrief.js";

const GAME_CITY_SIZE = 24;
const SHIFT_BLOCKS = 180;
// Real time per animation frame (two frames per simulated minute) while the
// player is idle, and the time-warp factors applied by the worker: faster
// while on a trip (nothing to decide) and somewhat faster while idle.
const FRAME_DELAY_MS = 400;
const WARP_BUSY = 0.3;
const WARP_IDLE = 0.75;

const MARKETS = ["busy", "normal", "slow"];
const DIFFICULTIES = ["rookie", "pro"];

const PHASE_STATUS = {
  P1: "Idle, waiting for an offer",
  P2: "Driving to the pickup (unpaid)",
  P3: "Rider on board (paid)",
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
    document.getElementById("game-start").addEventListener("click", () => this.start());
    document.getElementById("game-pause").addEventListener("click", () => this.togglePause());
    document.getElementById("game-quit").addEventListener("click", () => this.endEarly());
    document.addEventListener("keydown", (event) => {
      if (!this.isActive() || this.offerCard.visible || event.repeat) return;
      if (event.key === " " && (this.state === "playing" || this.state === "paused")) {
        event.preventDefault();
        this.togglePause();
      }
    });
  }

  /**
   * Pre-select the setup screen from a link, e.g.
   * #game?market=busy&code=friday. Unknown values are ignored.
   * difficulty=pro is a hidden switch: Pro (5 s offers, no pay-per-minute,
   * acceptance-rate timeouts) is kept under the hood but no longer offered on
   * the setup screen, since every driver on a platform gets the same time.
   * @param {URLSearchParams} params
   */
  applyLinkParams(params) {
    if (!this.offerCard) return; // no Game tab markup (see setupEventHandlers)
    const market = params.get("market");
    if (MARKETS.includes(market)) {
      document.querySelector(`input[name="game-market"][value="${market}"]`).checked = true;
    }
    const difficulty = params.get("difficulty");
    if (DIFFICULTIES.includes(difficulty)) {
      document.querySelector(
        `input[name="game-difficulty"][value="${difficulty}"]`,
      ).checked = true;
    }
    const code = params.get("code");
    if (code) {
      document.getElementById("game-code").value = code.slice(0, 32);
    }
  }

  /**
   * A link that opens this shift's setup screen: same market and code (and
   * difficulty, only if it isn't the default - see applyLinkParams).
   */
  shiftLink(shift) {
    const params = new URLSearchParams({ market: shift.market, code: shift.code });
    if (shift.difficulty !== "rookie") {
      params.set("difficulty", shift.difficulty);
    }
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
  }

  _post(message) {
    window.w.postMessage(message);
  }

  start(shift = null) {
    this.stop();
    this.shift = shift || {
      market: document.querySelector('input[name="game-market"]:checked').value,
      difficulty: document.querySelector('input[name="game-difficulty"]:checked').value,
      code: document.getElementById("game-code").value.trim() || todayCode(),
    };
    this.shift.endedEarly = false;
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
      difficulty: this.shift.difficulty,
      code: this.shift.code,
      action: SimulationActions.Play,
      frameIndex: 0,
      chartType: CHART_TYPES.MAP,
      citySize: GAME_CITY_SIZE,
      timeBlocks: SHIFT_BLOCKS,
      animationDelay: FRAME_DELAY_MS,
      gameWarpBusy: WARP_BUSY,
      gameWarpIdle: WARP_IDLE,
    };
    this.lastGame = null;
    this.shownOfferTrip = null;
    this._showScreen("play");
    document.getElementById("game-loading").hidden = false;
    document.getElementById("game-pause").textContent = "Pause";
    this._renderHud(null);
    initMap(
      { ctxMap: document.getElementById("game-map-canvas").getContext("2d") },
      { citySize: GAME_CITY_SIZE },
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
    if (this.offerCard.visible) return; // no pausing to think
    if (this.state === "playing") {
      this.settings.action = SimulationActions.Pause;
      this._post({ ...this.settings });
      this.state = "paused";
      document.getElementById("game-pause").textContent = "Resume";
    } else if (this.state === "paused") {
      this.settings.action = SimulationActions.Play;
      // A non-zero frameIndex resumes the existing shift instead of starting
      // a new one
      this.settings.frameIndex = 1;
      this._post({ ...this.settings });
      this.state = "playing";
      document.getElementById("game-pause").textContent = "Pause";
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
    setGameOverlay({ ...this._overlayState(this.lastGame), offer: null });
    window.chart?.draw();
    this._post({ action: SimulationActions.GameDecision, accept, timedOut });
  }

  _overlayState(game) {
    const phase = game.player_phase;
    return {
      player: game.player,
      citySize: GAME_CITY_SIZE,
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
    if (this.state === "starting") {
      this.state = "playing";
      document.getElementById("game-loading").hidden = true;
    }
    this.lastGame = game;
    this._renderHud(game);
    const overlay = this._overlayState(game);
    if (game.offer && game.offer.trip_id !== this.shownOfferTrip) {
      this.shownOfferTrip = game.offer.trip_id;
      overlay.offer = game.offer;
      this.offerCard.show(game.offer, game.offer_seconds, this.shift.difficulty === "rookie");
    }
    setGameOverlay(overlay);
    window.chart?.draw();
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
    const status = document.getElementById("game-status");
    status.textContent = game ? PHASE_STATUS[game.player_phase] || "" : "";
    status.dataset.phase = game ? game.player_phase : "";
    const banner = document.getElementById("game-timeout-banner");
    if (game && game.timeout_blocks_left > 0) {
      banner.textContent = `Too many declines: the platform has stopped sending you offers for ${game.timeout_blocks_left} min.`;
      banner.hidden = false;
    } else {
      banner.hidden = true;
    }
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
