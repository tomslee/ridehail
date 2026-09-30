/**
 * Game tab: the leaderboard section of the debrief. Talks to api/leaderboard.php
 * (named top scores per shift code + market; no sign-in). Where the endpoint
 * isn't available - the GitHub Pages copy, or any server without PHP - the
 * section stays hidden.
 */

const ENDPOINT = "api/leaderboard.php";
const NAME_KEY = "ridehail.game.name";
const MARKET_LABELS = { busy: "Busy Friday", normal: "Normal", slow: "Slow Tuesday" };

function money(value) {
  const sign = value < 0 ? "−" : "";
  return `${sign}$${Math.abs(value).toFixed(2)}`;
}

function ordinal(n) {
  const rem100 = n % 100;
  const suffix =
    rem100 >= 11 && rem100 <= 13 ? "th" : ["th", "st", "nd", "rd"][n % 10] || "th";
  return `${n}${suffix}`;
}

function escapeHtml(text) {
  return String(text).replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );
}

function loadName() {
  try {
    return localStorage.getItem(NAME_KEY) || "";
  } catch {
    return "";
  }
}

function saveName(name) {
  try {
    localStorage.setItem(NAME_KEY, name);
  } catch {
    // Storage unavailable: the name just isn't remembered
  }
}

/** Parse a JSON response, or null if the endpoint isn't really there. */
async function readJson(response) {
  const type = response.headers.get("Content-Type") || "";
  if (!type.includes("application/json")) return null;
  try {
    return await response.json();
  } catch {
    return null;
  }
}

async function fetchBoard(shift) {
  const params = new URLSearchParams({
    code: shift.code,
    market: shift.market,
    difficulty: shift.difficulty,
  });
  try {
    const response = await fetch(`${ENDPOINT}?${params}`, { cache: "no-store" });
    if (!response.ok) return null;
    return await readJson(response);
  } catch {
    return null;
  }
}

async function submitScore(shift, player, name) {
  const response = await fetch(ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      code: shift.code,
      market: shift.market,
      difficulty: shift.difficulty,
      name,
      version: window.app?.packageVersion || "",
      player,
    }),
  });
  const body = await readJson(response);
  if (!response.ok || !body || body.error) {
    throw new Error(body?.error || "The leaderboard isn't available right now");
  }
  return body;
}

function tableHtml(board, highlightName) {
  if (!board.top.length) {
    return '<p class="game-note">No scores yet on this board: yours could be the first.</p>';
  }
  const key = highlightName ? highlightName.toLowerCase() : null;
  const rows = board.top
    .map(
      (row) => `
      <tr class="${key && row.name.toLowerCase() === key ? "is-you" : ""}">
        <td class="num">${row.place}</td>
        <td>${escapeHtml(row.name)}</td>
        <td class="num">${money(row.net_per_hour)}</td>
      </tr>`,
    )
    .join("");
  return `
    <table class="game-table game-board-table">
      <thead><tr><th class="num"></th><th>Name</th><th class="num">Net per hour</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

/**
 * Fill the debrief's leaderboard section for a finished shift.
 * @param {HTMLElement} section - #game-leaderboard
 * @param {object} shift - {market, difficulty, code, endedEarly}
 * @param {object} player - results.player from ridehail.game
 */
export async function renderLeaderboard(section, shift, player) {
  section.hidden = true;
  const board = await fetchBoard(shift);
  if (!board || !Array.isArray(board.top)) return; // no leaderboard here
  const title = `Leaderboard: shift “${escapeHtml(shift.code)}”, ${MARKET_LABELS[shift.market]}`;
  const countText = (n) => `${n} ${n === 1 ? "driver" : "drivers"} on this board`;

  let formHtml;
  if (shift.endedEarly) {
    formHtml = '<p class="game-note">Only complete shifts can go on the leaderboard.</p>';
  } else {
    formHtml = `
      <form class="game-board-form" novalidate>
        <label for="game-board-name">Add your ${money(player.net_per_hour)}/hr to the board as</label>
        <div class="game-board-row">
          <input id="game-board-name" name="name" type="text" maxlength="20"
                 autocomplete="nickname" spellcheck="false" required
                 placeholder="Your name or nickname" value="${escapeHtml(loadName())}" />
          <button class="game-button game-button--primary" type="submit">Add my score</button>
        </div>
        <p class="game-board-message" role="status"></p>
        <p class="game-footnote">
          Your name and score are shown publicly on this board, and your best score
          under each name is kept. To limit spam, a scrambled form of your network
          address is kept for a day.
        </p>
      </form>`;
  }

  section.innerHTML = `
    <h3>${title}</h3>
    <p class="game-board-count">${countText(board.count)}</p>
    <div class="game-board-table-wrap">${tableHtml(board)}</div>
    ${formHtml}`;
  section.hidden = false;

  const form = section.querySelector("form");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = form.querySelector("input");
    const button = form.querySelector("button");
    const message = form.querySelector(".game-board-message");
    const name = input.value.trim().replace(/\s+/g, " ");
    if (!name) {
      message.textContent = "Please enter a name.";
      input.focus();
      return;
    }
    button.disabled = true;
    input.disabled = true;
    message.textContent = "Adding your score…";
    try {
      const result = await submitScore(shift, player, name);
      saveName(name);
      section.querySelector(".game-board-count").textContent = countText(result.count);
      section.querySelector(".game-board-table-wrap").innerHTML = tableHtml(result, result.name);
      const improved = result.best > player.net_per_hour;
      message.textContent = improved
        ? `Added. Your best under “${result.name}” is still ${money(result.best)}/hr: ${ordinal(result.rank)} of ${result.count}.`
        : `Added: you're ${ordinal(result.rank)} of ${result.count}.`;
      button.textContent = "Added";
    } catch (error) {
      message.textContent = error.message;
      button.disabled = false;
      input.disabled = false;
    }
  });
}
