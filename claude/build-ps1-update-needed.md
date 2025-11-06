# build.ps1 Windows Update - Documentation

## Status: ✅ IMPLEMENTED (Awaiting Windows Testing)

**Implementation Date**: 2024-12-06
**Implementation Status**: Complete - all changes from build.sh have been ported to build.ps1

## Current State

- `build.sh` (Linux/Mac): ✅ **UPDATED** with web animation packaging - Tested and working
- `build.ps1` (Windows): ✅ **IMPLEMENTED** with web animation packaging - Awaiting Windows testing

## What Was Implemented

The `build.ps1` file has been updated to match the new two-build process from `build.sh`. All functionality has been ported to PowerShell syntax.

### Implemented Changes (lines 54-231 in build.ps1)

The following PowerShell implementation was added:

```powershell
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

# Copy web interface files using robocopy (PowerShell equivalent of rsync)
#  /E = copy subdirectories including empty ones
#  /XD = exclude directories
robocopy docs/lab $LAB_PKG_DIR /E `
    /XD pyodide dist img .claude .vscode controllers invoices out output `
    /XF .gitignore CLAUDE.md UI_DESIGN_DECISIONS.md `
    /NFL /NDL /NJH /NJS /nc /ns /np

# Remove Read and Toronto tab components (not needed for CLI)
Remove-Item -Path "$LAB_PKG_DIR/components/read-tab.html" -ErrorAction SilentlyContinue
Remove-Item -Path "$LAB_PKG_DIR/components/toronto-tab.html" -ErrorAction SilentlyContinue

# Clean up index.html to remove Read and Toronto tabs
Write-Host "Cleaning index.html for CLI mode..."
$pythonScript = @"
import re

INDEX_FILE = 'ridehail/lab/index.html'

with open(INDEX_FILE, 'r') as f:
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

with open(INDEX_FILE, 'w') as f:
    f.write(content)

print('✓ index.html cleaned for CLI mode (removed Read and Toronto tabs)')
"@

python -c $pythonScript

# Copy wheel to CLI version
New-Item -ItemType Directory -Force -Path "$LAB_PKG_DIR/dist" | Out-Null
Copy-Item $WHEEL_FILE "$LAB_PKG_DIR/dist/"

$LAB_SIZE = (Get-ChildItem $LAB_PKG_DIR -Recurse | Measure-Object -Property Length -Sum).Sum / 1KB
Write-Green "Minimal CLI web interface created in $LAB_PKG_DIR ($([math]::Round($LAB_SIZE))KB)"
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

$FINAL_SIZE = (Get-Item $WHEEL_FILE).Length / 1KB
Write-Green "Final wheel built: $WHEEL_FILE ($([math]::Round($FINAL_SIZE))KB)"
Write-Green "  Size increase: $INITIAL_SIZE → $([math]::Round($FINAL_SIZE))KB"

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
    wheel_size = "$([math]::Round($FINAL_SIZE))KB"
    initial_size = "$INITIAL_SizeKB"
} | ConvertTo-Json

Set-Content -Path $MANIFEST_FILE -Value $manifest
Write-Green "Created $MANIFEST_FILE"
```

### Update Final Output Message

Replace the final output section (around lines 92-106) with:

```powershell
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
Write-Host "Wheel file: $WHEEL_FILE ($([math]::Round($FINAL_SIZE))KB)"
Write-Host ""
Write-Blue "Two versions created:"
Write-Host "  1. GitHub Pages (full): docs/lab/ with all tabs and images"
Write-Host "  2. PyPI CLI (minimal): $LAB_PKG_DIR/ (Experiment + What If only)"
Write-Host ""
Write-Blue "Next steps:"
Write-Host "1. Verify wheel contents: python -m zipfile -l $WHEEL_FILE | findstr lab/"
Write-Host "2. Check wheel size: Get-Item $WHEEL_FILE | Select-Object Length"
Write-Host "3. Test version: python -m ridehail --version"
Write-Host "4. Test web interface (full): cd docs/lab; python -m http.server"
Write-Host "5. Test CLI web animation: python -m ridehail test.config -a web_map"
Write-Host "6. Commit version changes if satisfied"
Write-Host ""
Write-Blue "Reproducible build:"
Write-Host "Building again from the same commit will produce identical wheel files"
```

## Key Differences from build.sh

### Directory Copying

**Linux (rsync)**:
```bash
rsync -a --exclude='pyodide/' --exclude='img/' ... docs/lab/ ridehail/lab/
```

**Windows (robocopy)**:
```powershell
robocopy docs/lab ridehail/lab /E /XD pyodide img ... /XF .gitignore ...
```

### File Size Calculation

**Linux**:
```bash
du -h file.whl  # Returns: "452K"
```

**Windows**:
```powershell
(Get-Item file.whl).Length / 1KB  # Returns: 452 (number)
$([math]::Round($size))KB  # Format as: "452KB"
```

### Python Script Execution

**Linux**:
```bash
python3 << 'PYTHON_SCRIPT'
# ... python code ...
PYTHON_SCRIPT
```

**Windows**:
```powershell
$pythonScript = @"
# ... python code ...
"@
python -c $pythonScript
```

## Testing Checklist

After implementing changes in `build.ps1`:

- [ ] Run `./build.ps1` on Windows
- [ ] Verify final wheel size (~452KB)
- [ ] Check wheel contents: `python -m zipfile -l dist/ridehail-*.whl`
- [ ] Verify no img/ directory in wheel
- [ ] Verify no read-tab.html or toronto-tab.html in wheel
- [ ] Test development mode: `python -m ridehail test.config -a web_map`
- [ ] Install from wheel: `pip install dist/ridehail-*.whl --force-reinstall`
- [ ] Test installed mode: `python -m ridehail test.config -a web_map`

## Known Issues / Considerations

1. **robocopy vs rsync**: robocopy has different behavior for excludes. May need adjustment.
2. **Python heredoc**: PowerShell's `@" ... "@` has different quoting rules than bash heredoc.
3. **Path separators**: Windows uses `\` but PowerShell usually handles `/` correctly.
4. **File size formatting**: Need to round and append "KB" manually in PowerShell.
5. **Error handling**: robocopy returns non-zero exit codes for "successful" copies (exit code 1 = files copied).

## Alternative Approach

If robocopy proves problematic, consider using PowerShell native commands:

```powershell
Copy-Item docs/lab/* $LAB_PKG_DIR -Recurse `
    -Exclude pyodide,dist,img,.claude,.vscode,CLAUDE.md,*.gitignore `
    -ErrorAction SilentlyContinue
```

However, this may not handle nested excludes as well as robocopy.

## References

- Current `build.ps1`: Lines 1-107
- Updated `build.sh`: Lines 52-205 (reference implementation)
- `claude/web-animations-pypi-package-plan.md`: Full specification

---

**Last Updated**: 2024-12-06
**Status**: Awaiting Windows testing and implementation
**Priority**: Medium (Windows users need this for full web animation support)
