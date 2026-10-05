/**
 * Game tab: the choices a shift is set up from, in one place for game-tab.js,
 * game-debrief.js and game-leaderboard.js.
 *
 * They mirror ridehail.game (MARKETS and their labels, CARDS, the city sizes
 * of CITIES, GameParams.shift_blocks); the setup screen
 * (components/game-tab.html) repeats the labels. test/test_game.py checks all
 * three agree, so SETUP must stay valid JSON: the test reads it as such.
 */

const SETUP = {
  "shiftBlocks": 180,
  "citySizes": { "standard": 32, "big": 48 },
  "markets": { "busy": "Busy Friday", "normal": "Normal", "slow": "Slow Tuesday" },
  "cards": { "helper": "Rate helper", "platform": "Platform only" }
};

// Simulated minutes in a shift (one block per minute)
export const SHIFT_BLOCKS = SETUP.shiftBlocks;
// City size in blocks of 0.37 km: the standard city (11.8 km) and the hidden
// big one (17.8 km)
export const CITY_SIZES = SETUP.citySizes;
export const MARKET_LABELS = SETUP.markets;
export const MARKETS = Object.keys(SETUP.markets);
// Offer screens: with the rate helper ($/km and $/hr on the card, as a
// third-party driver app shows them) or the platform's card alone. Each has
// its own leaderboard.
export const CARD_LABELS = SETUP.cards;
export const CARDS = Object.keys(SETUP.cards);
