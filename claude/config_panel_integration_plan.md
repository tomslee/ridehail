# ConfigPanel Integration Plan for terminal_map and terminal_stats

**Date**: December 2024
**Status**: Approved design, awaiting implementation

## Overview

Add the ConfigPanel (currently only in `terminal_console`) to `terminal_map` and `terminal_stats` animations to provide consistent UX across all textual-based displays. The panel will only show when the terminal is wide enough to accommodate it without intruding on the primary visualization.

## Current Architecture

### textual_console.py (animation_style = console) ✅ Already has ConfigPanel

- Layout: `Header | [EnhancedProgressPanel | ConfigPanel] | Footer`
- Uses `Horizontal` container with two panels side-by-side
- ConfigPanel already implemented and working

### textual_map.py (animation_style = terminal_map) ⚠️ Needs ConfigPanel

- Layout: `Header | MapContainer | Footer`
- Single full-width map display
- No configuration panel currently

### textual_stats.py (animation_style = terminal_stats) ⚠️ Needs ConfigPanel

- Layout: `Header | StatsChartWidget | Footer`
- Single full-width chart display
- No configuration panel currently

## Design Goals

1. **Add ConfigPanel** to terminal_map and terminal_stats
2. **Responsive layout** - only show panel when terminal is wide enough
3. **Consistent UX** across all textual-based animations
4. **Non-intrusive** - don't compromise the primary visualization

## Proposed Solution: Responsive Two-Column Layout

### Visual Layout

```
┌─ Header ────────────────────────────────────────────────────────┐
│ Ridehail Simulation - Block 50/200                              │
├──────────────────────────────────────────────────────────────────┤
│ ┌─ Main Display ──────────┐ │ ┌─ Configuration ─────┐          │
│ │ (Map or Chart)           │ │ │ Title: ...          │          │
│ │                          │ │ │ ┌──────────────────┐│          │
│ │    [PRIMARY FOCUS]       │ │ │ │city_size      48 ││          │
│ │                          │ │ │ │vehicle_count 600 ││          │
│ │                          │ │ │ │...               ││          │
│ │                          │ │ │ └──────────────────┘│          │
│ └──────────────────────────┘ │ └─────────────────────┘          │
├──────────────────────────────────────────────────────────────────┤
│ Footer: [q] Quit  [space] Pause  [r] Reset                      │
└──────────────────────────────────────────────────────────────────┘
```

### Width Thresholds

- **< 100 columns**: ConfigPanel hidden, primary display full width (current behavior)
- **≥ 100 columns**: ConfigPanel shown in right column (45 chars wide), primary display takes remaining space

## Implementation Plan

### **RECOMMENDED: Phase 4 - Static Approach (Simplest)**

Implement this first for simplicity and reliability. Dynamic resize can be added later if needed.

#### Step 4.1: Modify TextualMapApp in textual_map.py

**File**: `ridehail/animation/textual_map.py`

**Location**: `TextualMapApp.compose()` method (around line 904)

**Current code**:

```python
def compose(self) -> ComposeResult:
    """Create child widgets for the map app"""
    yield Header()
    yield MapContainer(self.sim, id="map_container")
    yield Footer()
```

**New code**:

```python
def compose(self) -> ComposeResult:
    """Create child widgets for the map app"""
    from textual.containers import Horizontal
    from .textual_base import ConfigPanel

    yield Header()

    # Check if terminal is wide enough for config panel
    # Note: self.size may not be available yet in compose(),
    # so we use console.size instead
    terminal_width = self.console.size.width if hasattr(self.console, 'size') else 80

    if terminal_width >= 100:
        # Two-column layout with config panel
        with Horizontal(id="layout_container"):
            yield MapContainer(self.sim, id="map_container")
            yield ConfigPanel(self.sim, id="config_panel")
    else:
        # Single-column layout (current behavior)
        yield MapContainer(self.sim, id="map_container")

    yield Footer()
```

**Add CSS to TextualMapApp** (in same file):

```python
CSS = """
#layout_container {
    width: 1fr;
    height: 1fr;
}

#map_container {
    width: 1fr;
    height: 1fr;
}

#config_panel {
    width: 45;
    height: 1fr;
    border: solid $primary;
}
"""
```

#### Step 4.2: Modify TextualStatsApp in textual_stats.py

**File**: `ridehail/animation/textual_stats.py`

**Location**: `StatsApp.compose()` method (around line 368)

**Current code**:

```python
def compose(self) -> ComposeResult:
    yield Header(show_clock=True)
    yield StatsChartWidget(self.animation.sim, id="chart_container")
    yield Footer()
```

**New code**:

```python
def compose(self) -> ComposeResult:
    from textual.containers import Horizontal
    from ridehail.animation.textual_base import ConfigPanel

    yield Header(show_clock=True)

    # Check if terminal is wide enough for config panel
    terminal_width = self.console.size.width if hasattr(self.console, 'size') else 80

    if terminal_width >= 100:
        # Two-column layout with config panel
        with Horizontal(id="layout_container"):
            yield StatsChartWidget(self.animation.sim, id="chart_container")
            yield ConfigPanel(self.sim, id="config_panel")
    else:
        # Single-column layout (current behavior)
        yield StatsChartWidget(self.animation.sim, id="chart_container")

    yield Footer()
```

**Update CSS in StatsApp.CSS** (around line 340):

Add to existing CSS block:

```python
CSS = """
Header {
    background: $primary;
}

Footer {
    background: $secondary;
}

#layout_container {
    width: 1fr;
    height: 1fr;
}

#chart_container {
    width: 1fr;
    height: 1fr;
}

#config_panel {
    width: 45;
    height: 1fr;
    border: solid $primary;
}

#stats_plot {
    width: 1fr;
    height: 1fr;
    border: solid $primary;
}
"""
```

### Alternative: Phases 1-3 - Dynamic Responsive Layout (Advanced)

Only implement this if the static approach proves insufficient or users request dynamic resize capability.

#### Phase 1: Create Responsive Container Base Class

**File**: `ridehail/animation/textual_base.py`

**Add new class after ConfigPanel** (around line 355):

```python
class ResponsiveLayoutContainer(Container):
    """
    Container that shows/hides ConfigPanel based on terminal width.

    Shows two-column layout (main content + config) when wide enough,
    single-column layout (main content only) when narrow.

    This is an advanced implementation that handles dynamic resizing.
    For a simpler approach, see the static layout pattern used in
    TextualConsoleApp.
    """

    MINIMUM_WIDTH_FOR_CONFIG = 100  # Minimum terminal width to show config panel
    CONFIG_PANEL_WIDTH = 45         # Fixed width for config panel

    CSS = """
    ResponsiveLayoutContainer {
        layout: horizontal;
        width: 1fr;
        height: 1fr;
    }

    ResponsiveLayoutContainer > #config_panel {
        width: 45;
        height: 1fr;
        border: solid $primary;
    }

    ResponsiveLayoutContainer > :first-child {
        width: 1fr;
        height: 1fr;
    }
    """

    def __init__(self, sim, main_widget_factory, **kwargs):
        """
        Args:
            sim: RideHailSimulation instance
            main_widget_factory: Callable that creates the main widget
                                (e.g., lambda: MapContainer(sim, id="map"))
        """
        super().__init__(**kwargs)
        self.sim = sim
        self.main_widget_factory = main_widget_factory
        self._show_config = False

    def compose(self) -> ComposeResult:
        """Initial composition - decide layout based on current terminal width"""
        # Create main widget
        yield self.main_widget_factory()

        # Conditionally create config panel
        if self.size.width >= self.MINIMUM_WIDTH_FOR_CONFIG:
            self._show_config = True
            yield ConfigPanel(self.sim, id="config_panel")

    def on_resize(self, event) -> None:
        """
        Handle terminal resize - show/hide config panel dynamically.

        Note: This requires careful implementation to avoid recreating
        widgets unnecessarily. May be complex with Textual's reactive system.
        """
        should_show = event.size.width >= self.MINIMUM_WIDTH_FOR_CONFIG

        if should_show != self._show_config:
            # Need to add or remove config panel
            # This may require using mount()/remove() methods
            # Implementation TBD based on Textual best practices
            pass
```

#### Phase 2: Integrate into TextualMapApp

**File**: `ridehail/animation/textual_map.py`

```python
def compose(self) -> ComposeResult:
    """Create child widgets for the map app"""
    from .textual_base import ResponsiveLayoutContainer

    yield Header()

    # Create responsive layout with map and optional config panel
    yield ResponsiveLayoutContainer(
        self.sim,
        lambda: MapContainer(self.sim, id="map_container"),
        id="layout_container"
    )

    yield Footer()
```

#### Phase 3: Integrate into TextualStatsApp

**File**: `ridehail/animation/textual_stats.py`

```python
def compose(self) -> ComposeResult:
    from ridehail.animation.textual_base import ResponsiveLayoutContainer

    yield Header(show_clock=True)

    # Create responsive layout with chart and optional config panel
    yield ResponsiveLayoutContainer(
        self.sim,
        lambda: StatsChartWidget(self.animation.sim, id="chart_container"),
        id="layout_container"
    )

    yield Footer()
```

## Design Considerations

### Advantages

- ✅ Consistent UX across all textual animations
- ✅ ConfigPanel code reused (DRY principle)
- ✅ Non-intrusive - hidden when space is tight
- ✅ Helpful reference for users running simulations
- ✅ Title field now displays prominently in config panel

### Challenges

- ⚠️ Dynamic resize handling may be complex (Textual reactive system)
- ⚠️ Fixed config panel width (45 chars) needs tuning for different use cases
- ⚠️ CSS grid/horizontal layout interactions need testing
- ⚠️ Terminal width detection timing (may not be available in compose())

### Risk Mitigation

- Start with simpler **static approach** (Phase 4) - decide layout on startup
- If successful, enhance with **dynamic resize** later (Phases 1-3)
- Maintain current behavior as fallback for narrow terminals
- Test extensively with various terminal sizes

## Testing Plan

### Unit Tests

1. **Narrow terminal** (< 100 cols): Verify config panel hidden, map/chart full width
2. **Wide terminal** (≥ 100 cols): Verify two-column layout, both panels visible
3. **Edge case** (exactly 100 cols): Verify threshold behavior is correct

### Integration Tests

4. **terminal_map with small city** (8x8): Verify map remains readable with config panel
5. **terminal_map with large city** (48x48): Verify layout handles larger maps
6. **terminal_stats**: Verify plotext charts remain readable with reduced width
7. **Resize during session** (if dynamic): Verify smooth show/hide transitions

### Visual Tests

8. **Title display**: Verify long titles display correctly in config panel
9. **Section dividers**: Verify sections display correctly in narrow config panel
10. **Scrolling**: Verify config panel scrolls correctly for long parameter lists

### Test Commands

```bash
# Test terminal_map in narrow terminal (80 columns)
python -m ridehail test.config -a terminal_map

# Test terminal_map in wide terminal (120 columns)
python -m ridehail test.config -a terminal_map

# Test terminal_stats in narrow terminal
python -m ridehail test.config -a terminal_stats

# Test terminal_stats in wide terminal
python -m ridehail test.config -a terminal_stats

# Test with config that has a long title
python -m ridehail feb_6_48.config -a terminal_map
```

## Recommendation

**Implement Phase 4 (Static Approach) first** for these reasons:

1. **Simplicity**: Decide layout once on startup, no complex resize handling
2. **Reliability**: Less prone to edge cases and timing issues
3. **Fast to implement**: Can be done in a single session
4. **Easy to test**: Straightforward test cases
5. **Good user experience**: Most users don't resize terminals during simulation
6. **Incremental approach**: Can enhance with dynamic resize later if requested

**Enhancement path** (if users request dynamic resize):

- Implement Phases 1-3 after Phase 4 is stable
- Add feature flag to toggle between static and dynamic layouts
- Gather user feedback before committing to dynamic approach

## Implementation Checklist

When implementing, follow this checklist:

- [ ] Read this document thoroughly
- [ ] Choose approach: Phase 4 (static) or Phases 1-3 (dynamic)
- [ ] Implement textual_map.py changes
- [ ] Implement textual_stats.py changes
- [ ] Add/update CSS styling
- [ ] Test with narrow terminal (< 100 cols)
- [ ] Test with wide terminal (≥ 100 cols)
- [ ] Test with various city sizes
- [ ] Test title display with long titles
- [ ] Verify section dividers display correctly
- [ ] Update documentation if needed
- [ ] Consider adding config parameter to force config panel on/off

## Notes

- ConfigPanel is defined in `ridehail/animation/textual_base.py` starting at line 174
- ConfigPanel already handles title display, section grouping, and weight-based ordering
- The `title` field now passes through to the simulation object and displays prominently
- Terminal width of 100 characters is a reasonable threshold (leaves ~55 chars for map/chart)
- Config panel width of 45 characters accommodates parameter names and values comfortably

## Related Work

- ConfigPanel implementation: `ridehail/animation/textual_base.py:174-355`
- TextualConsoleApp (reference implementation): `ridehail/animation/textual_console.py:456`
- Title field integration: Completed December 2024
- Section-based exclusion logic: Completed December 2024
