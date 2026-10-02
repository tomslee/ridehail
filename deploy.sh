#!/usr/bin/env bash
#
# deploy.sh — publish the Ridehail Lab web app to the self-hosted server.
#
# Syncs docs/lab/ to the "/ridehail/" sub-path of the docroot, matching the
# "Ridehail Lab" navbar item (href="/ridehail/") on the main tomslee site.
#
# The Pyodide runtime is loaded from the CDN in production (see
# docs/lab/webworker.js), so the local docs/lab/pyodide/ copy and other
# dev-only cruft are excluded from the sync. The dist/ wheel + manifest.json
# ARE required and are kept.
#
# Rebuild the wheel first (refreshes docs/lab/dist/) if the package changed:
#     ./build.sh
#
# Always preview first with:   ./deploy.sh --dry-run
#
set -euo pipefail

# ── CONFIG ──────────────────────────────────────────────────────────────
#SSH_TARGET="tomslee@salticus.web.net"
SSH_TARGET="tomslee@tomslee.net"
DOCROOT="/home/tomslee/public_html"          # no trailing slash
SUBPATH="ridehail"                            # must match the navbar href /ridehail/

# Local source: this script lives in the repo root; the app is docs/lab/.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${SCRIPT_DIR}/docs/lab/"
# ────────────────────────────────────────────────────────────────────────

RSYNC_OPTS=(-avz --delete --human-readable)
if [[ "${1:-}" == "--dry-run" || "${1:-}" == "-n" ]]; then
  RSYNC_OPTS+=(--dry-run)
  echo ">> DRY RUN — no files will be transferred"
fi

if [[ ! -d "$SRC_DIR" ]]; then
  echo "ERROR: source directory not found: $SRC_DIR" >&2
  exit 1
fi

echo ">> Syncing Ridehail Lab from ${SRC_DIR}"
echo "   to ${SSH_TARGET}:${DOCROOT}/${SUBPATH}/"
rsync "${RSYNC_OPTS[@]}" \
  --exclude='pyodide/' \
  --exclude='__pycache__/' \
  --exclude='.ruff_cache/' \
  --exclude='tests/' \
  --exclude='out/' \
  --exclude='output/' \
  --exclude='CLAUDE.md' \
  --exclude='UI_DESIGN_DECISIONS.md' \
  "$SRC_DIR" "${SSH_TARGET}:${DOCROOT}/${SUBPATH}/"

echo ">> Done."
