# Value Review: Frontend i18n Gap Fill (全盘国际化补充)

**Date**: 2026-05-20
**Task Level**: L2 (Cross-module)
**Reviewer**: Cognitive Engine v4.0

---

## 1. First Principles: What Does the User Actually Need?

### Surface Request
"Already did i18n, now need to fill in the gaps -- internationalize everything not yet internationalized."

### Root Need (One Level Deeper)
The user has invested in i18n infrastructure (react-i18next, 4 languages, 4 namespaces) and now sees ~1936 lines of hardcoded Chinese across 63 source files that break the multilingual experience. The real purpose is: **when a non-Chinese user switches language, the entire UI should respond, not just 4 pages out of 67+ files.**

### Physical Form
This task is essentially: **find-and-replace ~1500-1800 hardcoded string literals with translation key lookups, and create corresponding key-value pairs in 4 JSON files per namespace.** The infrastructure already works; the labor is mechanical extraction and key assignment.

### First Principles Verdict
This is NOT an XY problem. The user has a working i18n system and gaps that directly undermine it. The ask is legitimate and proportional. No simpler alternative achieves "language switch actually works everywhere."

---

## 2. Dialectical Analysis: Trade-offs

### Thesis (Do It Fully)
- **Benefit**: Product becomes genuinely usable in 4 markets. Current state is worse than no i18n -- users see a language switcher that only works on 4 pages, creating false expectations.
- **Benefit**: Future language additions become trivial (add a JSON file).
- **Benefit**: Terminology consistency enforced by centralized key-value pairs (e.g., "channel" is always one term, not "频道" / "博主" / "频道号" depending on which page you're on).

### Antithesis (Don't Do It)
- **Cost**: ~1500-1800 string extractions across 63 files. Estimated 20-30 hours of careful manual or semi-automated work. High risk of regression if keys are misspelled or misplaced.
- **Cost**: Every future UI change now requires updating 4 JSON files instead of 1 inline string. Developer friction increases.
- **Cost**: Namespace design decisions have long-tail consequences. Wrong namespace boundaries cause circular dependencies or bloated bundles.

### Synthesis (Partial / Phased Approach)
Not all Chinese strings have equal user impact. A prioritized rollout captures 80% of user-visible value with 20% of the effort:

1. **High-impact, low-risk**: Navigation labels, page titles, common action buttons (save/cancel/delete) -- many already exist in `common.json` and `nav.json`, just not consumed.
2. **Medium-impact**: Form labels, table column headers, error/success messages in top-10 most-used pages.
3. **Low-impact**: Theme names/descriptions (4 strings, admin-only), service-layer error messages (thrown to console, not user-facing in most cases), internal placeholders.

**Key Tension**: The current i18n infrastructure already has ~7.5KB of zh-CN translations across 4 namespaces. The gap fill will multiply this by 10-15x. The JSON structure must be designed for navigability, or it becomes unmaintainable.

---

## 3. Systems Thinking: Cascade Effects

### Build-Time
- i18n JSON files are statically imported (not lazy-loaded). Adding 10-15x more keys increases initial bundle size. At current ~32KB total for all 4 locales, even 10x growth (~320KB) is acceptable for a SPA, but should be monitored.
- **Risk**: If namespaces grow without lazy-loading, each page loads ALL translation keys, not just its own.

### Runtime
- No runtime performance concern. `t()` lookups are O(1) hash lookups.
- **Risk**: React re-renders on language change. With many `useTranslation()` calls across 63 files, a language switch triggers a full app re-render. Currently only 4 files subscribe; 63 files subscribing could cause a noticeable flicker. Mitigation: React concurrent features or `Trans` component for static content.

### Developer Experience
- **Positive**: Centralized terminology. No more "did I spell this button label the same way as last time?"
- **Negative**: Adding a new label now requires: (1) decide namespace, (2) pick key name, (3) add to 4 locale files, (4) use `t('ns:key')` in component. 4 steps vs 1 inline string.
- **Negative**: Code review becomes harder -- reviewers must cross-reference JSON files to verify key correctness.

### Maintenance Surface
- 4 languages x ~12-15 namespaces x ~50-100 keys each = ~3000-6000 key-value pairs to keep in sync.
- Machine-translated ja-JP/ko-KR will have quality issues. Need a process for human review of critical paths.

### Duplication Risk
- `src/locales/zh-CN.json` (legacy) vs `src/i18n/locales/zh-CN/*.json` (current). Must be resolved before adding more keys. Legacy file should be deleted or migrated.

---

## 4. Critical Thinking: Edge Cases and Self-Attack

### Is This an XY Problem?
No. The user explicitly says "i18n is done, fill the gaps." They are not asking for a different solution; they are asking to complete an in-progress one.

### What Could Go Horribly Wrong?
1. **Key collision**: Two components use key "title" in the same namespace with different meanings. Current flat structure in some namespaces makes this likely. **Mitigation**: Namespace per page/module (e.g., `radar`, `settings`, `youtube`) rather than functional grouping.
2. **Template literal fragmentation**: Strings like `"混编任务已提交，可在任务中心查看进度"` contain both static text and embedded logic. Splitting into `"混编任务已提交，可在{{location}}查看进度"` requires interpolation discipline.
3. **Backend error messages in services/**: 7 hardcoded Chinese error strings in services (e.g., `throw new Error("对象存储直传失败（HTTP ${res.status}）")`). These are NOT user-facing (they're caught by apiClient interceptor which shows a generic error). Internationalizing them is low-value and risks changing error-handling behavior. **Recommendation**: Skip services/ layer for now.
4. **Theme names**: Only 4 strings, admin-only UI. Can be deferred to a later pass without user impact.
5. **Test files**: 5 test files have Chinese assertion strings. These should NOT be internationalized -- they're testing code, not UI.

### Simpler Alternative?
**Option A: Automated extraction tool**. Use `i18next-parser` (or similar) to auto-extract Chinese strings from codebase into JSON keys. Reduces manual labor by ~60%. Risk: auto-generated key names are opaque (e.g., `key1234`). Requires human review of key naming.

**Option B: Component-level namespace loading**. Instead of adding all keys upfront, create namespaces per page and only populate them when that page is worked on. Spreads the work over time but never delivers "complete i18n."

**Option C: Hybrid approach (recommended)**. Use `i18next-parser` for extraction + manual key naming + phased rollout by page priority. This is the lightest path to "complete i18n" without a Big Bang rewrite.

---

## 5. Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Key name collisions within namespace | HIGH | MEDIUM | Use page-scoped namespaces (`radar`, `youtube`, `settings`) |
| Regression from misspelled keys | HIGH | HIGH | Add CI check: `i18next --fail-on-missing-keys` or custom script |
| Bundle size bloat from static imports | MEDIUM | LOW | Monitor; add lazy namespace loading if >100KB |
| Machine translation quality (ja-JP, ko-KR) | LOW | HIGH | Flag MT keys in JSON with `_mt: true`; plan human review |
| Legacy `locales/zh-CN.json` conflicts | MEDIUM | MEDIUM | Delete legacy file before starting gap fill |
| Developer friction (4-file edits per string) | MEDIUM | CERTAIN | Provide script/tooling for key addition |
| services/ layer error messages | LOW | CERTAIN | Explicitly exclude from scope |

---

## 6. Recommended Approach

### Scope
- **IN scope**: All UI-facing Chinese in `pages/`, `components/`, `config/features.ts`, `store/` (user-visible strings only)
- **OUT of scope**: Code comments, test files, `services/` layer error strings, theme descriptions, aria-labels
- **Estimated key count**: ~1200-1500 new keys across ~10 new namespaces

### Namespace Strategy
Current: `common`, `nav`, `auth`, `settings` (4 namespaces)
Proposed: Add per-module namespaces: `radar`, `youtube`, `keyword`, `seo`, `trend`, `inspiration`, `knowledge`, `sop`, `feishu`, `admin`, `components`

Rationale: Page-scoped namespaces prevent key collision, enable lazy loading, and make it clear which keys belong to which feature.

### Phasing
1. **Phase 1** (Quick wins): Pages with highest Chinese count and most user exposure -- NavigationGuide(218), ConfigCenter(143), ChannelList(134), BlueOceanRadar(130). Also delete legacy `locales/zh-CN.json`.
2. **Phase 2** (Core pages): ScriptWorkflowSOP, ChannelDetail, GlobalVideoList, TrendDiscovery, InspirationPool, SeoScoring, AssetLibrary, KeywordResearch.
3. **Phase 3** (Remaining): All other pages, shared components, store user-visible strings.

### Automation
- Use `i18next-parser` for initial extraction
- Add `eslint-plugin-i18next` to CI to prevent new hardcoded strings
- Create a script to sync keys across 4 locale files with MT placeholder

---

## 7. Core Contradiction

**The fundamental tension**: Completeness vs. Sustainability.
Full i18n coverage is the right goal, but achieving it in one shot creates a massive, fragile PR that is hard to review and easy to regress. Phased delivery is slower to "complete" but each phase is reviewable, testable, and incrementally reduces the gap.

The MVP insight: **A user who switches to English and sees 70% of the UI in English is far better served than one who sees 6% (current state).** Phase 1 alone (4 highest-traffic pages + existing infrastructure) would take coverage from ~6% to ~40%.

---

## 8. Verdict

VERDICT: PASS

Rationale: The need is legitimate, the infrastructure exists, and the gap is directly undermining the existing investment. The phased approach mitigates the main risks (regression, review burden, bundle size). Services/ layer and themes should be explicitly excluded from scope. Key risks (collision, missing keys) have concrete mitigations. The task is labor-intensive but not architecturally complex -- it is the right kind of " grind" that delivers real user value.

**Risk flag**: HIGH -- key namespace design must be decided before Phase 1 begins. Wrong namespace boundaries are expensive to refactor once 1500 keys are in place.

**Risk flag**: MEDIUM -- CI enforcement (`eslint-plugin-i18next` or equivalent) must be added in Phase 1, otherwise new hardcoded strings will immediately re-accumulate.
