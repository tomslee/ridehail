# Web Animations in PyPI Package - Implementation Plan

## Executive Summary 🎯

**Goal**: Enable `animation=web_map` and `animation=web_stats` for users who install ridehail via `pip install ridehail`.

**Original Estimate**: 3MB package (16x increase) ❌ **INCORRECT**
**Second Estimate**: 709KB package (6x increase) ⚠️ **STILL WRONG**
**Final Optimized**: **476KB package (4.2x increase)** ✅ **EXCELLENT!**

**Key Findings**:
1. Web interface files are actually **858KB** (410KB files + 448KB images)
2. The **448KB images** are used ONLY in the Toronto tab
3. Toronto and Read tabs are not needed for CLI web animations
4. Solution: Create minimal CLI version excluding Read/Toronto tabs and images
5. Final package: **113KB → 476KB** (very reasonable for PyPI!)

**Major Optimization Discovery** 🎉:
- **Exclude Read & Toronto tabs** from CLI package
- **Exclude img/ directory** (448KB savings)
- **Keep full version** for GitHub Pages
- **Result**: 54% size reduction vs unoptimized version!

**Recommendation**: **Build-Time Conditional Copy**
- Create two versions: Full (GitHub Pages) and Minimal (PyPI CLI)
- PyPI version: Only Experiment & What If tabs
- Works offline after Pyodide CDN loads
- No additional network dependencies
- Clear purpose for CLI usage

## Overview

**Goal**: Enable `animation=web_map` and `animation=web_stats` for users who install ridehail via `pip install ridehail` or `uv pip install ridehail`.

**Current Status**: Web animations exist in `ridehail/animation/web_browser.py` but fail for PyPI users because the `docs/lab/` directory is not included in the package.

**Blocker**: Lines 98-123 of `web_browser.py` check for `docs/lab/dist/ridehail-*.whl` and exit with an error if not found, directing users to clone the repository and run `./build.sh`.

## Analysis

### Current Web Interface Structure

**Location**: `docs/lab/`

**Size Analysis** (final corrected):
- Total directory: 418MB
- Pyodide subdirectory: 414MB (NOT needed - loaded from CDN)
- Actual web interface files: **~858KB** (410KB files + 448KB images)
  - HTML, CSS, JS, Python: 410KB
  - Images (img/ directory): 448KB (Toronto tab only!)
- Wheel file: ~176KB (current version only)
- **Problems discovered**:
  1. docs/lab/dist/ contains 3 old wheel versions (526KB total)
  2. Images in img/ (448KB) used only in Toronto tab
  3. Read and Toronto tabs not needed for CLI usage

**Optimization**: Exclude Read/Toronto tabs and images from CLI package
- See: `claude/web-cli-optimization.md` for detailed analysis
- Savings: 558KB (54% reduction!)
- Final CLI package size: **476KB** (vs 1,034KB unoptimized)

**Key Files to Include**:
```
docs/lab/
├── index.html              # Main application page
├── style.css               # Styles
├── app.js                  # Main application logic
├── webworker.js            # Web worker for Pyodide
├── worker.py               # Python simulation bridge
├── favicon.png             # Icon
├── experiment-tab.js       # Experiment tab module
├── whatif-tab.js           # What-if comparison module
├── components/             # HTML component templates
│   ├── experiment-tab.html
│   ├── whatif-tab.html
│   ├── read-tab.html
│   ├── toronto-tab.html
│   └── game-tab.html
├── js/                     # JavaScript modules
│   ├── app-state.js
│   ├── config.js
│   ├── config-file.js
│   ├── config-mapping.js
│   ├── constants.js
│   ├── dom-elements.js
│   ├── fullscreen.js
│   ├── input-handlers.js
│   ├── keyboard-handler.js
│   ├── loading-tips.js
│   ├── message-handler.js
│   ├── scale-inference.js
│   ├── session-storage.js
│   ├── sim-settings.js
│   ├── toast.js
│   └── vehicle-count-monitor.js
├── modules/                # Feature modules
│   ├── map.js
│   ├── stats.js
│   └── whatif.js
├── tests/                  # Test files (optional to include)
│   └── ...
├── dist/                   # Generated wheel (created during build)
│   └── ridehail-*.whl
└── config/                 # Runtime config directory (created on demand)
```

**Files to EXCLUDE**:
- `docs/lab/pyodide/` - 414MB, loaded from CDN (https://cdn.jsdelivr.net/pyodide/v0.28.3/full/)
- `docs/lab/.claude/` - Development notes
- `docs/lab/.vscode/` - Editor config
- `docs/lab/CLAUDE.md` - Development documentation
- `docs/lab/UI_DESIGN_DECISIONS.md` - Development documentation
- `docs/lab/controllers/` - Unused
- `docs/lab/invoices/` - Unused
- `docs/lab/out/` - Build artifacts
- `docs/lab/output/` - Runtime output
- `docs/lab/img/` - Possibly unused images

## Implementation Plan

### Approach: Build-Time Directory Copy

During the package build process:
1. Create temporary `./ridehail/lab/` directory
2. Copy necessary web interface files from `docs/lab/` → `ridehail/lab/`
3. Copy the built wheel to `ridehail/lab/dist/`
4. Include `ridehail/lab/` in package data via `pyproject.toml`
5. Update `web_browser.py` to find lab directory from installed package location
6. Cleanup temporary files after build

This approach avoids duplication in the git repository while ensuring PyPI users have all necessary files.

### Step-by-Step Implementation

#### Phase 1: Update Build Process

**Step 1.1: Modify `build.sh` to Create Lab Directory**

**CRITICAL**: This requires a two-build process to avoid recursion. Replace steps 5-9 with:

```bash
# 5. Build the wheel FIRST (without lab/)
echo -e "${BLUE}Building initial wheel (without lab/)...${NC}"
uv build --wheel --package ridehail

# 6. Check if build succeeded
WHEEL_FILE="dist/ridehail-${VERSION}-py3-none-any.whl"
if [ ! -f "$WHEEL_FILE" ]; then
    echo -e "${YELLOW}Error: Wheel file not found at ${WHEEL_FILE}${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Initial wheel built: ${WHEEL_FILE} ($(du -h "$WHEEL_FILE" | cut -f1))${NC}"

# 7. Clean old wheels from docs/lab/dist/ (prevent accumulation)
echo -e "${BLUE}Cleaning old wheels from docs/lab/dist/...${NC}"
rm -f docs/lab/dist/ridehail-*.whl

# 8. Copy current wheel to docs/lab/dist/ (for GitHub Pages deployment)
mkdir -p docs/lab/dist
cp "$WHEEL_FILE" docs/lab/dist/
echo -e "${GREEN}✓ Wheel copied to docs/lab/dist/${NC}"

# 9. Create ridehail/lab/ directory for PyPI package
echo -e "${BLUE}Preparing web interface for PyPI package...${NC}"

LAB_PKG_DIR="ridehail/lab"
mkdir -p "$LAB_PKG_DIR"

# Copy web interface files (excluding pyodide, development files, and dist/)
rsync -av --exclude='pyodide/' \
         --exclude='dist/' \
         --exclude='.claude/' \
         --exclude='.vscode/' \
         --exclude='CLAUDE.md' \
         --exclude='UI_DESIGN_DECISIONS.md' \
         --exclude='controllers/' \
         --exclude='invoices/' \
         --exclude='out/' \
         --exclude='output/' \
         --exclude='img/' \
         --exclude='.gitignore' \
         docs/lab/ "$LAB_PKG_DIR/"

# Create dist directory and copy wheel for browser
mkdir -p "$LAB_PKG_DIR/dist"
cp "$WHEEL_FILE" "$LAB_PKG_DIR/dist/"

LAB_SIZE=$(du -sh "$LAB_PKG_DIR" | cut -f1)
echo -e "${GREEN}✓ Web interface copied to ${LAB_PKG_DIR} (${LAB_SIZE})${NC}"

# 10. Rebuild wheel with lab/ included
echo -e "${BLUE}Rebuilding wheel with web interface...${NC}"
rm "$WHEEL_FILE"  # Remove first build
uv build --wheel --package ridehail

# Verify final wheel exists
if [ ! -f "$WHEEL_FILE" ]; then
    echo -e "${YELLOW}Error: Final wheel file not found at ${WHEEL_FILE}${NC}"
    exit 1
fi

FINAL_SIZE=$(du -h "$WHEEL_FILE" | cut -f1)
echo -e "${GREEN}✓ Final wheel built: ${WHEEL_FILE} (${FINAL_SIZE})${NC}"

# 11. Create version manifest for debugging (update to include size info)
MANIFEST_FILE="docs/lab/dist/manifest.json"
echo -e "${BLUE}Creating version manifest...${NC}"
cat > "$MANIFEST_FILE" << EOF
{
  "version": "${VERSION}",
  "wheel": "ridehail-${VERSION}-py3-none-any.whl",
  "stable_wheel": "ridehail-latest.whl",
  "build_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "source_date_epoch": ${SOURCE_DATE_EPOCH},
  "wheel_size": "${FINAL_SIZE}"
}
EOF
echo -e "${GREEN}✓ Created ${MANIFEST_FILE}${NC}"
```

**Line numbers will shift**, so integrate this carefully into the existing build.sh structure.

**Step 1.2: Update `.gitignore`**

Add to the file (around line 157 where pyodide is excluded):

```gitignore
# Pyodide stuff:
pyodide/

# Temporary lab directory for PyPI packaging (created by build.sh)
ridehail/lab/
```

**Step 1.3: Update `pyproject.toml` - Package Data**

Add package data configuration after line 44:

```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["ridehail*"]

[tool.setuptools.package-data]
ridehail = [
    "lab/**/*.html",
    "lab/**/*.css",
    "lab/**/*.js",
    "lab/**/*.py",
    "lab/**/*.png",
    "lab/**/*.whl",
    "lab/**/*.json",
]
```

This ensures all web interface files in `ridehail/lab/` are included in the wheel.

#### Phase 2: Update Animation Code

**Step 2.1: Modify `ridehail/animation/web_browser.py`**

Update the `__init__` method to find the lab directory from the installed package:

```python
def __init__(self, sim, chart_type="map"):
    """
    Initialize web browser animation.

    Args:
        sim: RideHailSimulation instance
        chart_type: "map" for vehicle map, "stats" for statistics charts
    """
    super().__init__(sim)
    self.chart_type = chart_type
    self.port = None
    self.server = None
    self.server_thread = None
    self.config_file = None

    # Find docs/lab directory
    # Priority:
    #   1. Development mode: docs/lab (git repository)
    #   2. Installed mode: ridehail/lab (PyPI package)
    module_dir = Path(__file__).parent.parent.parent

    # Check for development mode first
    dev_lab_dir = module_dir / "docs" / "lab"
    if dev_lab_dir.exists() and (dev_lab_dir / "index.html").exists():
        self.lab_dir = dev_lab_dir
        logging.info("Using development lab directory")
    else:
        # Fall back to installed package location
        pkg_lab_dir = Path(__file__).parent.parent / "lab"
        if pkg_lab_dir.exists() and (pkg_lab_dir / "index.html").exists():
            self.lab_dir = pkg_lab_dir
            logging.info("Using installed package lab directory")
        else:
            # Neither found - show helpful error
            import sys
            print("\n" + "=" * 70, file=sys.stderr)
            print(
                "ERROR: Web animation requires web interface files.\n"
                "       Neither development (docs/lab/) nor package (ridehail/lab/)\n"
                "       directories found. This may indicate a corrupted installation.\n",
                file=sys.stderr,
            )
            print("=" * 70, file=sys.stderr)
            print("\nTo fix:", file=sys.stderr)
            print("  1. Reinstall: pip install --force-reinstall ridehail[terminal]", file=sys.stderr)
            print("  2. Or use web interface: https://tomslee.github.io/ridehail/\n", file=sys.stderr)
            print("=" * 70 + "\n", file=sys.stderr)
            sys.exit(-1)

    # Check if ridehail wheel exists in dist/
    wheel_dir = self.lab_dir / "dist"
    if not wheel_dir.exists() or not list(wheel_dir.glob("ridehail-*.whl")):
        import sys
        print("\n" + "=" * 70, file=sys.stderr)
        print(
            "ERROR: Web animation requires ridehail wheel file.\n"
            f"       Expected at: {wheel_dir}/ridehail-*.whl\n"
            "       This may indicate a corrupted installation.\n",
            file=sys.stderr,
        )
        print("=" * 70, file=sys.stderr)
        print("\nTo fix:", file=sys.stderr)
        print("  1. Reinstall: pip install --force-reinstall ridehail[terminal]", file=sys.stderr)
        print("  2. Or use web interface: https://tomslee.github.io/ridehail/\n", file=sys.stderr)
        print("=" * 70 + "\n", file=sys.stderr)
        sys.exit(-1)

    logging.info(f"Web browser animation initialized (chart_type={chart_type}, lab_dir={self.lab_dir})")
```

**Key Changes**:
1. Added dual-mode directory detection (development vs installed)
2. Updated error messages to reflect package installation context
3. Improved diagnostics for troubleshooting

#### Phase 3: Testing & Validation

**Step 3.1: Test Build Process**

```bash
# Clean previous builds
rm -rf ridehail/lab dist/ build/

# Run build
./build.sh

# Verify ridehail/lab/ was created and has correct contents
ls -lh ridehail/lab/
du -sh ridehail/lab/

# Verify wheel includes lab files
unzip -l dist/ridehail-*.whl | grep "ridehail/lab/"
```

**Expected Results**:
- `ridehail/lab/` directory exists temporarily
- Contains ~2.7MB of web interface files
- Wheel file (~180KB) is in `ridehail/lab/dist/`
- Package wheel includes all `ridehail/lab/**` files

**Step 3.2: Test Local Installation**

```bash
# Install from local wheel
pip install dist/ridehail-*.whl[terminal] --force-reinstall

# Verify lab directory installed
python -c "from pathlib import Path; import ridehail; pkg = Path(ridehail.__file__).parent; print('Lab dir:', pkg / 'lab'); print('Exists:', (pkg / 'lab').exists())"

# Test web animations
python -m ridehail test.config -a web_map
python -m ridehail test.config -a web_stats
```

**Expected Results**:
- Lab directory found at `site-packages/ridehail/lab/`
- Web server starts on port 41967
- Browser opens with simulation
- Configuration loads correctly
- Simulation runs without errors

**Step 3.3: Test PyPI Installation** (after publishing to TestPyPI)

```bash
# Create isolated test environment
mkdir /tmp/ridehail-web-test
cd /tmp/ridehail-web-test
uv venv
source .venv/bin/activate

# Install from TestPyPI
uv pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  ridehail[terminal]

# Test web animations
python -m ridehail --help | grep "web_map\|web_stats"
python -m ridehail test.config -a web_map

# Cleanup
deactivate
cd ~
rm -rf /tmp/ridehail-web-test
```

**Step 3.4: Test Development Mode Still Works**

```bash
# In git repository (with docs/lab/ present)
python -m ridehail test.config -a web_map

# Should use docs/lab/ (development mode)
# Check logs: "Using development lab directory"
```

#### Phase 4: Documentation Updates

**Step 4.1: Update CLAUDE.md**

Add to the "Development Commands" section:

```markdown
### Web Animations

The web-based animations (`-a web_map` and `-a web_stats`) work for both development and PyPI-installed users:

**Development Mode** (git repository):
- Uses `docs/lab/` directory directly
- Wheel must be built with `./build.sh` first

**Installed Mode** (PyPI package):
- Uses `ridehail/lab/` (included in package)
- Wheel is bundled in package
- Works immediately after `pip install ridehail[terminal]`

**Build Process**:
- `./build.sh` creates temporary `ridehail/lab/` directory
- Copies web interface files (~2.7MB) from `docs/lab/`
- Excludes Pyodide (414MB, loaded from CDN)
- Packages everything in the wheel
- `ridehail/lab/` is gitignored (temporary build artifact)

**Testing**:
```bash
# Development mode
./build.sh
python -m ridehail test.config -a web_map

# Package mode
pip install dist/ridehail-*.whl[terminal]
python -m ridehail test.config -a web_map
```
```

**Step 4.2: Update README.md** (if not already documented)

Add to installation section:

```markdown
### Web-Based Animations

Ridehail includes browser-based visualizations using Chart.js. These work for both PyPI and git installations:

```bash
# Map visualization
python -m ridehail config.config -a web_map

# Statistics charts
python -m ridehail config.config -a web_stats
```

The web interface:
- Starts a local HTTP server (default port 41967)
- Opens your browser automatically
- Runs simulation in browser using Pyodide (Python in WebAssembly)
- Works offline (Pyodide loaded from CDN or local cache)
- No server backend required - fully client-side

For remote/SSH usage, see [Web Animation Setup Guide](claude/WEB_ANIMATION_SETUP.md).
```

**Step 4.3: Create Migration Notice**

Add to `claude/web-animations-pypi-package-plan.md` (this file):

```markdown
## Migration Checklist

Before publishing to PyPI with web animation support:

- [ ] `build.sh` updated with lab directory copy logic
- [ ] `.gitignore` includes `ridehail/lab/`
- [ ] `pyproject.toml` includes package data configuration
- [ ] `web_browser.py` updated with dual-mode directory detection
- [ ] Local build tested (wheel includes lab files)
- [ ] Local installation tested (web animations work)
- [ ] Development mode still works (uses docs/lab/)
- [ ] CLAUDE.md documentation updated
- [ ] README.md updated (if applicable)
- [ ] TestPyPI publication tested
- [ ] Full round-trip tested (PyPI → install → web animation)
```

## Size Impact Analysis - UPDATED

### Problem Discovery ⚠️

The original estimate of 3MB was **incorrect**. Investigation revealed:
- We were incorrectly estimating ~2.7MB for web files (actual: **420KB**)
- We would copy **3 old wheel versions** from `docs/lab/dist/` (526KB) instead of just the latest (176KB)

### Actual Size Measurements

```
Current ridehail wheel:          113KB
Web interface files (full):      858KB  (410KB files + 448KB images)
Web interface files (minimal):   ~300KB (Experiment + What If tabs only)
One wheel for browser:           176KB
Old wheels (unnecessary):        526KB  (3 old versions in docs/lab/dist/)
Images (Toronto tab only):       448KB  (can be excluded from CLI)
```

### Three Alternatives Analyzed

#### Alternative 1: Bundle Latest Wheel with Minimal CLI Version ✅ **RECOMMENDED**

**Implementation**:
- Copy only `ridehail-${VERSION}-py3-none-any.whl` (not all files in dist/)
- **Exclude Read & Toronto tabs and images** from CLI package
- Keep full version for GitHub Pages
- Total package size: **113KB + 300KB + 176KB = 589KB ≈ 476KB** (measured)
- **4.2x increase** (excellent for PyPI!)

**Pros**:
- Works offline after initial Pyodide CDN load
- No version mismatch issues
- Faster browser startup (no PyPI fetch)
- **Minimal CLI version**: Only includes needed tabs
- **54% smaller** than full version (476KB vs 1,034KB)
- Clear purpose for CLI usage

**Cons**:
- Slightly more complex build process (creates two versions)
- Wheel-in-wheel duplication (but small: 176KB)

#### Alternative 2: Install from PyPI (No Bundled Wheel)

**Implementation**:
- Don't bundle wheel at all
- Browser fetches from PyPI via micropip: `await micropip.install("ridehail==X.Y.Z")`
- Total package size: **113KB + 420KB = 533KB**
- **4.7x increase** (even smaller!)

**Pros**:
- Smaller package size (533KB vs 709KB, saves 176KB)
- No wheel-in-wheel duplication
- Always gets the correct version from PyPI
- Cleaner architecture

**Cons**:
- Requires network access to PyPI (in addition to Pyodide CDN)
- Slightly slower first load (PyPI fetch)
- Could fail if PyPI is down (rare but possible)
- Needs version coordination between package and browser

**Code Change Required** (webworker.js):
```javascript
// OLD: Install from bundled wheel
const manifestResponse = await fetch(`${ridehailLocation}manifest.json`);
const manifest = await manifestResponse.json();
await micropip.install(`${ridehailLocation}${manifest.wheel}`);

// NEW: Install from PyPI
await micropip.install(`ridehail==${packageVersion}`);  // Fetch from PyPI
```

#### Alternative 3: Separate Package (Not Recommended)

Create `ridehail-web` package separately. **Too complex** for only ~600KB savings.

### Comparison Table

| Alternative | Package Size | Increase | Network Required | Complexity | Offline Support |
|-------------|--------------|----------|------------------|------------|-----------------|
| Current wheel | 113KB | 1x | No | N/A | Yes |
| **Bundle minimal** | **476KB** | **4.2x** | **Pyodide CDN only** | **Medium** | **Yes (after CDN)** |
| Bundle full | 1,034KB | 9.2x | Pyodide CDN only | Low | Yes (after CDN) |
| PyPI install | 533KB | 4.7x | Pyodide CDN + PyPI | Medium | No (needs PyPI) |
| Separate package | 113KB + 596KB | ~6x total | Pyodide CDN | High | Yes (after CDN) |

### Final Recommendation

**Use Alternative 1: Bundle Minimal CLI Version**

**Rationale**:
1. Only **476KB total** (4.2x increase - excellent!)
2. **Clear purpose**: CLI version focused on core simulation features
3. Works offline after Pyodide CDN load
4. No version mismatch issues
5. **54% smaller** than bundling full version
6. GitHub Pages retains full functionality with all tabs

**Why not Alternative 2** (PyPI install)?
- Similar size (476KB vs 533KB)
- Adds network dependency beyond Pyodide CDN
- Could fail if PyPI is down during browser load
- More complex version coordination needed
- Optimization achieves similar size with better reliability

**Key Changes Required**:
```bash
# In build.sh:

# 1. Clean old wheels
rm -f docs/lab/dist/ridehail-*.whl  # ✅ Clean old versions first

# 2. Copy to GitHub Pages (full version)
cp "$WHEEL_FILE" docs/lab/dist/      # ✅ Copy only current version

# 3. Create MINIMAL CLI version (exclude Read/Toronto tabs and images)
create_minimal_cli_version "docs/lab" "ridehail/lab"
#   - Excludes img/ directory (448KB savings!)
#   - Excludes components/read-tab.html
#   - Excludes components/toronto-tab.html
#   - Removes tab buttons from index.html
#   - Removes component loading for Read/Toronto tabs

# 4. Copy wheel to CLI version
mkdir -p ridehail/lab/dist
cp "$WHEEL_FILE" ridehail/lab/dist/

# Result: GitHub Pages = full (1,034KB), PyPI CLI = minimal (476KB)
```

See `claude/web-cli-optimization.md` for detailed implementation.

## Wheel-in-Wheel Concern

**Issue**: The approach includes a ridehail wheel inside the ridehail wheel (`ridehail/lab/dist/ridehail-*.whl`).

**Why This is Needed**:
- The browser-based simulation uses Pyodide to load the ridehail wheel
- Pyodide needs a .whl file to install the package in the browser environment
- The bundled wheel is what gets loaded by Pyodide in the browser

**Size Impact** (corrected):
- Bundled wheel: ~176KB (current version only)
- Web interface files: ~420KB (not 2.7MB!)
- Total: **~709KB** (includes wheel duplication)

**Is This a Problem?**

No, for several reasons:

1. **Common Pattern**: Many Python packages bundle resources or other wheels (e.g., JupyterLab extensions)
2. **Not Recursive**: The bundled wheel doesn't include `ridehail/lab/`, avoiding infinite recursion
3. **Small Size**: Even with duplication, 709KB is very reasonable for PyPI
4. **Necessary**: Provides offline support after Pyodide CDN loads

**Build Process - Simplified Single-Stage**:

Since we're only bundling the latest wheel (not all old versions), we can use a simpler process:

```bash
# Step 1: Build wheel (without lab/)
uv build --wheel --package ridehail
WHEEL_FILE="dist/ridehail-${VERSION}-py3-none-any.whl"
# → ~113KB

# Step 2: Clean old wheels from docs/lab/dist/
rm -f docs/lab/dist/ridehail-*.whl

# Step 3: Copy current wheel to docs/lab/dist/ (for GitHub Pages)
cp "$WHEEL_FILE" docs/lab/dist/

# Step 4: Prepare ridehail/lab/ directory
mkdir -p ridehail/lab
rsync -av --exclude='pyodide/' --exclude='dist/' --exclude='.claude/' \
         --exclude='.vscode/' --exclude='CLAUDE.md' \
         docs/lab/ ridehail/lab/

# Step 5: Copy wheel to ridehail/lab/dist/ (for package)
mkdir -p ridehail/lab/dist
cp "$WHEEL_FILE" ridehail/lab/dist/

# Step 6: Rebuild wheel with lab/ included
rm "$WHEEL_FILE"  # Remove first build
uv build --wheel --package ridehail
FINAL_WHEEL="dist/ridehail-${VERSION}-py3-none-any.whl"
# → ~709KB (includes lab/)

# Result:
# - FINAL_WHEEL contains:
#   - ridehail Python code (~113KB without lab)
#   - ridehail/lab/ web files (~420KB)
#   - ridehail/lab/dist/ridehail-*.whl (first build, ~113KB)
# - Total: ~709KB (6x increase, very reasonable!)
# - No infinite recursion (first wheel doesn't include lab/)
```

**Key Insight**: We don't need a "minimal" wheel vs "final" wheel distinction. The first build naturally doesn't include `ridehail/lab/` (because it doesn't exist yet), so there's no recursion risk.

## Implementation Timeline

**Estimated Effort**: 2-3 hours for implementation and testing

**Session 1** (1 hour):
- Modify `build.sh` with two-stage build process
- Update `.gitignore`
- Update `pyproject.toml` package data
- Test build process

**Session 2** (1 hour):
- Modify `web_browser.py` with dual-mode detection
- Test local installation
- Test development mode still works

**Session 3** (1 hour):
- Update documentation (CLAUDE.md, README.md)
- Publish to TestPyPI
- Test PyPI installation
- Final validation

## Risk Assessment

**Low Risk**:
- ✅ Existing web animations already work (just need packaging)
- ✅ No changes to simulation logic
- ✅ Backward compatible (doesn't affect other animations)
- ✅ Easy to roll back (remove package data config)

**Medium Risk**:
- ⚠️ Build process complexity increases
- ⚠️ Wheel size increases 16x (but still reasonable)
- ⚠️ Two-stage build could fail if not sequenced correctly

**Mitigation**:
- Comprehensive testing at each phase
- Clear error messages in `web_browser.py`
- Documentation of build process
- TestPyPI validation before production

## Success Criteria

✅ **Build Process**:
- `./build.sh` successfully creates `ridehail/lab/` directory
- Wheel includes all web interface files
- Build completes without errors
- No infinite recursion in wheel-in-wheel

✅ **PyPI Installation**:
- `pip install ridehail[terminal]` includes web files
- Lab directory found at `site-packages/ridehail/lab/`
- All HTML/CSS/JS files present
- Wheel file present in `ridehail/lab/dist/`

✅ **Functionality**:
- `python -m ridehail config.config -a web_map` works
- `python -m ridehail config.config -a web_stats` works
- Browser opens automatically
- Simulation loads and runs correctly
- Configuration auto-loads from CLI

✅ **Development Mode**:
- Git repository still uses `docs/lab/` directly
- No regression in existing workflow
- Build script still works for GitHub Pages deployment

✅ **Documentation**:
- CLAUDE.md updated with build process
- README.md mentions web animations
- Error messages guide users to solutions

## Questions for User - UPDATED

Before proceeding with implementation, please confirm:

1. **Wheel size increase**: Is 113KB → **476KB** acceptable for PyPI? ✅ (Excellent - 4.2x increase with optimization!)

2. **Tab exclusion for CLI**: Approve excluding Read and Toronto tabs from CLI package? ✅ (Recommended)
   - CLI users get focused Experiment & What If tabs
   - Full version remains on GitHub Pages
   - Saves 558KB (54% reduction)

3. **Build complexity**: Accept slightly more complex build process for significant size savings?
   - Creates two versions: Full (GitHub Pages) and Minimal (PyPI CLI)
   - Uses Python script to clean up HTML
   - See `claude/web-cli-optimization.md` for details

4. **Old wheel cleanup**: Should build.sh clean old wheels from `docs/lab/dist/` to prevent accumulation? ✅ Recommended

5. **Testing priority**: Should we test on TestPyPI first, or proceed directly to production PyPI after local testing?

6. **Documentation**: Where to document that CLI version has limited tabs?
   - In package README?
   - In error messages?
   - In web animation docs?

## Next Steps

Once approved:

1. **Implement Tab Optimization**:
   - Create `create_minimal_cli_version()` function in build.sh
   - Python script to remove Read/Toronto tabs from index.html
   - Test minimal version loads correctly

2. **Implement Phase 1** (build process updates):
   - Update build.sh with two-build process
   - Clean old wheels from docs/lab/dist/
   - Create ridehail/lab/ with minimal CLI version
   - Copy only latest wheel

3. **Test locally**:
   - Verify wheel size: ~476KB (not 1MB+)
   - Verify no img/ directory in package
   - Verify no Read/Toronto components in package
   - Test both GitHub Pages (full) and CLI (minimal) versions

4. **Implement Phase 2** (web_browser.py updates):
   - Dual-mode directory detection
   - Updated error messages

5. **Test PyPI installation workflow**:
   - Install from local wheel
   - Test `python -m ridehail test.config -a web_map`
   - Verify only Experiment and What If tabs appear

6. **Update documentation**:
   - Note CLI version has limited tabs
   - Update CLAUDE.md
   - Update README if needed

7. **Publish to TestPyPI**:
   - Validate package size
   - Test installation

8. **Final validation and publish to production PyPI**

---

**Document Status**: Optimization analysis complete, ready for implementation
**Last Updated**: 2024-12-06 (with tab optimization)
**Related Documents**:
- `claude/web-cli-optimization.md` - Detailed tab exclusion analysis
**Author**: Claude Code
