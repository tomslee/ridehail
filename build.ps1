# Build script for ridehail package (Windows PowerShell version)
# Synchronizes version across all files and builds distribution
# Uses SOURCE_DATE_EPOCH for reproducible builds

$ErrorActionPreference = "Stop"

function Write-Blue { Write-Host $args -ForegroundColor Blue }
function Write-Green { Write-Host $args -ForegroundColor Green }
function Write-Yellow { Write-Host $args -ForegroundColor Yellow }

Write-Blue "Ridehail Build System"

# 1. Update version in pyproject.toml to today's date (YYYY.M.D format)
$NEW_VERSION = Get-Date -Format "yyyy.M.d"
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

# 5. Build the wheel
Write-Blue "Building wheel with uv (reproducible build)..."
uv build --wheel --package ridehail

# 6. Check if build succeeded
$WHEEL_FILE = "dist/ridehail-$VERSION-py3-none-any.whl"
if (-not (Test-Path $WHEEL_FILE)) {
    Write-Yellow "Error: Wheel file not found at $WHEEL_FILE"
    exit 1
}

Write-Green "Wheel built: $WHEEL_FILE"

# 7. Copy versioned wheel to docs/lab/dist/
Write-Blue "Copying wheel to docs/lab/dist/..."
New-Item -ItemType Directory -Force -Path docs/lab/dist | Out-Null
Copy-Item $WHEEL_FILE docs/lab/dist/
Write-Green "Wheel copied to docs/lab/dist/"

# 8. Create version manifest
$MANIFEST_FILE = "docs/lab/dist/manifest.json"
Write-Blue "Creating version manifest..."
$BUILD_DATE = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$manifest = @{
    version = $VERSION
    wheel = "ridehail-$VERSION-py3-none-any.whl"
    stable_wheel = "ridehail-latest.whl"
    build_date = $BUILD_DATE
    source_date_epoch = [int]$SOURCE_DATE_EPOCH
} | ConvertTo-Json

Set-Content -Path $MANIFEST_FILE -Value $manifest
Write-Green "Created $MANIFEST_FILE"

# 9. Git status check
Write-Blue "Changed files:"
git status --short pyproject.toml ridehail/__init__.py docs/lab/webworker.js

Write-Host ""
Write-Green "Build complete!"
Write-Host "Package version: $VERSION"
Write-Host "SOURCE_DATE_EPOCH: $SOURCE_DATE_EPOCH"
Write-Host "Wheel file: $WHEEL_FILE"
Write-Host "Web deployment: docs/lab/dist/ridehail-$VERSION-py3-none-any.whl"
Write-Host ""
Write-Blue "Next steps:"
Write-Host "1. Verify version consistency: python test/test_version.py"
Write-Host "2. Test locally: python -m ridehail --version"
Write-Host "3. Test web interface: cd docs/lab; python -m http.server"
Write-Host "4. Commit version changes if satisfied"
Write-Host ""
Write-Blue "Reproducible build:"
Write-Host "Building again from the same commit will produce identical wheel files"
