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

# 1. Update version in pyproject.toml to today's date (YYYY.MM.DD format)
NEW_VERSION=$(date +%Y.%m.%d)
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

# 5. Build the wheel (SOURCE_DATE_EPOCH is inherited by build tools)
echo -e "${BLUE}Building wheel with uv (reproducible build)...${NC}"
uv build --wheel --package ridehail

# 6. Check if build succeeded
WHEEL_FILE="dist/ridehail-${VERSION}-py3-none-any.whl"
if [ ! -f "$WHEEL_FILE" ]; then
    echo -e "${YELLOW}Error: Wheel file not found at ${WHEEL_FILE}${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Wheel built: ${WHEEL_FILE}${NC}"

# 7. Copy versioned wheel to docs/lab/dist/
echo -e "${BLUE}Copying wheel to docs/lab/dist/...${NC}"
mkdir -p docs/lab/dist
cp "$WHEEL_FILE" docs/lab/dist/
echo -e "${GREEN}✓ Wheel copied to docs/lab/dist/${NC}"

# 8. Create version manifest for debugging
MANIFEST_FILE="docs/lab/dist/manifest.json"
echo -e "${BLUE}Creating version manifest...${NC}"
cat > "$MANIFEST_FILE" << EOF
{
  "version": "${VERSION}",
  "wheel": "ridehail-${VERSION}-py3-none-any.whl",
  "stable_wheel": "ridehail-latest.whl",
  "build_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "source_date_epoch": ${SOURCE_DATE_EPOCH}
}
EOF
echo -e "${GREEN}✓ Created ${MANIFEST_FILE}${NC}"

# 9. Git status check (optional, shows if version files changed)
echo -e "${BLUE}Changed files:${NC}"
git status --short pyproject.toml ridehail/__init__.py docs/lab/webworker.js

echo -e "${GREEN}Build complete!${NC}"
echo -e "Package version: ${VERSION}"
echo -e "SOURCE_DATE_EPOCH: ${SOURCE_DATE_EPOCH}"
echo -e "Wheel file: ${WHEEL_FILE}"
echo -e "Web deployment: docs/lab/dist/ridehail-${VERSION}-py3-none-any.whl"
echo -e ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Verify version consistency: python test/test_version.py"
echo -e "2. Test locally: python -m ridehail --version"
echo -e "3. Test web interface: cd docs/lab && python -m http.server"
echo -e "4. Commit version changes if satisfied"
echo -e ""
echo -e "${BLUE}Reproducible build:${NC}"
echo -e "Building again from the same commit will produce identical wheel files"
