# Version Numbering Design Specification

## Overview

This specification defines a unified version numbering system for the ridehail simulation package that provides:
1. Single point of truth for package version
2. Command-line version display via `python -m ridehail -v`
3. Version availability in simulation results for all interfaces (desktop, web)
4. Integration with web frontend (replacing current `docs/lab/js/version.js`)
5. Automated version management in build process

## Current State Analysis

### Version Locations
- **pyproject.toml**: `version = "0.1.0"` - Package build version
- **docs/lab/js/version.js**: `VERSION = "0.24"`, `LAST_MODIFIED = "2025-10-07"` - Web frontend version
- **build_wheel.sh**: Extracts version from pyproject.toml, updates webworker.js wheel filename

### Issues
- No runtime access to package version from Python code
- Web version separate from package version
- No command-line version display
- Version not included in simulation results/metadata

## Design Goals

### 1. Single Source of Truth
**Location**: `pyproject.toml` `[project]` section

**Rationale**:
- Standard Python packaging location
- Already used by build system
- Compatible with all modern Python tooling (pip, uv, build)

### 2. Runtime Access Pattern
**Implementation**: `ridehail/__init__.py` exports `__version__`

**Pattern**:
```python
# ridehail/__init__.py
__version__ = "0.1.0"  # Synchronized with pyproject.toml

# Usage in code
from ridehail import __version__
```

### 3. Command-Line Access
**Interface**: `python -m ridehail -v` or `python -m ridehail --version`

**Output Format**:
```
ridehail 0.1.0
```

### 4. Simulation Results Integration
**Metadata Field**: Add `version` to simulation result dictionaries

**Benefits**:
- Reproducibility: Know which version generated results
- Debugging: Identify version-specific behavior
- Analysis: Track results across versions

### 5. Web Frontend Integration
**Replace**: `docs/lab/js/version.js` with version from Python package

**Method**: `worker.py` includes version in initialization message

## Implementation Plan

### Phase 1: Core Version Infrastructure

#### Step 1.1: Add Version to Package Init
**File**: `ridehail/__init__.py`

**Changes**:
```python
"""Ridehail simulation package."""

__version__ = "0.1.0"

# Existing imports...
```

**Rationale**: Standard Python convention, enables `from ridehail import __version__`

#### Step 1.2: Add Version CLI Support
**File**: `ridehail/__main__.py`

**Changes**:
```python
import sys
from ridehail import __version__

def main():
    # Handle version flags before config parsing
    if "--version" in sys.argv or "-v" in sys.argv:
        print(f"ridehail {__version__}")
        return 0

    # Existing main logic...
```

**Test**:
```bash
python -m ridehail --version
python -m ridehail -v
uv run -m ridehail --version
```

**Expected Output**: `ridehail 0.1.0`

#### Step 1.3: Add Version to RideHailConfig
**File**: `ridehail/config.py`

**Changes**:
```python
from ridehail import __version__

class RideHailConfig:
    def __init__(self, *args, **kwargs):
        # ... existing init code ...

        # Add version configuration item
        self.version = ConfigItem(
            "version",
            __version__,
            str,
            "Package version",
            "DEFAULT",
            is_exposed=False  # Internal, not user-configurable
        )
```

**Benefits**: Version accessible throughout simulation code

### Phase 2: Simulation Results Integration

#### Step 2.1: Add Version to Simulation Results
**File**: `ridehail/simulation.py`

**Changes**:
```python
def get_results(self) -> dict:
    """Return simulation results with metadata."""
    results = {
        "version": self.config.version.value,  # Add version
        "config": {
            # Existing config export...
        },
        "metrics": {
            # Existing metrics...
        }
    }
    return results
```

**Test**: Run simulation, check output includes `"version": "0.1.0"`

#### Step 2.2: Add Version to Animation Displays
**Files**:
- `ridehail/animation/textual_console.py`
- `ridehail/animation/textual_map.py`
- `ridehail/animation/textual_stats.py`

**Changes**: Add version to footer or header display
```python
def compose(self) -> ComposeResult:
    # ... existing widgets ...
    yield Footer()  # Could show version in footer
```

**Note**: Optional enhancement, not critical for core functionality

### Phase 3: Web Frontend Integration

#### Step 3.1: Add Version to worker.py Results
**File**: `docs/lab/worker.py`

**Changes**:
```python
from ridehail import __version__

def initialize_simulation(sim_settings):
    """Initialize simulation and return initial state with version."""
    # ... existing init code ...

    return {
        "version": __version__,  # Add package version
        "map_data": {...},
        "stats_data": {...}
    }

def next_frame_map(sim_settings):
    """Return map frame with version in metadata."""
    # ... existing code ...

    return {
        "version": __version__,  # Include in every frame
        "vehicles": [...],
        # ... rest of frame data ...
    }
```

**Benefits**: Web interface has access to Python package version

#### Step 3.2: Update webworker.js to Extract Version
**File**: `docs/lab/webworker.js`

**Changes**:
```javascript
async function initializeSimulation(simSettings) {
  // ... existing code ...

  const result = workerPackage.initialize_simulation(simSettingsPy);
  const resultJS = result.toJs({ dict_converter: Object.fromEntries });

  // Extract and store version
  const packageVersion = resultJS.version || "unknown";

  // Send to main thread
  self.postMessage({
    type: "initialized",
    version: packageVersion,  // Include version
    data: resultJS
  });
}
```

#### Step 3.3: Update app.js to Display Version
**File**: `docs/lab/app.js`

**Changes**:
```javascript
constructor() {
  // ... existing code ...
  this.packageVersion = null;  // Store package version
}

handleWorkerMessage(message) {
  if (message.type === "initialized") {
    this.packageVersion = message.version;
    // Update UI with version
    this.updateVersionDisplay();
  }
}

updateVersionDisplay() {
  // Add version to UI (footer, about dialog, etc.)
  const versionElement = document.getElementById("package-version");
  if (versionElement) {
    versionElement.textContent = `v${this.packageVersion}`;
  }
}
```

#### Step 3.4: Remove Old version.js
**Action**: Delete `docs/lab/js/version.js`

**Update imports**: Remove any imports of version.js from HTML/JS files

**Rationale**: Package version is now the single source of truth

### Phase 4: Build Process Enhancement

#### Step 4.1: Enhance build_wheel.sh with Version Sync
**File**: `build_wheel.sh`

**Rename**: `build_wheel.sh` → `build.sh` (more general purpose)

**Enhanced Functionality**:
```bash
#!/usr/bin/bash
# Build script for ridehail package
# Synchronizes version across all files and builds distribution

set -e  # Exit on error

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Ridehail Build System${NC}"

# 1. Extract version from pyproject.toml (single source of truth)
VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

if [ -z "$VERSION" ]; then
    echo -e "${YELLOW}Error: Could not extract version from pyproject.toml${NC}"
    exit 1
fi

echo -e "${GREEN}Version: ${VERSION}${NC}"

# 2. Update ridehail/__init__.py with version
echo -e "${BLUE}Updating version in ridehail/__init__.py...${NC}"
sed -i "s/__version__ = \".*\"/__version__ = \"${VERSION}\"/" ridehail/__init__.py
echo -e "${GREEN}✓ Updated ridehail/__init__.py${NC}"

# 3. Build the wheel
echo -e "${BLUE}Building wheel with uv...${NC}"
uv build --wheel --package ridehail

# 4. Check if build succeeded
WHEEL_FILE="dist/ridehail-${VERSION}-py3-none-any.whl"
if [ ! -f "$WHEEL_FILE" ]; then
    echo -e "${YELLOW}Error: Wheel file not found at ${WHEEL_FILE}${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Wheel built: ${WHEEL_FILE}${NC}"

# 5. Copy to docs/lab/dist/
echo -e "${BLUE}Copying wheel to docs/lab/dist/...${NC}"
mkdir -p docs/lab/dist
cp "$WHEEL_FILE" docs/lab/dist/
echo -e "${GREEN}✓ Wheel copied to docs/lab/dist/${NC}"

# 6. Update version in webworker.js
WEBWORKER_FILE="docs/lab/webworker.js"
if [ -f "$WEBWORKER_FILE" ]; then
    echo -e "${BLUE}Updating version in ${WEBWORKER_FILE}...${NC}"
    sed -i "s/ridehail-[0-9.]*-py3-none-any\.whl/ridehail-${VERSION}-py3-none-any.whl/g" "$WEBWORKER_FILE"
    echo -e "${GREEN}✓ Updated ${WEBWORKER_FILE}${NC}"
else
    echo -e "${YELLOW}Warning: ${WEBWORKER_FILE} not found${NC}"
fi

# 7. Git status check (optional, shows if version files changed)
echo -e "${BLUE}Changed files:${NC}"
git status --short ridehail/__init__.py docs/lab/webworker.js

echo -e "${GREEN}Build complete!${NC}"
echo -e "Package version: ${VERSION}"
echo -e "Wheel file: ${WHEEL_FILE}"
echo -e "Web location: docs/lab/dist/ridehail-${VERSION}-py3-none-any.whl"
echo -e ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Test locally: python -m ridehail --version"
echo -e "2. Test web interface: cd docs/lab && python -m http.server"
echo -e "3. Commit version changes if satisfied"
```

#### Step 4.2: Add Version Sync Verification
**New File**: `scripts/verify_version.py`

**Purpose**: CI/CD verification that all version strings match

```python
#!/usr/bin/env python3
"""Verify version consistency across project files."""

import re
import sys
from pathlib import Path

def extract_version_pyproject():
    """Extract version from pyproject.toml."""
    content = Path("pyproject.toml").read_text()
    match = re.search(r'^version = "(.*)"', content, re.MULTILINE)
    return match.group(1) if match else None

def extract_version_init():
    """Extract version from ridehail/__init__.py."""
    content = Path("ridehail/__init__.py").read_text()
    match = re.search(r'^__version__ = "(.*)"', content, re.MULTILINE)
    return match.group(1) if match else None

def extract_version_webworker():
    """Extract version from webworker.js wheel path."""
    content = Path("docs/lab/webworker.js").read_text()
    match = re.search(r'ridehail-([0-9.]+)-py3-none-any\.whl', content)
    return match.group(1) if match else None

def main():
    """Check version consistency."""
    versions = {
        "pyproject.toml": extract_version_pyproject(),
        "ridehail/__init__.py": extract_version_init(),
        "docs/lab/webworker.js": extract_version_webworker(),
    }

    print("Version check:")
    for source, version in versions.items():
        print(f"  {source:30} {version or 'NOT FOUND'}")

    # Check all versions match
    unique_versions = set(v for v in versions.values() if v)

    if len(unique_versions) == 0:
        print("\n❌ ERROR: No versions found")
        return 1
    elif len(unique_versions) > 1:
        print(f"\n❌ ERROR: Version mismatch: {unique_versions}")
        return 1
    else:
        print(f"\n✓ All versions match: {unique_versions.pop()}")
        return 0

if __name__ == "__main__":
    sys.exit(main())
```

**Usage**:
```bash
# Run manually
python scripts/verify_version.py

# Add to CI/CD pipeline
# Add to pre-commit hook
```

### Phase 5: Documentation and Testing

#### Step 5.1: Update CLAUDE.md
**File**: `CLAUDE.md`

**Add section**: "Version Management"
```markdown
## Version Management

### Single Source of Truth
- **pyproject.toml**: Primary version location
- All other version strings synchronized during build

### Version Update Process
1. Update version in `pyproject.toml` only
2. Run `./build.sh` to synchronize and build
3. Verify with `python scripts/verify_version.py`
4. Test: `python -m ridehail --version`

### Build Commands
```bash
# Full build with version sync
./build.sh

# Verify version consistency
python scripts/verify_version.py

# Test version display
python -m ridehail --version
uv run -m ridehail -v
```

### Version in Code
```python
# Access package version
from ridehail import __version__

# Version included in simulation results
results = sim.get_results()  # Contains results["version"]

# Version available in config
version = config.version.value
```
```

#### Step 5.2: Testing Checklist

**Unit Tests**:
- ✅ `python -m ridehail --version` displays correct version
- ✅ `python -m ridehail -v` displays correct version
- ✅ `from ridehail import __version__` works
- ✅ `__version__` matches pyproject.toml

**Integration Tests**:
- ✅ Simulation results include version field
- ✅ Config object has version attribute
- ✅ Web worker receives version from Python
- ✅ Web UI displays package version

**Build Tests**:
- ✅ `./build.sh` synchronizes versions
- ✅ Wheel filename includes correct version
- ✅ `scripts/verify_version.py` passes
- ✅ Git shows only expected version file changes

**Desktop Tests**:
```bash
# Test version display
python -m ridehail --version
uv run -m ridehail -v

# Test version in simulation
python run.py test.config  # Check results include version
```

**Web Tests**:
```bash
# Build and serve
./build.sh
cd docs/lab
python -m http.server 8000

# Open http://localhost:8000
# Check console for package version in worker messages
# Check UI displays version (if UI element added)
```

## Implementation Timeline

### Session 1: Core Infrastructure (Phase 1)
- Estimated time: 30-45 minutes
- **Deliverables**:
  - `ridehail/__init__.py` with `__version__`
  - `ridehail/__main__.py` with `-v` flag
  - `ridehail/config.py` with version ConfigItem
  - Tests pass

### Session 2: Simulation Integration (Phase 2)
- Estimated time: 30 minutes
- **Deliverables**:
  - Version in simulation results
  - Version in animation displays (optional)
  - Tests pass

### Session 3: Web Integration (Phase 3)
- Estimated time: 45-60 minutes
- **Deliverables**:
  - Version in worker.py
  - Version in webworker.js
  - Version in app.js UI
  - Remove old version.js
  - Tests pass

### Session 4: Build Enhancement (Phase 4)
- Estimated time: 30-45 minutes
- **Deliverables**:
  - Enhanced build.sh script
  - Version verification script
  - Build tests pass

### Session 5: Documentation (Phase 5)
- Estimated time: 20-30 minutes
- **Deliverables**:
  - Updated CLAUDE.md
  - Testing checklist complete
  - Documentation reviewed

## Alternatives Considered

### Alternative 1: Version in Separate File
**Approach**: Create `ridehail/_version.py` with version string

**Rejected**: Adds complexity, pyproject.toml is sufficient source of truth

### Alternative 2: Dynamic Version Import
**Approach**: Use `importlib.metadata.version("ridehail")` at runtime

**Rejected**:
- Requires package installation
- Doesn't work during development
- More complex than simple `__version__` constant

### Alternative 3: Keep Web Version Separate
**Approach**: Maintain independent `docs/lab/js/version.js`

**Rejected**:
- Violates single source of truth principle
- Creates version drift
- Package version is more meaningful for reproducibility

## Benefits Summary

### For Developers
- ✅ Single version string to update (pyproject.toml)
- ✅ Automated synchronization via build script
- ✅ Easy verification of version consistency
- ✅ Standard Python packaging conventions
- ✅ Reproducible builds via SOURCE_DATE_EPOCH

### For Users
- ✅ Simple version check: `python -m ridehail -v`
- ✅ Version included in all simulation results
- ✅ Clear package version in web interface
- ✅ Reproducible results with version tracking
- ✅ Verifiable builds (security auditing)

### For Project
- ✅ Professional version management
- ✅ Reduced maintenance burden
- ✅ Better debugging with version metadata
- ✅ Improved documentation and examples
- ✅ Reproducible builds following industry standards

## Reproducible Builds with SOURCE_DATE_EPOCH

### Implementation

**Status**: ✅ Implemented in build.sh

The build system uses SOURCE_DATE_EPOCH to ensure reproducible builds:

```bash
# In build.sh
export SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
```

### How It Works

1. **Git Commit Timestamp**: Uses the timestamp of the last git commit
2. **Exported to Build Tools**: All build tools (uv, setuptools, pip) respect SOURCE_DATE_EPOCH
3. **Deterministic Timestamps**: Wheel file timestamps are consistent across builds
4. **Bit-for-Bit Reproducible**: Same source + same commit = identical wheel

### Benefits

- **Security**: Verify official builds by comparing checksums
- **Debugging**: Identical builds from same source
- **Distribution**: Package maintainers can verify builds
- **Standards Compliance**: Follows reproducible-builds.org specification

### Verification

```bash
# Build twice, should produce identical checksums
./build.sh
sha256sum dist/ridehail-0.1.0-py3-none-any.whl

rm dist/ridehail-0.1.0-py3-none-any.whl
./build.sh
sha256sum dist/ridehail-0.1.0-py3-none-any.whl

# Checksums should match exactly
```

### References

- [SOURCE_DATE_EPOCH Specification](https://reproducible-builds.org/specs/source-date-epoch/)
- [Reproducible Builds Project](https://reproducible-builds.org/)
- Python support: py_compile, setuptools, wheel all respect SOURCE_DATE_EPOCH

## Future Enhancements (Optional)

### Semantic Versioning
- Adopt semantic versioning: MAJOR.MINOR.PATCH
- Document version bump criteria
- Automated version bump scripts

### Git Integration
- Auto-tag releases with version
- Version derived from git tags
- CI/CD version validation

### Extended Metadata
- Add git commit hash to __version__ metadata
- Add Python version used for build info
- Runtime environment detection

### Web UI Version Display
- Add "About" dialog with version info
- Show version in footer
- Version in exported results/screenshots
