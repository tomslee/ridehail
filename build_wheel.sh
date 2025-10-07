#!/bin/bash

# Build script for ridehail wheel package
# Extracts version from pyproject.toml, builds wheel, and updates web interface

set -e  # Exit on error

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Building ridehail wheel package...${NC}"

# Extract version from pyproject.toml
VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

if [ -z "$VERSION" ]; then
    echo -e "${YELLOW}Error: Could not extract version from pyproject.toml${NC}"
    exit 1
fi

echo -e "${GREEN}Version: ${VERSION}${NC}"

# Build the wheel
echo -e "${BLUE}Building wheel with uv...${NC}"
uv build --wheel --package ridehail

# Check if build succeeded
WHEEL_FILE="dist/ridehail-${VERSION}-py3-none-any.whl"
if [ ! -f "$WHEEL_FILE" ]; then
    echo -e "${YELLOW}Error: Wheel file not found at ${WHEEL_FILE}${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Wheel built: ${WHEEL_FILE}${NC}"

# Copy to docs/lab/dist/
echo -e "${BLUE}Copying wheel to docs/lab/dist/...${NC}"
mkdir -p docs/lab/dist
cp "$WHEEL_FILE" docs/lab/dist/

echo -e "${GREEN}✓ Wheel copied to docs/lab/dist/${NC}"

# Update version in webworker.js
WEBWORKER_FILE="docs/lab/webworker.js"
if [ -f "$WEBWORKER_FILE" ]; then
    echo -e "${BLUE}Updating version in ${WEBWORKER_FILE}...${NC}"

    # Use sed to replace the version in the micropip.install line
    # Pattern matches: ridehail-X.Y.Z-py3-none-any.whl
    sed -i "s/ridehail-[0-9.]*-py3-none-any\.whl/ridehail-${VERSION}-py3-none-any.whl/g" "$WEBWORKER_FILE"

    echo -e "${GREEN}✓ Updated ${WEBWORKER_FILE}${NC}"
else
    echo -e "${YELLOW}Warning: ${WEBWORKER_FILE} not found${NC}"
fi

echo -e "${GREEN}Build complete!${NC}"
echo -e "Wheel file: ${WHEEL_FILE}"
echo -e "Web location: docs/lab/dist/ridehail-${VERSION}-py3-none-any.whl"
