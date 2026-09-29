/**
 * Game tab: the offer card. Shows one offer with a countdown and reports one
 * decision per offer: accept, decline, or timeout (which counts as a decline).
 * Keys while the card is up: → / Enter accept, ← / Esc decline.
 */

const TIMER_RADIUS = 19;
const TIMER_CIRCUMFERENCE = 2 * Math.PI * TIMER_RADIUS;

function money(value) {
  return `$${value.toFixed(2)}`;
}

function minutesKm(minutes, km) {
  return `${Math.round(minutes)} min · ${km.toFixed(1)} km`;
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
    this.arc.style.strokeDasharray = `${TIMER_CIRCUMFERENCE}`;
    document
      .getElementById("game-accept")
      .addEventListener("click", () => this.decide(true, false));
    document
      .getElementById("game-decline")
      .addEventListener("click", () => this.decide(false, false));
    this._onKey = (event) => this._handleKey(event);
    document.addEventListener("keydown", this._onKey);
  }

  get visible() {
    return this.offer !== null;
  }

  /**
   * @param {object} offer - pending offer from worker.py (ridehail.game)
   * @param {number} seconds - time allowed
   * @param {boolean} rookie - also show the pay per minute. The comparison
   *   with the rate card is never shown: real upfront offers don't show it,
   *   and not knowing is part of what makes the decision hard. The debrief
   *   reveals it afterwards.
   */
  show(offer, seconds, rookie) {
    this.offer = offer;
    this._seconds = seconds;
    document.getElementById("game-offer-price").textContent = money(offer.offer);
    const rate = document.getElementById("game-offer-rate");
    rate.textContent = `${money(offer.per_min)} a minute, pickup included (${money(offer.per_min * 60)}/hr)`;
    rate.hidden = !rookie;
    document.getElementById("game-offer-pickup").textContent =
      `${minutesKm(offer.pickup_minutes, offer.pickup_km)} (unpaid)`;
    document.getElementById("game-offer-trip").textContent = minutesKm(
      offer.trip_minutes,
      offer.trip_km,
    );
    document.getElementById("game-offer-dropoff").textContent =
      offer.dropoff_zone === "core" ? "Downtown (busy area)" : "Outskirts (quieter area)";
    this.el.hidden = false;
    this._deadline = performance.now() + seconds * 1000;
    this._tick();
    document.getElementById("game-accept").focus({ preventScroll: true });
  }

  hide() {
    this.offer = null;
    this.el.hidden = true;
    if (this._raf !== null) {
      cancelAnimationFrame(this._raf);
      this._raf = null;
    }
  }

  decide(accept, timedOut) {
    if (!this.visible) return;
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
    if (!this.visible || event.repeat) return;
    if (event.key === "ArrowRight" || event.key === "Enter") {
      event.preventDefault();
      this.decide(true, false);
    } else if (event.key === "ArrowLeft" || event.key === "Escape") {
      event.preventDefault();
      this.decide(false, false);
    }
  }
}
