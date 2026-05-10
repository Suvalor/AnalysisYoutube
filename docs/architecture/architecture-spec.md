# Architecture Spec: 8-Page Theme Adaptation

> Author: architect Agent | Date: 2026-04-30 | Status: DRAFT

## 1. Current State Analysis

### 1.1 Existing Theme Infrastructure

The project already has a solid theme foundation with 4 themes:

| Theme | Token File | Character |
|-------|-----------|-----------|
| light | `light.ts` | Light classic, white/gray base |
| deep-blue | `deep-blue.ts` | Dark blue tech, #0F172A base |
| liblib-dark | `liblib-dark.ts` | Pure dark, #111318 base |
| warm-orange | `warm-orange.ts` | Dark warm, #1A1412 base with orange accent |

**Token System** (`tokens.ts`): Defines 72 semantic tokens organized into 8 groups:

- `bg-*` (8): page, card, card-hover, sidebar, header, input, modal, overlay
- `text-*` (6): primary, secondary, muted, inverse, link, link-hover
- `border-*` (5): default, hover, focus, card, divider
- `accent-*` (4): default, hover, light, text
- `status-*` (8): success/warning/error/info x default/light
- `shadow-*` (2): card, modal
- `radius-*` (3): sm, md, lg
- `spacing-*` (2): compact, comfortable

**Tailwind Mapping** (`tailwind.config.ts`): All 72 tokens mapped as `yc-*` utility classes (e.g. `yc-bg-page`, `yc-text-primary`).

**Ant Design Themes** (`antd-themes.ts`): Full Ant Design `theme.config` for each theme, mapping to the same CSS variables via `token` overrides.

**ThemeProvider** (`ThemeProvider.tsx`): On theme change, calls `applyTheme(themeName)` which sets all CSS custom properties on `:root` via `document.documentElement.style.setProperty`.

**Theme Store** (`useThemeStore.ts`): Zustand store with `theme` state, `setTheme` action, and localStorage persistence.

### 1.2 Hardcoded Color Patterns in 8 Target Pages

| Page | File | Hex/rgba Count | Tailwind Arbitrary | style= Count | Key Patterns |
|------|------|---------------|-------------------|-------------|-------------|
| blue-ocean-radar | `BlueOceanRadar.tsx` | 0 | 45+ | 3 | Heavy `bg-[#xxx]`/`text-[#xxx]`/`border-[#xxx]` arbitrary values |
| navigation-guide | `NavigationGuide.tsx` | 0 | 25+ | 0 | Tailwind arbitrary values for card/table/chart |
| competitor-analysis | `CompetitorAnalysis.tsx` | 0 | 20+ | 0 | Tailwind arbitrary + recharts radar/area charts |
| channel-list | `ChannelList.tsx` | 0 | 10+ | 0 | Light Tailwind arbitrary values |
| channel-detail | `ChannelDetail.tsx` | 0 | 40+ | 2 | Extensive Tailwind arbitrary, recharts charts |
| global-video-list | `GlobalVideoList.tsx` | 0 | 15+ | 0 | Tailwind arbitrary values |
| video-board | `VideoBoard.tsx` | 0 | 55+ | 5 | Entire page hardcoded dark theme, full `bg-[#0F172A]` deep-blue palette |
| config-center | `ConfigCenter.tsx` | 0 | 8+ | 0 | Light Tailwind arbitrary values |

**Critical Finding**: All 8 pages use Tailwind arbitrary value syntax (`bg-[#xxx]`, `text-[#xxx]`, `border-[#xxx]`, `from-[#xxx]`, `to-[#xxx]`) rather than inline `style` or hex-in-JS. This is favorable -- Tailwind arbitrary values can be replaced with `yc-*` utilities with no runtime cost.

**Pattern Classification**:

| Category | Description | Example | Count (approx) |
|----------|-------------|---------|----------------|
| **A. Backgrounds** | `bg-[#xxx]` on cards, sections, hover states | `bg-[#1E293B]`, `bg-[#0F172A]` | 60+ |
| **B. Text** | `text-[#xxx]` for headings, labels, values | `text-[#94A3B8]`, `text-[#E2E8F0]` | 45+ |
| **C. Borders** | `border-[#xxx]` and `divide-[#xxx]` | `border-[#334155]` | 15+ |
| **D. Gradients** | `from-[#xxx] to-[#xxx]` | `from-[#1E40AF] to-[#7C3AED]` | 8+ |
| **E. Chart colors** | Fill/stroke in recharts, progress bars | `fill="#3B82F6"`, `stroke="#8B5CF6"` | 20+ |
| **F. Shadows/Overlays** | `shadow-[#xxx]`, overlay backgrounds | `shadow-[rgba(...)]` | 5+ |
| **G. Misc** | Ring, outline, decoration colors | `ring-[#xxx]` | 3+ |

### 1.3 Token Coverage Gap Analysis

The 72 existing tokens cover common UI elements well. Gaps for these 8 pages:

| Gap | Current Tokens | What's Missing |
|-----|---------------|----------------|
| Chart series colors | None | 6-8 distinct colors for chart lines/bars/areas |
| Chart gradient stops | None | Start/end colors for area chart gradients |
| Card variant backgrounds | `yc-bg-card`, `yc-bg-card-hover` | Elevated card, highlighted card, stat card backgrounds |
| Data visualization backgrounds | None | Chart plot area, grid lines, axis labels |
| Status accent colors | `yc-status-*` (4 pairs) | Chart-specific positive/negative indicators |
| Gradient definitions | None | Named gradient from/to pairs |
| VideoBoard-specific | None | Video score gauge, ranking badge, trend indicator |

---

## 2. ADR: Architecture Decision Records

### ADR-1: Hardcoded Color Replacement Strategy

**Decision**: Direct replacement with existing `yc-*` utilities where possible; add new semantic tokens only when no existing token semantically matches.

**Rationale**:
- The existing 72 tokens already cover ~60% of the hardcoded values semantically (e.g., `bg-[#1E293B]` in deep-blue = `yc-bg-card`, `text-[#94A3B8]` = `yc-text-muted`).
- Adding tokens for every unique hex value would balloon the system; instead, map each hardcoded value to the closest semantic token.
- Where a hardcoded value represents a genuinely new semantic concept (e.g., chart line color), add a new token.

**Decision Rule**:

| When | Action |
|------|--------|
| Hardcoded value matches an existing token's purpose | Replace with `yc-*` utility |
| Hardcoded value is a chart series color | Add to new `chart-*` token group |
| Hardcoded value is a gradient stop | Add to new `gradient-*` token group |
| Hardcoded value is a one-off decorative color | Add to `decorative-*` token group |
| Hardcoded value is a shadow/ring with color | Use `yc-shadow-*` or define new if needed |

### ADR-2: Recharts Theme Adaptation

**Decision**: Use a `useChartColors` hook that reads CSS variables at render time via `getComputedStyle`.

**Rationale**:
- Recharts requires JS values for `fill`, `stroke`, and `<linearGradient>` stops -- CSS variables cannot be used directly in JSX props.
- `getComputedStyle` reads the live CSS variable values, so theme changes are automatically reflected on next render.
- A hook is the simplest mechanism: components call `const colors = useChartColors()` and use `colors.series[0]`, `colors.gradient.start`, etc.
- Alternative considered: Zustand store subscription -- rejected because it duplicates state already in CSS variables.
- Alternative considered: CSS `currentColor` -- rejected because recharts SVG elements don't inherit text color consistently.

**Hook API**:

```typescript
// frontend/src/hooks/useChartColors.ts
interface ChartColors {
  series: string[];           // 8 distinct series colors
  grid: string;               // chart grid line color
  axis: string;               // axis label color
  tooltip: {                  // tooltip colors
    bg: string;
    border: string;
    text: string;
  };
  gradient: {                 // gradient stop pairs
    blue: [string, string];
    purple: [string, string];
    green: [string, string];
    orange: [string, string];
  };
}
```

**Performance**: `getComputedStyle` is called once per chart mount, not on every render. The hook uses `useMemo` with the theme name as dependency.

### ADR-3: VideoBoard Deep-Theme Refactoring

**Decision**: Remove the hardcoded deep-blue palette from VideoBoard and replace with theme-aware `yc-*` utilities. VideoBoard will use the same token system as all other pages.

**Rationale**:
- VideoBoard currently hardcodes `#0F172A`, `#1E293B`, `#334155`, `#94A3B8`, `#E2E8F0` etc., which are exactly the deep-blue theme values. Under deep-blue theme, the result is identical; under light theme, these would currently look broken.
- By switching to `yc-*` utilities, VideoBoard adapts to all 4 themes automatically.
- The visual appearance under deep-blue theme will be preserved (same token values); under other themes, it gains proper theming for the first time.

### ADR-4: MarkdownPreview Theme Adaptation

**Decision**: Add CSS variable-based styling to MarkdownPreview's wrapper, overriding `react-markdown`'s default rendering via CSS custom properties.

**Rationale**:
- MarkdownPreview uses `react-markdown` which renders standard HTML elements (`h1-h6`, `p`, `a`, `code`, `pre`, `table`, etc.).
- These elements inherit browser defaults unless styled. The component already has a wrapper div.
- Solution: Add a CSS class `markdown-preview` on the wrapper, and in `frontend/src/themes/index.css` (or a dedicated `markdown.css`), define theme-aware styles using `yc-*` CSS variables.

```css
.markdown-preview h1 { color: var(--yc-text-primary); }
.markdown-preview p { color: var(--yc-text-secondary); }
.markdown-preview code {
  background: var(--yc-bg-input);
  color: var(--yc-text-primary);
}
.markdown-preview a { color: var(--yc-text-link); }
.markdown-preview table th {
  background: var(--yc-bg-card);
  border-color: var(--yc-border-default);
}
```

### ADR-5: New Semantic Token Groups

**Decision**: Add 3 new token groups (20 tokens total) to cover chart colors, gradients, and card variants.

**New Tokens**:

| Group | Token | Purpose |
|-------|-------|---------|
| `chart-*` | `chart-1` through `chart-8` | Series colors for charts |
| `chart-*` | `chart-grid` | Grid line color |
| `chart-*` | `chart-axis` | Axis text color |
| `chart-*` | `chart-tooltip-bg` | Tooltip background |
| `chart-*` | `chart-tooltip-border` | Tooltip border |
| `chart-*` | `chart-tooltip-text` | Tooltip text |
| `gradient-*` | `gradient-blue-from`, `gradient-blue-to` | Blue gradient stops |
| `gradient-*` | `gradient-purple-from`, `gradient-purple-to` | Purple gradient stops |
| `gradient-*` | `gradient-green-from`, `gradient-green-to` | Green gradient stops |
| `gradient-*` | `gradient-orange-from`, `gradient-orange-to` | Orange gradient stops |
| `card-*` | `card-elevated` | Elevated card background (between card and card-hover) |
| `card-*` | `card-highlight` | Highlighted/selected card background |
| `card-*` | `card-stat` | Stat card background |

Total new tokens: 20. This brings the system from 72 to 92 tokens.

---

## 3. System Boundary & File Mapping

### 3.1 Files to Modify

| Category | File Path | Change Type |
|----------|-----------|-------------|
| **Token Definitions** | `src/themes/tokens.ts` | Add 20 new tokens to `ThemeTokens` interface and `defaultTokens` |
| **Token Definitions** | `src/themes/light.ts` | Add 20 new token values for light theme |
| **Token Definitions** | `src/themes/deep-blue.ts` | Add 20 new token values for deep-blue theme |
| **Token Definitions** | `src/themes/liblib-dark.ts` | Add 20 new token values for liblib-dark theme |
| **Token Definitions** | `src/themes/warm-orange.ts` | Add 20 new token values for warm-orange theme |
| **Tailwind Config** | `tailwind.config.ts` | Add 20 new `yc-*` utility mappings |
| **New Hook** | `src/hooks/useChartColors.ts` | New file -- chart color hook |
| **New CSS** | `src/styles/markdown-theme.css` | New file -- MarkdownPreview theme styles |
| **MarkdownPreview** | `src/components/MarkdownPreview.tsx` | Add `markdown-preview` class to wrapper |
| **Page** | `src/pages/radar/BlueOceanRadar.tsx` | Replace ~45 arbitrary Tailwind values |
| **Page** | `src/pages/radar/NavigationGuide.tsx` | Replace ~25 arbitrary Tailwind values |
| **Page** | `src/pages/youtube/CompetitorAnalysis.tsx` | Replace ~20 arbitrary Tailwind values + recharts colors |
| **Page** | `src/pages/youtube/ChannelList.tsx` | Replace ~10 arbitrary Tailwind values |
| **Page** | `src/pages/youtube/ChannelDetail.tsx` | Replace ~40 arbitrary Tailwind values + recharts colors |
| **Page** | `src/pages/youtube/GlobalVideoList.tsx` | Replace ~15 arbitrary Tailwind values |
| **Page** | `src/pages/board/VideoBoard.tsx` | Replace ~55 arbitrary Tailwind values (full page) |
| **Page** | `src/pages/settings/ConfigCenter.tsx` | Replace ~8 arbitrary Tailwind values |

**Total**: 5 token files + 1 tailwind config + 1 new hook + 1 new CSS + 1 component + 8 pages = 17 files.

### 3.2 Modification Pattern Classification

| Pattern | Description | Technique | Example |
|---------|-------------|-----------|---------|
| **P1: Direct yc-* swap** | Hardcoded value maps to existing token | Replace `bg-[#1E293B]` with `yc-bg-card` | ~55% of changes |
| **P2: New yc-* swap** | Hardcoded value maps to new token | Replace `bg-[#0F172A]` with `yc-bg-card-elevated` | ~25% of changes |
| **P3: Chart hook** | Recharts fill/stroke/gradient | Use `useChartColors()` hook values | ~12% of changes |
| **P4: CSS class** | MarkdownPreview, global elements | Add `markdown-preview` class | ~3% of changes |
| **P5: Gradient utility** | Tailwind gradient classes | Replace `from-[#xxx] to-[#xxx]` with `yc-gradient-blue-from yc-gradient-blue-to` | ~5% of changes |

---

## 4. API Contract: New CSS Variable Naming & Value Definitions

### 4.1 Naming Convention

All new CSS variables follow the existing pattern `--yc-{group}-{name}`:

```
--yc-chart-{1-8}          # Series colors
--yc-chart-grid           # Grid lines
--yc-chart-axis           # Axis labels
--yc-chart-tooltip-bg     # Tooltip background
--yc-chart-tooltip-border # Tooltip border
--yc-chart-tooltip-text   # Tooltip text
--yc-gradient-blue-from   # Blue gradient start
--yc-gradient-blue-to     # Blue gradient end
--yc-gradient-purple-from # Purple gradient start
--yc-gradient-purple-to   # Purple gradient end
--yc-gradient-green-from  # Green gradient start
--yc-gradient-green-to    # Green gradient end
--yc-gradient-orange-from # Orange gradient start
--yc-gradient-orange-to   # Orange gradient end
--yc-card-elevated        # Elevated card bg
--yc-card-highlight       # Highlighted card bg
--yc-card-stat            # Stat card bg
```

### 4.2 Value Definitions Per Theme

| Token | light | deep-blue | liblib-dark | warm-orange |
|-------|-------|-----------|-------------|-------------|
| `chart-1` | `#3B82F6` | `#3B82F6` | `#60A5FA` | `#F97316` |
| `chart-2` | `#8B5CF6` | `#8B5CF6` | `#A78BFA` | `#FB923C` |
| `chart-3` | `#10B981` | `#10B981` | `#34D399` | `#FBBF24` |
| `chart-4` | `#F59E0B` | `#F59E0B` | `#FBBF24` | `#F87171` |
| `chart-5` | `#EF4444` | `#EF4444` | `#F87171` | `#A78BFA` |
| `chart-6` | `#06B6D4` | `#06B6D4` | `#22D3EE` | `#34D399` |
| `chart-7` | `#EC4899` | `#EC4899` | `#F472B6` | `#60A5FA` |
| `chart-8` | `#6366F1` | `#6366F1` | `#818CF8` | `#2DD4BF` |
| `chart-grid` | `#E5E7EB` | `#1E293B` | `#1F2937` | `#2D2420` |
| `chart-axis` | `#6B7280` | `#94A3B8` | `#9CA3AF` | `#A89080` |
| `chart-tooltip-bg` | `#FFFFFF` | `#1E293B` | `#1F2937` | `#2D2420` |
| `chart-tooltip-border` | `#E5E7EB` | `#334155` | `#374151` | `#3D302A` |
| `chart-tooltip-text` | `#111827` | `#E2E8F0` | `#E5E7EB` | `#F5E6D3` |
| `gradient-blue-from` | `#3B82F6` | `#3B82F6` | `#60A5FA` | `#F97316` |
| `gradient-blue-to` | `#93C5FD` | `#1E40AF` | `#3B82F6` | `#FDBA74` |
| `gradient-purple-from` | `#8B5CF6` | `#8B5CF6` | `#A78BFA` | `#FB923C` |
| `gradient-purple-to` | `#C4B5FD` | `#5B21B6` | `#7C3AED` | `#F97316` |
| `gradient-green-from` | `#10B981` | `#10B981` | `#34D399` | `#FBBF24` |
| `gradient-green-to` | `#6EE7B7` | `#047857` | `#059669` | `#F59E0B` |
| `gradient-orange-from` | `#F59E0B` | `#F59E0B` | `#FBBF24` | `#F87171` |
| `gradient-orange-to` | `#FCD34D` | `#B45309` | `#D97706` | `#EF4444` |
| `card-elevated` | `#F9FAFB` | `#162032` | `#1A1D24` | `#211A14` |
| `card-highlight` | `#EFF6FF` | `#1E3A5F` | `#1E293B` | `#2D1F14` |
| `card-stat` | `#F0F9FF` | `#0F2847` | `#111827` | `#1A1208` |

### 4.3 Tailwind Utility Mapping Additions

In `tailwind.config.ts`, under `theme.extend.colors.yc`:

```typescript
// Add to existing yc mapping
'chart-1': 'var(--yc-chart-1)',
'chart-2': 'var(--yc-chart-2)',
// ... through chart-8
'chart-grid': 'var(--yc-chart-grid)',
'chart-axis': 'var(--yc-chart-axis)',
'chart-tooltip-bg': 'var(--yc-chart-tooltip-bg)',
'chart-tooltip-border': 'var(--yc-chart-tooltip-border)',
'chart-tooltip-text': 'var(--yc-chart-tooltip-text)',
'gradient-blue-from': 'var(--yc-gradient-blue-from)',
'gradient-blue-to': 'var(--yc-gradient-blue-to)',
'gradient-purple-from': 'var(--yc-gradient-purple-from)',
'gradient-purple-to': 'var(--yc-gradient-purple-to)',
'gradient-green-from': 'var(--yc-gradient-green-from)',
'gradient-green-to': 'var(--yc-gradient-green-to)',
'gradient-orange-from': 'var(--yc-gradient-orange-from)',
'gradient-orange-to': 'var(--yc-gradient-orange-to)',
'card-elevated': 'var(--yc-card-elevated)',
'card-highlight': 'var(--yc-card-highlight)',
'card-stat': 'var(--yc-card-stat)',
```

---

## 5. Storage & State Flow: Theme Switch Mechanism

### 5.1 Current Flow (No Change Needed)

```
User clicks theme selector
  --> useThemeStore.setTheme(themeName)
  --> ThemeProvider detects store change
  --> applyTheme(themeName) called
  --> document.documentElement.style.setProperty('--yc-xxx', value) for all tokens
  --> CSS variables update on :root
  --> Tailwind yc-* utilities resolve new values
  --> Ant Design ConfigProvider receives new theme config
  --> Components re-render with new styles
```

This flow already works. The new tokens are automatically included because `applyTheme` iterates all keys in the token map and sets CSS variables. No infrastructure change is needed.

### 5.2 Recharts Color Update Flow

```
ThemeProvider applies new CSS variables
  --> useThemeStore.theme value changes
  --> Components using useChartColors() re-render (hook depends on theme)
  --> useChartColors reads CSS variables via getComputedStyle
  --> Returns new chart color values
  --> Recharts components receive new fill/stroke/gradient props
  --> Charts re-render with new colors
```

### 5.3 useChartColors Hook Design

```typescript
// frontend/src/hooks/useChartColors.ts
import { useMemo } from 'react';
import { useThemeStore } from '@/store/useThemeStore';

function readVar(name: string): string {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
}

export function useChartColors() {
  const theme = useThemeStore(s => s.theme);

  return useMemo(() => {
    const series = Array.from({ length: 8 }, (_, i) =>
      readVar(`--yc-chart-${i + 1}`)
    );

    const gradient = {
      blue: [readVar('--yc-gradient-blue-from'), readVar('--yc-gradient-blue-to')] as [string, string],
      purple: [readVar('--yc-gradient-purple-from'), readVar('--yc-gradient-purple-to')] as [string, string],
      green: [readVar('--yc-gradient-green-from'), readVar('--yc-gradient-green-to')] as [string, string],
      orange: [readVar('--yc-gradient-orange-from'), readVar('--yc-gradient-orange-to')] as [string, string],
    };

    return {
      series,
      grid: readVar('--yc-chart-grid'),
      axis: readVar('--yc-chart-axis'),
      tooltip: {
        bg: readVar('--yc-chart-tooltip-bg'),
        border: readVar('--yc-chart-tooltip-border'),
        text: readVar('--yc-chart-tooltip-text'),
      },
      gradient,
    };
  }, [theme]);
}
```

---

## 6. Sprint Planning

### Sprint 0: Infrastructure (1 day)

**Goal**: Extend token system, add new hook, add markdown CSS.

| Task | File(s) | Est. |
|------|---------|------|
| Add 20 new tokens to `ThemeTokens` interface and `defaultTokens` | `tokens.ts` | 0.5h |
| Add 20 new token values for all 4 themes | `light.ts`, `deep-blue.ts`, `liblib-dark.ts`, `warm-orange.ts` | 1h |
| Add 20 new `yc-*` utility mappings | `tailwind.config.ts` | 0.5h |
| Create `useChartColors` hook | `hooks/useChartColors.ts` (new) | 1h |
| Create markdown theme CSS | `styles/markdown-theme.css` (new) | 0.5h |
| Add `markdown-preview` class to MarkdownPreview | `MarkdownPreview.tsx` | 0.5h |
| Verify: toggle all 4 themes, check new tokens apply correctly | Browser test | 0.5h |

**Verification**: After Sprint 0, `getComputedStyle(document.documentElement).getPropertyValue('--yc-chart-1')` returns the correct value per theme.

### Sprint 1: Low-Complexity Pages (1 day)

**Goal**: Theme-adapt the 3 simplest pages. These have few hardcoded values and no recharts.

| Task | Page | Hardcoded Count | Est. |
|------|------|----------------|------|
| ConfigCenter | `settings/ConfigCenter.tsx` | ~8 | 1h |
| ChannelList | `youtube/ChannelList.tsx` | ~10 | 1.5h |
| GlobalVideoList | `youtube/GlobalVideoList.tsx` | ~15 | 2h |

**Pattern**: All changes are P1 (direct yc-* swap) or P2 (new yc-* swap). No chart hook needed.

**Verification**: Toggle each theme, visual check that colors adapt. No hardcoded hex/rgba should remain.

### Sprint 2: Medium-Complexity Pages with Charts (1.5 days)

**Goal**: Theme-adapt 2 pages that use recharts charts.

| Task | Page | Hardcoded Count | Est. |
|------|------|----------------|------|
| CompetitorAnalysis | `youtube/CompetitorAnalysis.tsx` | ~20 + recharts | 3h |
| ChannelDetail | `youtube/ChannelDetail.tsx` | ~40 + recharts | 5h |

**Pattern**: P1/P2 for Tailwind arbitrary values, P3 (chart hook) for recharts. ChannelDetail is the largest in this sprint.

**Verification**: Toggle each theme, check chart colors adapt. Verify chart tooltips, legends, and grid lines change with theme.

### Sprint 3: Radar Pages (1.5 days)

**Goal**: Theme-adapt the 2 radar pages. High Tailwind arbitrary value count but no recharts in NavigationGuide.

| Task | Page | Hardcoded Count | Est. |
|------|------|----------------|------|
| NavigationGuide | `radar/NavigationGuide.tsx` | ~25 | 3h |
| BlueOceanRadar | `radar/BlueOceanRadar.tsx` | ~45 | 5h |

**Pattern**: P1/P2 for all Tailwind arbitrary values, P5 for gradients. NavigationGuide has recharts (pie/bar charts) -- needs P3.

**Verification**: Toggle each theme, check all cards, stats, tables, and charts adapt.

### Sprint 4: VideoBoard Full Refactor (1 day)

**Goal**: Refactor VideoBoard from fully hardcoded deep-blue palette to theme-aware.

| Task | Page | Hardcoded Count | Est. |
|------|------|----------------|------|
| VideoBoard | `board/VideoBoard.tsx` | ~55 | 6h |

**Risk**: This is the highest-risk page because it currently only looks correct under deep-blue. After refactoring, it must look correct under ALL 4 themes. Requires careful visual QA.

**Pattern**: P1/P2 for all Tailwind arbitrary values. May need P5 for gradient backgrounds on stat cards.

**Verification**:
1. Under deep-blue theme, VideoBoard should look identical to current (regression check).
2. Under light theme, all backgrounds, text, borders should be visible and readable.
3. Under liblib-dark and warm-orange, visual consistency with the rest of the app.

### Sprint 5: Integration QA & Polish (0.5 day)

| Task | Est. |
|------|------|
| Full regression: toggle all 4 themes across all 8 pages | 1h |
| Verify MarkdownPreview renders correctly in all themes | 0.5h |
| Verify recharts chart responsiveness after theme change | 0.5h |
| Fix any visual discrepancies found | 1h |
| Code review | 0.5h |

### Total Estimate

| Sprint | Duration | Cumulative |
|--------|----------|------------|
| Sprint 0: Infrastructure | 1 day | 1 day |
| Sprint 1: Simple pages | 1 day | 2 days |
| Sprint 2: Chart pages | 1.5 days | 3.5 days |
| Sprint 3: Radar pages | 1.5 days | 5 days |
| Sprint 4: VideoBoard | 1 day | 6 days |
| Sprint 5: QA & Polish | 0.5 day | 6.5 days |

**Total**: ~6.5 working days.

---

## 7. Risk Matrix

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Token value mismatch (theme looks wrong) | High | Medium | Visual QA in Sprint 5; compare screenshots before/after under each theme |
| VideoBoard regression under deep-blue | High | Low | Take screenshot before refactor; compare pixel-level after |
| Recharts gradient not updating on theme switch | Medium | Low | `useChartColors` depends on `theme` from store; triggers re-render |
| Missing semantic token for a pattern | Low | Medium | Add to `decorative-*` group as fallback; document for future cleanup |
| MarkdownPreview styling conflicts | Low | Low | Use scoped `.markdown-preview` class; test with actual markdown content |

---

## 8. Out of Scope

The following are explicitly out of scope for this effort:

- Adding new themes beyond the existing 4
- Refactoring pages not listed in the 8 target pages (other pages will be addressed in future iterations)
- Building a theme editor or visual token preview tool
- Changing the Ant Design component library version
- Performance optimization of CSS variable application
- Server-side rendering (SSR) considerations
