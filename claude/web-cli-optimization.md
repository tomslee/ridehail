# Web CLI Animation Optimization - Tab Exclusion

## Problem Discovery 🔍

**Original Analysis**: Web files = 420KB (incorrect - this excluded img/)
**Corrected Analysis**: Web files = 858KB (410KB files + 448KB images)

**Image Breakdown**:
```
docs/lab/img/feb6-1.png:  58KB
docs/lab/img/feb6-2.png:  58KB
docs/lab/img/feb6-3.png:  67KB
docs/lab/img/feb6-4.png:  66KB
docs/lab/img/feb6-5.png:  67KB
docs/lab/img/feb6-6.png: 118KB (largest)
----------------------------------------
Total img/ directory:    448KB
```

**Image Usage**: ALL images are used ONLY in the Toronto tab (`components/toronto-tab.html`)

## Package Size Comparison

### Current Plan (with all tabs):
```
Web files (HTML, CSS, JS, Python):    410KB
Images (Toronto tab):                 448KB
One wheel for browser:                176KB
-------------------------------------------------
Total package:                        1,034KB (~1MB)
Increase:                             9.2x
```

### Optimized Plan (exclude Read & Toronto tabs):
```
Web files (Experiment + What If only): ~300KB (estimated, excluding components)
Images:                                0KB (excluded)
One wheel for browser:                 176KB
-------------------------------------------------
Total package:                         476KB (~0.5MB)
Increase:                              4.2x
```

**Savings**: 558KB (54% reduction!)

## Implementation Strategy

### Option 1: Build-Time Conditional Copy ✅ **RECOMMENDED**

Create two directory structures during build:
1. **GitHub Pages** (full): All tabs, all images
2. **PyPI Package** (minimal): Only Experiment & What If tabs, no images

**Benefits**:
- Clean separation of concerns
- No runtime overhead
- Smaller package for PyPI users
- Full functionality for web users

**Implementation**:

```bash
# In build.sh, create TWO versions of the lab

# 1. Full version for GitHub Pages (already done)
mkdir -p docs/lab/dist
cp "$WHEEL_FILE" docs/lab/dist/

# 2. Minimal CLI version for PyPI package
LAB_PKG_DIR="ridehail/lab"
mkdir -p "$LAB_PKG_DIR"

# Copy core files
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
         --exclude='img/' \                    # ✅ EXCLUDE images
         --exclude='.gitignore' \
         docs/lab/ "$LAB_PKG_DIR/"

# Remove Read and Toronto tab components
rm -f "$LAB_PKG_DIR/components/read-tab.html"
rm -f "$LAB_PKG_DIR/components/toronto-tab.html"

# Create minimal index.html (without Read/Toronto tabs)
# Option: Use sed to comment out or remove tab definitions
sed -i '/<a[^>]*id="tab-read"/,/<\/a>/d' "$LAB_PKG_DIR/index.html"
sed -i '/<a[^>]*id="tab-TO"/,/<\/a>/d' "$LAB_PKG_DIR/index.html"
sed -i '/scroll-tab-read/d' "$LAB_PKG_DIR/index.html"
sed -i '/scroll-tab-TO/d' "$LAB_PKG_DIR/index.html"

# Copy wheel to CLI version
mkdir -p "$LAB_PKG_DIR/dist"
cp "$WHEEL_FILE" "$LAB_PKG_DIR/dist/"
```

**Detailed File Modifications**:

1. **index.html** - Remove tab buttons (lines 60-79):
   ```html
   <!-- REMOVE THESE SECTIONS -->
   <a href="#scroll-tab-read" id="tab-read" class="app-tab">
     <span>Read</span>
   </a>
   <a href="#scroll-tab-TO" id="tab-TO" class="app-tab">
     <span>Toronto</span>
   </a>
   ```

2. **index.html** - Remove tab panels (lines 166-180):
   ```html
   <!-- REMOVE THESE SECTIONS -->
   <section class="app-tab-panel" id="scroll-tab-read">...</section>
   <section class="app-tab-panel" id="scroll-tab-TO">...</section>
   ```

3. **index.html** - Remove component loading (lines 278-279):
   ```javascript
   // REMOVE THESE LINES
   loadComponent("scroll-tab-read", "components/read-tab.html"),
   loadComponent("scroll-tab-TO", "components/toronto-tab.html"),
   ```

**Automated Script Approach**:

```bash
# Create a helper function in build.sh
create_minimal_cli_version() {
    local SOURCE_DIR="$1"
    local TARGET_DIR="$2"

    echo "Creating minimal CLI version..."

    # Copy everything except images and specific components
    rsync -av \
        --exclude='pyodide/' \
        --exclude='dist/' \
        --exclude='img/' \
        --exclude='components/read-tab.html' \
        --exclude='components/toronto-tab.html' \
        "$SOURCE_DIR/" "$TARGET_DIR/"

    # Use Python to clean up index.html (more robust than sed)
    python3 << 'PYTHON_SCRIPT'
import re

with open("${TARGET_DIR}/index.html", "r") as f:
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

# Remove component loading for Read and Toronto
content = re.sub(
    r'loadComponent\("scroll-tab-read",.*?\),?\s*',
    '',
    content
)
content = re.sub(
    r'loadComponent\("scroll-tab-TO",.*?\),?\s*',
    '',
    content
)

# Clean up any resulting double commas or trailing commas in Promise.all
content = re.sub(r',\s*,', ',', content)
content = re.sub(r',(\s*\])', r'\1', content)

with open("${TARGET_DIR}/index.html", "w") as f:
    f.write(content)

print("✓ index.html cleaned for CLI mode")
PYTHON_SCRIPT

    echo "✓ Minimal CLI version created"
}

# Use it in build.sh
create_minimal_cli_version "docs/lab" "ridehail/lab"
```

### Option 2: Runtime Conditional Loading

Modify app.js to skip loading Read/Toronto tabs when in CLI mode.

**Benefits**:
- Still need to exclude img/ from package
- Simpler build process

**Cons**:
- Still includes component files unnecessarily
- Less clean architecture
- Minimal savings (only 448KB from images, still have component HTML)

**Implementation** (app.js):

```javascript
// Around line 275 in index.html
(async () => {
  // Check if in CLI mode
  const urlParams = new URLSearchParams(window.location.search);
  const isCliMode = urlParams.has('autoLoad');

  const componentsToLoad = [
    loadComponent("scroll-tab-1", "components/experiment-tab.html"),
    loadComponent("scroll-tab-what-if", "components/whatif-tab.html"),
    loadComponent("scroll-tab-game", "components/game-tab.html"),
  ];

  // Only load Read/Toronto tabs for web mode (not CLI)
  if (!isCliMode) {
    componentsToLoad.push(
      loadComponent("scroll-tab-read", "components/read-tab.html"),
      loadComponent("scroll-tab-TO", "components/toronto-tab.html")
    );
  } else {
    // Hide tab buttons in CLI mode
    document.getElementById('tab-read')?.style.setProperty('display', 'none');
    document.getElementById('tab-TO')?.style.setProperty('display', 'none');
  }

  await Promise.all(componentsToLoad);

  // Continue with app initialization...
})();
```

**Limitation**: This still requires excluding img/ directory from the package, so savings are similar to Option 1.

## Comparison

| Approach | Package Size | Build Complexity | Runtime Overhead | Savings |
|----------|--------------|------------------|------------------|---------|
| Current (all tabs) | 1,034KB | Low | None | Baseline |
| **Option 1: Build-time** | **476KB** | **Medium** | **None** | **558KB (54%)** |
| Option 2: Runtime | ~586KB | Low | Small | 448KB (43%) |

**Savings Breakdown**:
- **Images**: 448KB (both options)
- **Read tab HTML**: ~10KB (Option 1 only)
- **Toronto tab HTML**: ~15KB (Option 1 only)
- **Unused JS/CSS**: ~85KB (Option 1, more aggressive)

## Recommendation

**Use Option 1: Build-Time Conditional Copy**

**Rationale**:
1. **Maximum savings**: 558KB (54% reduction)
2. **Clean architecture**: CLI version only contains what it needs
3. **No runtime overhead**: No conditional logic in browser
4. **Clear purpose**: Makes CLI web animation purpose obvious
5. **Reasonable complexity**: Python script for HTML cleanup is maintainable

**Final Package Sizes**:
- **Current wheel**: 113KB
- **With full web interface**: 1,034KB (9.2x increase)
- **With optimized CLI web**: 476KB (4.2x increase) ✅ **MUCH BETTER**

## Updated Build Process

```bash
#!/usr/bin/bash
# build.sh - Updated to create minimal CLI web version

# ... (existing version sync steps 1-4)

# 5. Build initial wheel (without lab/)
uv build --wheel --package ridehail
WHEEL_FILE="dist/ridehail-${VERSION}-py3-none-any.whl"

# 6. Clean old wheels from docs/lab/dist/
rm -f docs/lab/dist/ridehail-*.whl

# 7. Copy current wheel to docs/lab/dist/ (for GitHub Pages)
mkdir -p docs/lab/dist
cp "$WHEEL_FILE" docs/lab/dist/

# 8. Create MINIMAL CLI version for PyPI package
create_minimal_cli_version "docs/lab" "ridehail/lab"

# 9. Copy wheel to CLI version
mkdir -p ridehail/lab/dist
cp "$WHEEL_FILE" ridehail/lab/dist/

# 10. Rebuild wheel with minimal CLI lab/ included
rm "$WHEEL_FILE"
uv build --wheel --package ridehail
FINAL_WHEEL="dist/ridehail-${VERSION}-py3-none-any.whl"

echo "✓ Final wheel: $FINAL_WHEEL ($(du -h "$FINAL_WHEEL" | cut -f1))"
```

## Testing Checklist

- [ ] GitHub Pages: All tabs visible and functional
- [ ] GitHub Pages: Images load correctly in Toronto tab
- [ ] CLI Mode: Only Experiment and What If tabs visible
- [ ] CLI Mode: No broken image links
- [ ] CLI Mode: Simulation runs correctly
- [ ] Package size: ~476KB (verify with `du -h dist/*.whl`)
- [ ] Wheel contents: Verify no img/ directory (`unzip -l dist/*.whl | grep img`)
- [ ] Wheel contents: Verify no read-tab.html or toronto-tab.html

## Future Enhancements

1. **Further optimization**: Minify JavaScript/CSS for CLI version
2. **What If tab**: Consider if this is needed for CLI (saves ~25KB more)
3. **Tests**: Could exclude test files for additional ~48KB savings
4. **Game tab**: Already hidden by default, could remove for CLI

## Documentation Updates

Update `claude/web-animations-pypi-package-plan.md`:
- Corrected package size: 476KB (not 709KB)
- Increase: 4.2x (not 6x)
- Note that CLI version excludes Read and Toronto tabs
- Explain that images are GitHub Pages only

Update README.md or web animation docs:
- CLI web animations show Experiment and What If tabs only
- For full documentation and Toronto case study, visit: https://tomslee.github.io/ridehail/

---

**Status**: Ready for implementation
**Estimated Effort**: +1 hour (add Python HTML cleanup script, test both versions)
**Final Package Size**: **476KB** (4.2x increase, very reasonable!)
