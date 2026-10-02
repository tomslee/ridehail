#!/usr/bin/env bash
# game.sh - report on and moderate the Game tab ("Just One More Shift…")
# leaderboards (docs/lab/api/leaderboard.php).
#
# Usage:
#   ./game.sh list [-n N] [-m MARKET] [-c CARD] [-a] [-e] [CODE...]
#       CODE       shift codes to show ("today" means today's date, the game's
#                  default code); default every code with scores, newest first
#       -n N       entries per board (default 10, the site's TOP_N; 0 = all)
#       -m MARKET  only this market: busy, normal or slow
#       -c CARD    only this offer screen: helper or platform
#       -a         include scores made under older rules (marked "old"); the
#                  site leaves out versions below MIN_SCORING_VERSION
#       -e         every entry, not just each name's best
#   ./game.sh delete [-y] ID...       delete entries by id (asks first unless -y)
#
# list reads the SQLite database directly over ssh (read-only: it is copied
# to a temporary file first), so it sees every board. MIN_SCORING_VERSION is
# read from the deployed leaderboard.php so the standings match the site.
# Set SSH_TARGET to use another server.
#
# delete goes through the web API (LEADERBOARD_URL), so it never writes to
# the database at the same time as PHP. It needs the admin token, read from
# TOKEN=... in .env next to this script (.env is git-ignored). It must match
# the admin-token file in the leaderboard's data directory on the server:
# ~/domains/tomslee.net/ridehail-data/admin-token (next to public_html's real
# location; see docs/lab/api/leaderboard.php).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
URL="${LEADERBOARD_URL:-https://tomslee.net/ridehail/api/leaderboard.php}"
SSH_TARGET="${SSH_TARGET:-tomslee@tomslee.net}"
DATA_DIR="domains/tomslee.net/ridehail-data"
PHP_FILE="public_html/ridehail/api/leaderboard.php"

usage() {
  sed -n '5,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

list_boards() {
  local top=10 market="" card="" all_versions=0 every_entry=0 opt code
  local OPTIND=1
  while getopts ":n:m:c:aeh" opt; do
    case "$opt" in
      n) top="$OPTARG" ;;
      m) market="$OPTARG" ;;
      c) card="$OPTARG" ;;
      a) all_versions=1 ;;
      e) every_entry=1 ;;
      h) usage 0 ;;
      *) usage 1 ;;
    esac
  done
  shift $((OPTIND - 1))
  [[ "$top" =~ ^[0-9]+$ ]] || { echo "ERROR: -n needs a number" >&2; exit 1; }

  local codes=()
  for code in "$@"; do
    [[ "$code" == "today" ]] && code="$(date +%F)"
    codes+=("$code")
  done

  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT

  # One connection: the database on stdout, the minimum version on stderr
  if ! ssh -o BatchMode=yes "$SSH_TARGET" \
    "cat $DATA_DIR/leaderboard.sqlite && sed -n \"s/^const MIN_SCORING_VERSION = '\\(.*\\)';/\\1/p\" $PHP_FILE >&2" \
    >"$tmp/leaderboard.sqlite" 2>"$tmp/min_version"; then
    echo "ERROR: could not read the leaderboard from $SSH_TARGET:" >&2
    cat "$tmp/min_version" >&2
    exit 1
  fi
  local min_version
  min_version="$(tr -d '[:space:]' <"$tmp/min_version")"
  if ! [[ "$min_version" =~ ^[0-9][0-9.]*$ ]]; then
    echo "WARNING: MIN_SCORING_VERSION not found in $PHP_FILE; showing all versions" >&2
    min_version=""
  fi

  python3 - "$tmp/leaderboard.sqlite" "$min_version" "$top" "$market" "$card" \
    "$all_versions" "$every_entry" "${codes[@]}" <<'PYTHON'
import re, sqlite3, sys

path, min_version, top, market, card, all_versions, every_entry, *codes = sys.argv[1:]
top = int(top)
all_versions = all_versions == "1"
every_entry = every_entry == "1"
MARKETS = ["busy", "normal", "slow"]
CARDS = ["helper", "platform"]
if market and market not in MARKETS:
    sys.exit(f"Unknown market '{market}' (busy, normal or slow)")
if card and card not in CARDS:
    sys.exit(f"Unknown offer screen '{card}' (helper or platform)")


def version_key(version):
    return [int(part) for part in re.findall(r"\d+", version or "")]


def current(version):
    # As leaderboard.php's current_rules()
    return bool(version) and (not min_version or version_key(version) >= version_key(min_version))


db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
db.row_factory = sqlite3.Row
rows = db.execute(
    "SELECT * FROM scores ORDER BY net_per_hour DESC, created_at ASC, id ASC"
).fetchall()

boards = {}
for row in rows:
    if codes and row["shift_code"] not in codes:
        continue
    if (market and row["market"] != market) or (card and row["card"] != card):
        continue
    is_current = current(row["version"])
    if not (is_current or all_versions):
        continue
    boards.setdefault((row["shift_code"], row["market"], row["card"]), []).append((row, is_current))

old_note = "" if all_versions else f", scores from v{min_version} on"
print(f"Ridehail leaderboards ({len(rows)} scores in all{old_note})")
if not boards:
    print("\nNo scores match.")
    sys.exit(0)


def board_order(key):
    code, mkt, crd = key
    m = MARKETS.index(mkt) if mkt in MARKETS else 99
    c = CARDS.index(crd) if crd in CARDS else 99
    return code, -m, -c


for key in sorted(boards, key=board_order, reverse=True):
    code, mkt, crd = key
    entries = boards[key]
    names = {row["name_key"] for row, _ in entries}
    if not every_entry:
        best = {}
        for row, is_current in entries:
            best.setdefault(row["name_key"], (row, is_current))
        entries = list(best.values())
    shown = entries if top == 0 else entries[:top]
    driver_s = "driver" if len(names) == 1 else "drivers"
    print(f"\n== {code} · {mkt.capitalize()} · {crd} — {len(names)} {driver_s}")
    print(f"  {'#':>3}  {'name':<20}  {'net/hr':>8}  {'earned':>7}  {'costs':>6}  "
          f"{'accepted':>8}  {'trips':>5}  {'played (UTC)':<16}  {'id':>5}  version")
    for place, (row, is_current) in enumerate(shown, 1):
        accepted = f"{row['accepts']}/{row['offers']}"
        played = row["created_at"][:16].replace("T", " ")
        flag = "" if is_current else "  old"
        print(f"  {place:>3}  {row['name']:<20}  {row['net_per_hour']:>8.2f}  "
              f"{row['earnings']:>7.2f}  {row['costs']:>6.2f}  {accepted:>8}  "
              f"{row['trips']:>5}  {played:<16}  {row['id']:>5}  {row['version'] or ''}{flag}")
    if len(entries) > len(shown):
        print(f"  … and {len(entries) - len(shown)} more")
PYTHON
}

read_token() {
  # Read the token without sourcing .env (which may hold other settings)
  TOKEN="$(sed -n 's/^TOKEN=//p' "$SCRIPT_DIR/.env" 2>/dev/null | tail -n 1 | tr -d '\r"'"'"' ')"
  if [[ -z "$TOKEN" ]]; then
    echo "ERROR: no TOKEN=... line in $SCRIPT_DIR/.env" >&2
    exit 1
  fi
}

delete_entry() {
  local id="$1" response
  response="$(printf '{"action":"delete","token":"%s","id":%d}' "$TOKEN" "$id" |
    curl -sS -X POST -H 'Content-Type: application/json' --data-binary @- "$URL")"
  python3 - "$id" "$response" <<'PYTHON'
import json, sys
entry, raw = sys.argv[1:3]
try:
    data = json.loads(raw)
except ValueError:
    sys.exit(f"Unexpected reply from the server: {raw[:200]}")
if "error" in data:
    sys.exit(f"Entry {entry}: {data['error']}")
print(f"Entry {entry}: {'deleted' if data.get('deleted') else 'not found'}")
PYTHON
}

command="${1:-}"
[[ $# -gt 0 ]] && shift
case "$command" in
  list)
    list_boards "$@"
    ;;
  delete)
    confirm=true
    if [[ "${1:-}" == "-y" ]]; then
      confirm=false
      shift
    fi
    [[ $# -gt 0 ]] || usage 1
    for id in "$@"; do
      if ! [[ "$id" =~ ^[0-9]+$ ]]; then
        echo "ERROR: '$id' is not an entry id" >&2
        exit 1
      fi
    done
    read_token
    if $confirm; then
      read -r -p "Delete entr$([[ $# -eq 1 ]] && echo y || echo ies) $*? [y/N] " answer
      [[ "$answer" =~ ^[Yy]$ ]] || { echo "Nothing deleted."; exit 0; }
    fi
    for id in "$@"; do
      delete_entry "$id"
    done
    ;;
  -h | --help | help | "")
    usage 0
    ;;
  *)
    echo "ERROR: unknown command '$command'" >&2
    usage 1
    ;;
esac
