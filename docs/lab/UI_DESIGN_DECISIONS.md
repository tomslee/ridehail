# UI Design Decisions

This document records key UI/UX design decisions for the ridehail web application.

## Help Text: Inline vs. Tooltips

**Decision Date**: 2024-12-10

**Decision**: Use inline help text below form controls, not tooltips with help icons.

### Context

The application uses sliders and form controls with descriptive help text (class `app-settings-card__description`) explaining parameters, units, and relationships. We evaluated whether to replace this with tooltip-based help triggered by icons next to control labels.

### Research Summary

**Against Tooltips**:
- **Mobile Incompatibility**: Tooltips rely on hover, which doesn't work on touch devices
- **Accessibility Issues**: Requires complex ARIA implementation for screen readers and keyboard users
- **Hidden Essential Information**: UX principle: "If it's truly useful, don't hide it"
- **Working Memory Burden**: Users must remember hidden information while interacting
- **WCAG 2.1 Compliance**: Requires dismissible, hoverable, persistent implementation (criterion 1.4.13)

**For Inline Text**:
- **Always Visible**: Information accessible during interaction
- **Mobile-First**: Works identically on desktop and touch devices
- **Zero Accessibility Barriers**: Standard text readable by all assistive technologies
- **Lower Cognitive Load**: No memory burden, information visible when needed

### Rationale

1. **Educational Tool**: The simulation is for learning - hiding explanations works against this goal
2. **Desktop & Mobile Users**: Many users access via tablets/phones
3. **Complex Relationships**: Help text explains parameter interactions users need while adjusting values
4. **Existing Responsive Design**: Help text already hidden on zoom (`ui-zoom-hide` class) for space management

### Implementation

**Current Pattern** (to be maintained):
```html
<div class="app-settings-card">
    <div class="app-settings-card__content">
        <label for="input-vehicle-count" class="app-settings-card__label">
            <span class="app-settings-card__label-text">Ridehail vehicles</span>
            <span class="value" id="option-vehicle-count">8</span>
        </label>
        <div class="app-slider-container">
            <input id="input-vehicle-count" class="app-slider" type="range" min="1" max="16" value="8" step="1">
            <div class="app-slider-track"></div>
        </div>
        <p class="ui-zoom-hide app-settings-card__description">
            Active vehicles in the area (changes with "Free entry & exit")
        </p>
    </div>
</div>
```

**Key Elements**:
- `app-settings-card__description` - Help text paragraph
- `ui-zoom-hide` - Automatically hides text when zoomed for space management
- Positioned directly below control for immediate visual association

### Future Considerations

**If space becomes a concern**:
- Focus on making descriptions more concise
- Consider expandable "Learn more" sections for deep dives (click/tap, not hover)
- Do not switch to tooltip-based help

**Progressive Disclosure Alternative** (if needed):
- Expandable sections below primary help text
- Works on all devices via click/tap
- More accessible than tooltips

### References

- Nielsen Norman Group: [Tooltip Guidelines](https://www.nngroup.com/articles/tooltip-guidelines/)
- Smashing Magazine: [Designing Better Tooltips For Mobile User Interfaces](https://www.smashingmagazine.com/2021/02/designing-tooltips-mobile-user-interfaces/)
- UX Stack Exchange: [Form fields tooltips vs. plain help text](https://ux.stackexchange.com/questions/69968/form-fields-tooltips-vs-plain-help-text-what-works-best)
- W3C: WCAG 2.1 Success Criterion 1.4.13 - Content on Hover or Focus

### Status

**Active** - This pattern is currently implemented and working well across the application.

---

## Slider Control Spacing Optimization

**Decision Date**: 2024-12-10

**Decision**: Optimize vertical spacing for slider controls while maintaining WCAG 2.5.8 touch target requirements.

### Research: WCAG Touch Target Requirements

**WCAG 2.5.8 (Level AA) - Target Size (Minimum)**:
- Minimum touch target size: **24×24 CSS pixels**
- Alternative: If target is smaller, it must have 24px spacing from other targets
- Reference: [WCAG 2.5.8 Understanding Document](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)

**WCAG 2.5.5 (Level AAA) - Target Size (Enhanced)**:
- Recommended touch target size: **44×44 CSS pixels**
- Aligns with iOS Human Interface Guidelines
- Reference: [WCAG 2.5.5 Understanding Document](https://www.w3.org/WAI/WCAG21/Understanding/target-size.html)

### Spacing Optimizations

**Settings Card**:
- Card margin-bottom: `8px` → `6px` (reduced 25%)
- Card content padding: `10px` → `8px` vertical (reduced 20%)
- Label margin-bottom: `6px` → `4px` (reduced 33%)

**Slider Container**:
- Desktop height: `32px` → `28px` (still provides 24px+ effective touch area)
- Mobile height: `48px` → `44px` (meets WCAG AAA 44×44px recommendation)
- Container margin: added explicit `6px 0` (previously implicit)

**Description Text**:
- Font size: `12px` → `11px` (improved density while maintaining readability)
- Line height: `1.3` → `1.25` (tighter spacing)
- Added `margin-top: 4px` for consistent spacing

### Space Savings

**Per slider control**:
- Desktop: ~12-15px saved per control (≈18% reduction)
- Mobile: ~10-12px saved per control (≈15% reduction)
- With 16 slider controls: **~200px total vertical space saved**

### WCAG Compliance

**Touch Target Verification**:
- ✅ Desktop: 20px thumb + 8px padding zones = **28px effective target** (exceeds 24px minimum)
- ✅ Mobile: 28px thumb + 16px padding zones = **44px effective target** (meets AAA standard)
- ✅ Spacing between controls: 6px card margin + borders provides adequate separation
- ✅ Slider track provides horizontal touch tolerance

**Accessibility Standards Met**:
- WCAG 2.5.8 (Level AA): Target Size (Minimum) - **Compliant**
- WCAG 2.5.5 (Level AAA): Target Size (Enhanced) - **Compliant on mobile**
- Mobile-first design with larger touch targets on small screens

### Implementation

**CSS Changes** (`style.css`):
```css
.app-settings-card {
  margin-bottom: 6px; /* Reduced from 8px */
}

.app-settings-card__content {
  padding: 8px 12px; /* Reduced from 10px vertical */
}

.app-settings-card__label {
  margin-bottom: 4px; /* Reduced from 6px */
}

.app-settings-card__description {
  font-size: 11px; /* Reduced from 12px */
  line-height: 1.25; /* Reduced from 1.3 */
  margin-top: 4px; /* Added for consistency */
}

.app-slider-container {
  height: 28px; /* Reduced from 32px (desktop) */
  margin: 6px 0; /* Explicit margin */
}

@media (max-width: 840px) {
  .app-slider-container {
    height: 44px; /* Reduced from 48px, meets WCAG AAA */
  }
}
```

### Benefits

1. **Better Screen Real Estate**: 200px saved allows more controls visible without scrolling
2. **Maintained Usability**: All touch targets meet or exceed WCAG AA standards
3. **Enhanced Mobile Experience**: 44×44px targets match iOS guidelines
4. **Improved Density**: More compact without feeling cramped
5. **Accessibility Compliant**: Meets WCAG 2.5.8 (AA) and 2.5.5 (AAA on mobile)

### Future Considerations

If additional vertical space is needed:
- Consider collapsible sections for advanced controls
- Implement virtual scrolling for long lists
- Do not reduce touch targets below current sizes (maintains accessibility)

### References

- [WCAG 2.5.8: Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
- [WCAG 2.5.5: Target Size (Enhanced)](https://www.w3.org/WAI/WCAG21/Understanding/target-size.html)
- [Smashing Magazine: Minimum WCAG-Conformant Interactive Element Size](https://www.smashingmagazine.com/2024/07/getting-bottom-minimum-wcag-conformant-interactive-element-size/)
- [Smashing Magazine: Accessible Target Sizes Cheatsheet](https://www.smashingmagazine.com/2023/04/accessible-tap-target-sizes-rage-taps-clicks/)

### Status

**Active** - Optimizations implemented and tested for accessibility compliance.
