# Build script for ridehail package (Windows PowerShell version)
# Synchronizes version across all files and builds distribution
# Uses SOURCE_DATE_EPOCH for reproducible builds

$ErrorActionPreference = "Stop"

function Write-Blue { Write-Host $args -ForegroundColor Blue }
function Write-Green { Write-Host $args -ForegroundColor Green }
function Write-Yellow { Write-Host $args -ForegroundColor Yellow }

Write-Blue "Ridehail Build System"

# 1. Determine version with auto-incrementing build number (YYYY.M.D.N format)
# PEP 440 format: YYYY.M.D.N where N is the build number for the day (0, 1, 2, ...)
# This allows multiple releases per day while remaining PEP 440 compliant

$BASE_VERSION = Get-Date -Format "yyyy.M.d"

# Find existing wheels for today and determine next build number
$BUILD_NUM = 0
$existingWheels = Get-ChildItem -Path dist -Filter "ridehail-$BASE_VERSION.*.whl" -ErrorAction SilentlyContinue

if ($existingWheels) {
    # Extract build numbers from existing wheels and find the maximum
    $buildNumbers = $existingWheels | ForEach-Object {
        if ($_.Name -match "ridehail-$BASE_VERSION\.(\d+)-py3") {
            [int]$matches[1]
        }
    } | Where-Object { $_ -ne $null }

    if ($buildNumbers) {
        $MAX_BUILD = ($buildNumbers | Measure-Object -Maximum).Maximum
        $BUILD_NUM = $MAX_BUILD + 1
        Write-Yellow "Found existing wheels for $BASE_VERSION, incrementing to build $BUILD_NUM"
    }
}

$NEW_VERSION = "$BASE_VERSION.$BUILD_NUM"
Write-Blue "Updating version to $NEW_VERSION..."

$pyproject = Get-Content pyproject.toml -Raw
$pyproject = $pyproject -replace 'version = ".*"', "version = `"$NEW_VERSION`""
Set-Content -Path pyproject.toml -Value $pyproject -NoNewline
Write-Green "Updated pyproject.toml version to $NEW_VERSION"

# 2. Set SOURCE_DATE_EPOCH for reproducible builds
try {
    git rev-parse --git-dir 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $SOURCE_DATE_EPOCH = git log -1 --format=%ct
        $GIT_DATE = git log -1 --format=%ci
        $env:SOURCE_DATE_EPOCH = $SOURCE_DATE_EPOCH
        Write-Green "SOURCE_DATE_EPOCH: $SOURCE_DATE_EPOCH ($GIT_DATE)"
    }
} catch {
    $SOURCE_DATE_EPOCH = [int](Get-Date -UFormat %s)
    $env:SOURCE_DATE_EPOCH = $SOURCE_DATE_EPOCH
    Write-Yellow "Not in git repo, using current time for SOURCE_DATE_EPOCH"
}

# 3. Extract version from pyproject.toml (single source of truth)
$VERSION = (Get-Content pyproject.toml | Select-String -Pattern '^version = "(.+)"').Matches.Groups[1].Value

if (-not $VERSION) {
    Write-Yellow "Error: Could not extract version from pyproject.toml"
    exit 1
}

Write-Green "Version: $VERSION"

# 4. Update ridehail/__init__.py with version
Write-Blue "Updating version in ridehail/__init__.py..."
$init_py = Get-Content ridehail/__init__.py -Raw
$init_py = $init_py -replace '__version__ = ".*"', "__version__ = `"$VERSION`""
Set-Content -Path ridehail/__init__.py -Value $init_py -NoNewline
Write-Green "Updated ridehail/__init__.py"

# 5. Build INITIAL wheel (without lab/) for browser bundling
Write-Blue "Building initial wheel (without lab/)..."
uv build --wheel --package ridehail

# 6. Check if initial build succeeded
$WHEEL_FILE = "dist/ridehail-$VERSION-py3-none-any.whl"
if (-not (Test-Path $WHEEL_FILE)) {
    Write-Yellow "Error: Wheel file not found at $WHEEL_FILE"
    exit 1
}

$INITIAL_SIZE = [math]::Round((Get-Item $WHEEL_FILE).Length / 1KB)
Write-Green "Initial wheel built: $WHEEL_FILE ($INITIAL_SIZE KB)"

# 7. Clean old wheels from docs/lab/dist/ (prevent accumulation)
Write-Blue "Cleaning old wheels from docs/lab/dist/..."
Remove-Item -Path "docs/lab/dist/ridehail-*.whl" -ErrorAction SilentlyContinue

# 8. Copy current wheel to docs/lab/dist/ (for GitHub Pages deployment)
New-Item -ItemType Directory -Force -Path docs/lab/dist | Out-Null
Copy-Item $WHEEL_FILE docs/lab/dist/
Write-Green "Wheel copied to docs/lab/dist/ (for GitHub Pages)"

# 9. Create MINIMAL CLI version for PyPI package
Write-Blue "Creating minimal CLI web interface for PyPI package..."

$LAB_PKG_DIR = "ridehail/lab"
New-Item -ItemType Directory -Force -Path $LAB_PKG_DIR | Out-Null

# Copy web interface files, excluding:
# - pyodide/ (414MB, loaded from CDN)
# - dist/ (will add wheel separately)
# - img/ (448KB, Toronto tab images - not needed for CLI)
# - Development files and cruft
# Note: robocopy exit code 1 means "files copied successfully"
robocopy docs/lab $LAB_PKG_DIR /E /XD pyodide dist img .claude .vscode controllers invoices out output /XF .gitignore CLAUDE.md UI_DESIGN_DECISIONS.md /NFL /NDL /NJH /NJS /nc /ns /np
if ($LASTEXITCODE -ge 8) {
    Write-Yellow "Error: Failed to copy web interface files"
    exit 1
}

# Remove Read and Toronto tab components (not needed for CLI)
Remove-Item -Path "$LAB_PKG_DIR/components/read-tab.html" -ErrorAction SilentlyContinue
Remove-Item -Path "$LAB_PKG_DIR/components/toronto-tab.html" -ErrorAction SilentlyContinue

# Clean up index.html to remove Read and Toronto tabs
$pythonScript = @'
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
'@

python -c $pythonScript

# Copy wheel to CLI version
New-Item -ItemType Directory -Force -Path "$LAB_PKG_DIR/dist" | Out-Null
Copy-Item $WHEEL_FILE "$LAB_PKG_DIR/dist/"

# Create manifest.json for CLI version (before rebuilding wheel)
$BUILD_DATE = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$cliManifest = @{
    version = $VERSION
    wheel = "ridehail-$VERSION-py3-none-any.whl"
    stable_wheel = "ridehail-latest.whl"
    build_date = $BUILD_DATE
    source_date_epoch = [int]$SOURCE_DATE_EPOCH
} | ConvertTo-Json

Set-Content -Path "$LAB_PKG_DIR/dist/manifest.json" -Value $cliManifest

$LAB_SIZE = [math]::Round((Get-ChildItem $LAB_PKG_DIR -Recurse | Measure-Object -Property Length -Sum).Sum / 1KB)
Write-Green "Minimal CLI web interface created in $LAB_PKG_DIR ($LAB_SIZE KB)"
Write-Green "  - Excluded: img/ (Toronto tab images)"
Write-Green "  - Excluded: Read and Toronto tab components"

# 10. Rebuild wheel with minimal CLI lab/ included
Write-Blue "Rebuilding wheel with minimal CLI web interface..."
Remove-Item $WHEEL_FILE  # Remove first build
uv build --wheel --package ridehail

# Verify final wheel exists
if (-not (Test-Path $WHEEL_FILE)) {
    Write-Yellow "Error: Final wheel file not found at $WHEEL_FILE"
    exit 1
}

$FINAL_SIZE = [math]::Round((Get-Item $WHEEL_FILE).Length / 1KB)
Write-Green "Final wheel built: $WHEEL_FILE ($FINAL_SIZE KB)"
Write-Green "  Size increase: $INITIAL_SIZE KB → $FINAL_SIZE KB"

# 11. Create version manifest (updated with size info)
$MANIFEST_FILE = "docs/lab/dist/manifest.json"
Write-Blue "Creating version manifest..."
$BUILD_DATE = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$manifest = @{
    version = $VERSION
    wheel = "ridehail-$VERSION-py3-none-any.whl"
    stable_wheel = "ridehail-latest.whl"
    build_date = $BUILD_DATE
    source_date_epoch = [int]$SOURCE_DATE_EPOCH
    wheel_size = "$FINAL_SIZE KB"
    initial_size = "$INITIAL_SIZE KB"
} | ConvertTo-Json

Set-Content -Path $MANIFEST_FILE -Value $manifest
Write-Green "Created $MANIFEST_FILE"

# 12. Git status check
Write-Blue "Changed files:"
git status --short pyproject.toml ridehail/__init__.py docs/lab/webworker.js

Write-Host ""
Write-Green "======================================"
Write-Green "Build complete!"
Write-Green "======================================"
Write-Host ""
Write-Host "Package version: $VERSION"
Write-Host "SOURCE_DATE_EPOCH: $SOURCE_DATE_EPOCH"
Write-Host "Wheel file: $WHEEL_FILE ($FINAL_SIZE KB)"
Write-Host ""
Write-Blue "Two versions created:"
Write-Host "  1. GitHub Pages (full): docs/lab/ with all tabs and images"
Write-Host "  2. PyPI CLI (minimal): $LAB_PKG_DIR/ (Experiment + What If only)"
Write-Host ""
Write-Blue "Next steps:"
Write-Host "1. Verify wheel contents: python -m zipfile -l $WHEEL_FILE | Select-String lab/"
Write-Host "2. Check wheel size: Get-Item $WHEEL_FILE | Select-Object Length"
Write-Host "3. Test version: python -m ridehail --version"
Write-Host "4. Test web interface (full): cd docs/lab; python -m http.server"
Write-Host "5. Test CLI web animation: python -m ridehail test.config -a web_map"
Write-Host "6. Commit version changes if satisfied"
Write-Host ""
Write-Blue "Reproducible build:"
Write-Host "Building again from the same commit will produce identical wheel files"
