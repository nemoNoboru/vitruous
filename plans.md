# UI/UX Improvements: Western Blot Quantifier (Phase 2)

## Overview
Polish the UI with visual enhancements and consistent branding. Key changes: peak annotations on profile graph, smooth animations, consistent cream/ink color palette, better typography, and loading skeleton states.

## Improvements to Implement

### 1. Peak Annotations on Profile Graph
- Draw vertical dashed lines at each band's X position on the profile
- Add band numbers at the top of each line
- Color-code to match the green selection color
- Aligns visually with the strip image below

### 2. Smooth Animations
- Fade transitions when showing/hiding panels
- Slide animation when switching between rows
- Subtle scale animation on detection overlay appearance
- CSS transitions for hover states

### 3. Consistent Cream/Ink Color Palette
- Replace slate colors in analysis panel with cream/ink palette
- Update table styling to match brand colors
- Consistent border and background colors throughout

### 4. Better Typography (Cormorant Serif)
- Use `font-serif` class for all section headings
- Consistent font weights and sizes
- Better visual hierarchy between headings and body text

### 5. Loading Skeleton States
- Show animated placeholder shapes while detecting/analyzing
- Skeleton for profile graph area
- Skeleton for band table rows
- Pulse animation effect

## Files to Modify

- `app/templates/index.html` - color classes, typography, skeleton markup
- `app/static/js/main.js` - peak annotations, animations, skeleton handling

## Implementation Steps

### Step 1: Update Color Palette (HTML + CSS)
- Replace `bg-slate-*`, `text-slate-*`, `border-slate-*` with cream/ink equivalents
- Analysis panel: `bg-cream-50` instead of `bg-white`
- Table header: `bg-cream-200` instead of `bg-slate-100`
- Borders: `border-cream-300` throughout
- Text: `text-ink-800` for primary, `text-ink-700/60` for secondary

### Step 2: Typography Improvements (HTML)
- Add `font-serif` to: "Band Intensity Analysis" heading
- Ensure consistent heading sizes across panels
- Check font weights (semibold for headings, normal for body)

### Step 3: Add CSS Animations (HTML style block)
```css
.fade-in { animation: fadeIn 0.3s ease-out; }
.slide-up { animation: slideUp 0.3s ease-out; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideUp { from { transform: translateY(10px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
.skeleton { background: linear-gradient(90deg, #e5ddd1 25%, #f0ebe3 50%, #e5ddd1 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
```

### Step 4: Add Skeleton Markup (HTML)
- Add skeleton elements inside `profileContainer` and `analysisPanel`
- Hidden by default, shown during loading
- Structure matches final content layout

### Step 5: Peak Annotations (JS - drawProfile function)
After drawing the profile line, add:
```js
// Draw band markers on profile
if (detectionResult && selectedRowId !== null) {
  const row = detectionResult.rows[selectedRowId];
  const rowBbox = row.bbox;
  row.bands.forEach((band, idx) => {
    const bandRelX = (band.center.x - rowBbox.x1) / (rowBbox.x2 - rowBbox.x1);
    const markerX = PROFILE_MARGIN_LEFT + bandRelX * graphW;

    // Dashed vertical line
    profileCtx.strokeStyle = '#22c55e';
    profileCtx.setLineDash([3, 3]);
    profileCtx.beginPath();
    profileCtx.moveTo(markerX, marginTop);
    profileCtx.lineTo(markerX, marginTop + graphH);
    profileCtx.stroke();
    profileCtx.setLineDash([]);

    // Band number label
    profileCtx.fillStyle = '#22c55e';
    profileCtx.font = 'bold 10px system-ui';
    profileCtx.textAlign = 'center';
    profileCtx.fillText(`${idx + 1}`, markerX, marginTop - 5);
  });
}
```

### Step 6: Animation Triggers (JS)
- Add animation classes when showing panels: `analysisPanel.classList.add('fade-in')`
- Add animation class to profile/strip on row change
- Manage skeleton visibility in `setLoading()` and analysis functions

## Color Reference

| Old (Slate)      | New (Cream/Ink)     |
|------------------|---------------------|
| bg-white         | bg-cream-50         |
| bg-slate-50      | bg-cream-100        |
| bg-slate-100     | bg-cream-200        |
| border-slate-100 | border-cream-200    |
| border-slate-200 | border-cream-300    |
| text-slate-800   | text-ink-800        |
| text-slate-600   | text-ink-700        |
| text-slate-500   | text-ink-700/70     |
| text-slate-400   | text-ink-700/50     |

## Verification

1. Start server: `uv run python run.py`
2. **Test colors**: Analysis panel uses cream/ink palette, not slate
3. **Test typography**: All headings use Cormorant serif font
4. **Test skeleton**: During detection, skeleton placeholders appear
5. **Test animations**: Panels fade in smoothly when appearing
6. **Test peak annotations**: Profile graph shows band markers aligned with strip
7. **Test row switch**: Switching rows has smooth transition
