#!/usr/bin/bash

# Publication script for ridehail package
# Builds and publishes to TestPyPI or PyPI
# Usage: ./publish.sh [test|prod]

set -e  # Exit on error

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Ridehail Publication System${NC}"
echo ""

# Parse command line argument
TARGET="${1:-test}"

if [ "$TARGET" != "test" ] && [ "$TARGET" != "prod" ]; then
    echo -e "${RED}Error: Invalid target. Use 'test' or 'prod'${NC}"
    echo "Usage: ./publish.sh [test|prod]"
    exit 1
fi

# Confirm target
if [ "$TARGET" == "prod" ]; then
    echo -e "${RED}WARNING: You are about to publish to PRODUCTION PyPI${NC}"
    echo -e "${YELLOW}This will make the package publicly available at pypi.org${NC}"
    read -p "Are you sure? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo -e "${YELLOW}Publication cancelled${NC}"
        exit 0
    fi
else
    echo -e "${GREEN}Publishing to TestPyPI (test.pypi.org)${NC}"
fi

echo ""
echo -e "${BLUE}Step 1: Pre-publication checks${NC}"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo "Install with: pip install uv"
    exit 1
fi
echo -e "${GREEN}✓ uv is installed${NC}"

# Check if ~/.pypirc exists
if [ ! -f ~/.pypirc ]; then
    echo -e "${RED}Error: ~/.pypirc not found${NC}"
    echo "Please configure API tokens in ~/.pypirc"
    exit 1
fi
echo -e "${GREEN}✓ ~/.pypirc found${NC}"

# Check git status
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo -e "${YELLOW}Warning: You have uncommitted changes${NC}"
    git status --short
    read -p "Continue anyway? (yes/no): " CONTINUE
    if [ "$CONTINUE" != "yes" ]; then
        echo -e "${YELLOW}Publication cancelled${NC}"
        exit 0
    fi
else
    echo -e "${GREEN}✓ Git working directory is clean${NC}"
fi

echo ""
echo -e "${BLUE}Step 2: Building package${NC}"

# Run the build script
./build.sh

# Extract version from pyproject.toml
VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
WHEEL_FILE="dist/ridehail-${VERSION}-py3-none-any.whl"

if [ ! -f "$WHEEL_FILE" ]; then
    echo -e "${RED}Error: Wheel file not found at ${WHEEL_FILE}${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Wheel built: ${WHEEL_FILE}${NC}"
echo ""

# Show wheel info
echo -e "${BLUE}Package Information:${NC}"
echo "  Version: ${VERSION}"
echo "  Wheel: ${WHEEL_FILE}"
echo "  Size: $(ls -lh "$WHEEL_FILE" | awk '{print $5}')"
echo ""

# Verify wheel contents
echo -e "${BLUE}Step 3: Verifying wheel contents${NC}"
echo -e "${YELLOW}Top-level files in wheel:${NC}"
python3 -c "import zipfile; z = zipfile.ZipFile('${WHEEL_FILE}'); print('\n'.join(sorted(set([f.split('/')[0] for f in z.namelist()]))))"
echo -e "${GREEN}✓ Wheel structure looks good${NC}"
echo ""

# Final confirmation
echo -e "${BLUE}Step 4: Publishing to $([ "$TARGET" == "prod" ] && echo "PyPI" || echo "TestPyPI")${NC}"

if [ "$TARGET" == "prod" ]; then
    read -p "Final confirmation - publish to PRODUCTION PyPI? (yes/no): " FINAL_CONFIRM
    if [ "$FINAL_CONFIRM" != "yes" ]; then
        echo -e "${YELLOW}Publication cancelled${NC}"
        exit 0
    fi
fi

# Publish with uv
if [ "$TARGET" == "test" ]; then
    echo -e "${BLUE}Uploading to TestPyPI...${NC}"
    uv publish --index testpypi "$WHEEL_FILE"
    PUBLISH_URL="https://test.pypi.org/project/ridehail/${VERSION}/"
else
    echo -e "${BLUE}Uploading to PyPI...${NC}"
    uv publish "$WHEEL_FILE"
    PUBLISH_URL="https://pypi.org/project/ridehail/${VERSION}/"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Publication Successful! 🎉${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Package Details:${NC}"
echo "  Name: ridehail"
echo "  Version: ${VERSION}"
echo "  URL: ${PUBLISH_URL}"
echo ""

if [ "$TARGET" == "test" ]; then
    echo -e "${BLUE}Next Steps (Testing):${NC}"
    echo "1. View package: ${PUBLISH_URL}"
    echo "2. Test installation:"
    echo "   uv pip install --index-url https://test.pypi.org/simple/ \\"
    echo "     --extra-index-url https://pypi.org/simple/ ridehail[terminal]"
    echo ""
    echo "3. Verify it works:"
    echo "   python -m ridehail --version"
    echo "   python -m ridehail test.config -as terminal_map"
    echo ""
    echo -e "${GREEN}If tests pass, publish to production with:${NC}"
    echo "   ./publish.sh prod"
else
    echo -e "${BLUE}Next Steps (Production):${NC}"
    echo "1. View package: ${PUBLISH_URL}"
    echo "2. Test installation:"
    echo "   pip install ridehail[terminal]"
    echo ""
    echo "3. Update project-scoped token (recommended):"
    echo "   https://pypi.org/manage/project/ridehail/settings/"
    echo ""
    echo "4. Create git tag:"
    echo "   git tag -a v${VERSION} -m 'Release ${VERSION}'"
    echo "   git push origin v${VERSION}"
    echo ""
    echo -e "${GREEN}Congratulations on your PyPI release! 🚀${NC}"
fi
