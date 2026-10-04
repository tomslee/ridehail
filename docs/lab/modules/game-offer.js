/**
 * Game tab: the offer card. Shows one offer with a countdown and reports one
 * decision per offer: accept, decline, or timeout (which counts as a decline).
 * Keys while the card is up: → / Enter accept, ← / Esc decline.
 *
 * The card can be paused (the Game tab's Pause): the countdown stops and the
 * card stays readable, but it takes no decision until it is resumed.
 *
 * Where the card floats over the map (desktop and laptop), it can be dragged
 * out of the way of the route. The offset is kept for later offers and held
 * inside the map area. On tablets and phones it sits in the layout instead.
 */

const TIMER_RADIUS = 19;
const TIMER_CIRCUMFERENCE = 2 * Math.PI * TIMER_RADIUS;

function money(value) {
  return `$${value.toFixed(2)}`;
}

/** Durations as a platform offer words them: "1 min", "13 mins", "2 hr 1 min". */
function duration(minutes) {
  const total = Math.round(minutes);
  const hours = Math.floor(total / 60);
  const mins = total % 60;
  const minText = `${mins} ${mins === 1 ? "min" : "mins"}`;
  if (hours === 0) return minText;
  return mins === 0 ? `${hours} hr` : `${hours} hr ${mins === 1 ? "1 min" : `${mins} min`}`;
}

/** One leg of the offer, e.g. "13 mins (10.8 km) away". */
function leg(minutes, km, suffix) {
  return `${duration(minutes)} (${km.toFixed(1)} km) ${suffix}`;
}

export class OfferCard {
  /**
   * @param {function(boolean, boolean): void} onDecision - called once per
   *   offer with (accept, timedOut)
   */
  constructor(onDecision) {
    this.onDecision = onDecision;
    this.el = document.getElementById("game-offer");
    this.arc = document.getElementById("game-offer-timer-arc");
    this.timerText = document.getElementById("game-offer-timer-text");
    this.offer = null;
    this._raf = null;
    this._deadline = 0;
    this._seconds = 0;
    this._remaining = 0;
    this.paused = false;
    this.buttons = [
      document.getElementById("game-decline"),
      document.getElementById("game-accept"),
    ];
    this.arc.style.strokeDasharray = `${TIMER_CIRCUMFERENCE}`;
    document
      .getElementById("game-accept")
      .addEventListener("click", () => this.decide(true, false));
    document
      .getElementById("game-decline")
      .addEventListener("click", () => this.decide(false, false));
    this._onKey = (event) => this._handleKey(event);
    document.addEventListener("keydown", this._onKey);
    this._dragX = 0;
    this._dragY = 0;
    this._drag = null;
    this.el.addEventListener("pointerdown", (event) => this._dragStart(event));
    this.el.addEventListener("pointermove", (event) => this._dragMove(event));
    this.el.addEventListener("pointerup", () => (this._drag = null));
    this.el.addEventListener("pointercancel", () => (this._drag = null));
  }

  get visible() {
    return this.offer !== null;
  }

  /**
   * @param {object} offer - pending offer from worker.py (ridehail.game)
   * @param {number} seconds - time allowed
   * @param {boolean} helper - the rate helper: also show the pay per km and
   *   per hour, pickup included, as the third-party apps some drivers use
   *   overlay it on the platform's card. Otherwise the platform's card alone. The comparison
   *   with the rate card is never shown: real upfront offers don't show it,
   *   and not knowing is part of what makes the decision hard. The debrief
   *   reveals it afterwards.
   */
  show(offer, seconds, helper) {
    this.offer = offer;
    this._seconds = seconds;
    document.getElementById("game-offer-price").textContent = money(offer.offer);
    document.getElementById("game-offer-per-km").textContent = money(offer.per_km);
    document.getElementById("game-offer-per-hour").textContent =
      `$${(offer.per_min * 60).toFixed(1)}`;
    document.getElementById("game-offer-rate").hidden = !helper;
    document.getElementById("game-offer-pickup").textContent = leg(
      offer.pickup_minutes,
      offer.pickup_km,
      "away",
    );
    document.getElementById("game-offer-trip").textContent = leg(
      offer.trip_minutes,
      offer.trip_km,
      "trip",
    );
    document.getElementById("game-offer-dropoff").textContent =
      offer.dropoff_zone === "core" ? "City Centre (busy area)" : "Outskirts (quieter area)";
    this.el.hidden = false;
    // The window may have been resized since the card was dragged
    this._setDrag(this._dragX, this._dragY);
    if (document.body.classList.contains("is-phone")) {
      // On phones the card covers the status pane below the map: make sure
      // it's on screen
      this.el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
    this._deadline = performance.now() + seconds * 1000;
    this._tick();
    document.getElementById("game-accept").focus({ preventScroll: true });
  }

  hide() {
    this.offer = null;
    this.el.hidden = true;
    this._stopTimer();
    this._setPaused(false);
  }

  /** Stop the countdown, keeping the card on screen. */
  pause() {
    if (!this.visible || this.paused) return;
    this._remaining = Math.max(0, this._deadline - performance.now());
    this._stopTimer();
    this._setPaused(true);
    this.timerText.textContent = "❚❚";
  }

  /** Restart the countdown from where it was paused. */
  resume() {
    if (!this.visible || !this.paused) return;
    this._setPaused(false);
    this._deadline = performance.now() + this._remaining;
    // Focus is left alone: moving it to Accept now could let the key that
    // resumed the game (space) press it on key-up
    this._tick();
  }

  /** The card is draggable only where it floats over the map. */
  get _draggable() {
    return getComputedStyle(this.el).position === "absolute";
  }

  _dragStart(event) {
    if (event.button !== 0 || event.target.closest("button, a")) return;
    if (!this._draggable) return;
    // No text selection, and focus stays on Accept for the keys
    event.preventDefault();
    this.el.setPointerCapture(event.pointerId);
    this._drag = {
      x: event.clientX - this._dragX,
      y: event.clientY - this._dragY,
    };
  }

  _dragMove(event) {
    if (!this._drag) return;
    this._setDrag(event.clientX - this._drag.x, event.clientY - this._drag.y);
  }

  /** Move the card by (dx, dy) from its home, held inside the map area. */
  _setDrag(dx, dy) {
    if (!this._draggable) return;
    const card = this.el.getBoundingClientRect();
    const area = this.el.offsetParent.getBoundingClientRect();
    // The card's position with no offset
    const left = card.left - this._dragX;
    const top = card.top - this._dragY;
    const clamp = (value, min, max) => Math.min(Math.max(value, min), Math.max(min, max));
    this._dragX = clamp(dx, area.left - left, area.right - card.width - left);
    this._dragY = clamp(dy, area.top - top, area.bottom - card.height - top);
    this.el.style.setProperty("--drag-x", `${this._dragX}px`);
    this.el.style.setProperty("--drag-y", `${this._dragY}px`);
  }

  _setPaused(paused) {
    this.paused = paused;
    this.el.classList.toggle("is-paused", paused);
    for (const button of this.buttons) button.disabled = paused;
  }

  _stopTimer() {
    if (this._raf !== null) {
      cancelAnimationFrame(this._raf);
      this._raf = null;
    }
  }

  decide(accept, timedOut) {
    if (!this.visible || this.paused) return;
    this.hide();
    this.onDecision(accept, timedOut);
  }

  _tick() {
    const remaining = Math.max(0, this._deadline - performance.now());
    const fraction = remaining / (this._seconds * 1000);
    this.arc.style.strokeDashoffset = `${TIMER_CIRCUMFERENCE * (1 - fraction)}`;
    this.arc.classList.toggle("is-urgent", remaining < 2000);
    this.timerText.textContent = `${Math.ceil(remaining / 1000)}`;
    if (remaining <= 0) {
      this.decide(false, true);
      return;
    }
    this._raf = requestAnimationFrame(() => this._tick());
  }

  _handleKey(event) {
    if (!this.visible || this.paused || event.repeat) return;
    if (event.key === "ArrowRight" || event.key === "Enter") {
      event.preventDefault();
      this.decide(true, false);
    } else if (event.key === "ArrowLeft" || event.key === "Escape") {
      event.preventDefault();
      this.decide(false, false);
    }
  }
}
