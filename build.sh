#!/usr/bin/bash

# Build script for ridehail package
# Synchronizes version across all files and builds distribution
# Uses SOURCE_DATE_EPOCH for reproducible builds

set -e  # Exit on error

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Ridehail Build System${NC}"

# 1. Update version in pyproject.toml to today's date (YYYY.M.D format)
# Use unpadded month/day (%-m, %-d) to match PEP 440 normalization by uv build
# PEP 440 requires leading zeros to be stripped (e.g., 2025.11.01 → 2025.11.1)
# Using unpadded format from the start prevents version mismatch when uv builds
NEW_VERSION=$(date +%Y.%-m.%-d)
echo -e "${BLUE}Updating version to ${NEW_VERSION}...${NC}"
sed -i "s/^version = \".*\"/version = \"${NEW_VERSION}\"/" pyproject.toml
echo -e "${GREEN}✓ Updated pyproject.toml version to ${NEW_VERSION}${NC}"

# 2. Set SOURCE_DATE_EPOCH for reproducible builds
# Use last git commit timestamp, or current time if not in git repo
if git rev-parse --git-dir > /dev/null 2>&1; then
    export SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
    GIT_DATE=$(git log -1 --format=%ci)
    echo -e "${GREEN}SOURCE_DATE_EPOCH: ${SOURCE_DATE_EPOCH} (${GIT_DATE})${NC}"
else
    export SOURCE_DATE_EPOCH=$(date +%s)
    echo -e "${YELLOW}Not in git repo, using current time for SOURCE_DATE_EPOCH${NC}"
fi

# 3. Extract version from pyproject.toml (single source of truth)
VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

if [ -z "$VERSION" ]; then
    echo -e "${YELLOW}Error: Could not extract version from pyproject.toml${NC}"
    exit 1
fi

echo -e "${GREEN}Version: ${VERSION}${NC}"

# 4. Update ridehail/__init__.py with version
echo -e "${BLUE}Updating version in ridehail/__init__.py...${NC}"
sed -i "s/__version__ = \".*\"/__version__ = \"${VERSION}\"/" ridehail/__init__.py
echo -e "${GREEN}✓ Updated ridehail/__init__.py${NC}"

# 5. Build INITIAL wheel (without lab/) for browser bundling
echo -e "${BLUE}Building initial wheel (without lab/)...${NC}"
uv build --wheel --package ridehail

# 6. Check if initial build succeeded
WHEEL_FILE="dist/ridehail-${VERSION}-py3-none-any.whl"
if [ ! -f "$WHEEL_FILE" ]; then
    echo -e "${YELLOW}Error: Wheel file not found at ${WHEEL_FILE}${NC}"
    exit 1
fi

INITIAL_SIZE=$(du -h "$WHEEL_FILE" | cut -f1)
echo -e "${GREEN}✓ Initial wheel built: ${WHEEL_FILE} (${INITIAL_SIZE})${NC}"

# 7. Clean old wheels from docs/lab/dist/ (prevent accumulation)
echo -e "${BLUE}Cleaning old wheels from docs/lab/dist/...${NC}"
rm -f docs/lab/dist/ridehail-*.whl

# 8. Copy current wheel to docs/lab/dist/ (for GitHub Pages deployment)
mkdir -p docs/lab/dist
cp "$WHEEL_FILE" docs/lab/dist/
echo -e "${GREEN}✓ Wheel copied to docs/lab/dist/ (for GitHub Pages)${NC}"

# 9. Create MINIMAL CLI version for PyPI package
echo -e "${BLUE}Creating minimal CLI web interface for PyPI package...${NC}"

LAB_PKG_DIR="ridehail/lab"
mkdir -p "$LAB_PKG_DIR"

# Copy web interface files, excluding:
# - pyodide/ (414MB, loaded from CDN)
# - dist/ (will add wheel separately)
# - img/ (448KB, Toronto tab images - not needed for CLI)
# - Development files and cruft
rsync -a --exclude='pyodide/' \
        --exclude='dist/' \
        --exclude='img/' \
        --exclude='.claude/' \
        --exclude='.vscode/' \
        --exclude='CLAUDE.md' \
        --exclude='UI_DESIGN_DECISIONS.md' \
        --exclude='controllers/' \
        --exclude='invoices/' \
        --exclude='out/' \
        --exclude='output/' \
        --exclude='.gitignore' \
        docs/lab/ "$LAB_PKG_DIR/"

# Remove Read and Toronto tab components (not needed for CLI)
rm -f "$LAB_PKG_DIR/components/read-tab.html"
rm -f "$LAB_PKG_DIR/components/toronto-tab.html"

# Clean up index.html to remove Read and Toronto tabs
python3 << 'PYTHON_SCRIPT'
import re

INDEX_FILE = "ridehail/lab/index.html"

with open(INDEX_FILE, "r") as f:
    content = f.read()

# Remove Read tab button
content = re.sub(
    r'<a[^>]*id="tab-read"[^>]*>.*?</a>\s*',
    '',
    content,
    flags=re.DOTALL
)

# Remove Toronto tab button
content = re.sub(
    r'<a[^>]*id="tab-TO"[^>]*>.*?</a>\s*',
    '',
    content,
    flags=re.DOTALL
)

# Remove Read tab panel
content = re.sub(
    r'<section[^>]*id="scroll-tab-read"[^>]*>.*?</section>\s*',
    '',
    content,
    flags=re.DOTALL
)

# Remove Toronto tab panel
content = re.sub(
    r'<section[^>]*id="scroll-tab-TO"[^>]*>.*?</section>\s*',
    '',
    content,
    flags=re.DOTALL
)

# Remove component loading for Read and Toronto tabs
content = re.sub(
    r'loadComponent\("scroll-tab-read",[^)]*\),?\s*',
    '',
    content
)
content = re.sub(
    r'loadComponent\("scroll-tab-TO",[^)]*\),?\s*',
    '',
    content
)

# Clean up any resulting double commas or trailing commas in arrays
content = re.sub(r',\s*,', ',', content)
content = re.sub(r',(\s*\])', r'\1', content)

with open(INDEX_FILE, "w") as f:
    f.write(content)

print("✓ index.html cleaned for CLI mode (removed Read and Toronto tabs)")
PYTHON_SCRIPT

# Copy wheel to CLI version
mkdir -p "$LAB_PKG_DIR/dist"
cp "$WHEEL_FILE" "$LAB_PKG_DIR/dist/"

LAB_SIZE=$(du -sh "$LAB_PKG_DIR" | cut -f1)
echo -e "${GREEN}✓ Minimal CLI web interface created in ${LAB_PKG_DIR} (${LAB_SIZE})${NC}"
echo -e "${GREEN}  - Excluded: img/ (Toronto tab images)${NC}"
echo -e "${GREEN}  - Excluded: Read and Toronto tab components${NC}"

# 10. Rebuild wheel with minimal CLI lab/ included
echo -e "${BLUE}Rebuilding wheel with minimal CLI web interface...${NC}"
rm "$WHEEL_FILE"  # Remove first build
uv build --wheel --package ridehail

# Verify final wheel exists
if [ ! -f "$WHEEL_FILE" ]; then
    echo -e "${YELLOW}Error: Final wheel file not found at ${WHEEL_FILE}${NC}"
    exit 1
fi

FINAL_SIZE=$(du -h "$WHEEL_FILE" | cut -f1)
echo -e "${GREEN}✓ Final wheel built: ${WHEEL_FILE} (${FINAL_SIZE})${NC}"
echo -e "${GREEN}  Size increase: ${INITIAL_SIZE} → ${FINAL_SIZE}${NC}"

# 11. Create version manifest (updated with size info)
MANIFEST_FILE="docs/lab/dist/manifest.json"
echo -e "${BLUE}Creating version manifest...${NC}"
cat > "$MANIFEST_FILE" << EOF
{
  "version": "${VERSION}",
  "wheel": "ridehail-${VERSION}-py3-none-any.whl",
  "stable_wheel": "ridehail-latest.whl",
  "build_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "source_date_epoch": ${SOURCE_DATE_EPOCH},
  "wheel_size": "${FINAL_SIZE}",
  "initial_size": "${INITIAL_SIZE}"
}
EOF
echo -e "${GREEN}✓ Created ${MANIFEST_FILE}${NC}"

# 12. Git status check (optional, shows if version files changed)
echo -e "${BLUE}Changed files:${NC}"
git status --short pyproject.toml ridehail/__init__.py docs/lab/webworker.js

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Build complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "Package version: ${VERSION}"
echo -e "SOURCE_DATE_EPOCH: ${SOURCE_DATE_EPOCH}"
echo -e "Wheel file: ${WHEEL_FILE} (${FINAL_SIZE})"
echo ""
echo -e "${BLUE}Two versions created:${NC}"
echo -e "  1. GitHub Pages (full): docs/lab/ with all tabs and images"
echo -e "  2. PyPI CLI (minimal): ${LAB_PKG_DIR}/ (Experiment + What If only)"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Verify wheel contents: unzip -l ${WHEEL_FILE} | grep lab/"
echo -e "2. Check wheel size: du -h ${WHEEL_FILE}"
echo -e "3. Test version: python -m ridehail --version"
echo -e "4. Test web interface (full): cd docs/lab && python -m http.server"
echo -e "5. Test CLI web animation: python -m ridehail test.config -a web_map"
echo -e "6. Commit version changes if satisfied"
echo ""
echo -e "${BLUE}Reproducible build:${NC}"
echo -e "Building again from the same commit will produce identical wheel files"
