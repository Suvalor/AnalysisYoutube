# ScriptWorkflowSOP Vite Syntax Error Diagnosis

Date: 2026-05-22

## Symptom

Vite reports:

```text
[plugin:vite:react-swc] Expected '</', got 'ident'
frontend/src/pages/sop/ScriptWorkflowSOP.tsx:800:1
```

The first failing line is:

```tsx
placeholder={t(“label.aiResultPlaceholder”)}
```

## Root Cause

`frontend/src/pages/sop/ScriptWorkflowSOP.tsx` contains smart quotes (`“`, `”`) in TSX syntax. TSX only accepts ASCII quotes (`"` or `'`) for string literals and JSX attributes. The parser stops at line 800, but there are additional smart quote occurrences later in the same file.

The Chinese locale file also contains Chinese quotation marks in user-facing text. Those are inside JSON string values and are valid content, so they do not need to be changed.

## Required Source Fixes

Replace smart quotes with ASCII quotes in these `ScriptWorkflowSOP.tsx` locations:

```text
800: placeholder={t("label.aiResultPlaceholder")}
849: <div className="rounded-lg border border-yc-border bg-yc-bg-secondary p-4 text-yc-text-secondary">
850: {t("card.noShots")}
863: <div className="mt-3 text-xs text-yc-text-secondary">{t("card.dragHint")}</div>
926: <div className="text-xs text-yc-text-secondary">
927: {t("card.publishOnlyWhenReady")}
1071: <div className="col-span-2 text-xs text-yc-text-secondary border border-dashed border-yc-border rounded p-3 text-center">
1072: {t("card.noAssets")}
```

## Suggested Verification

After applying the replacements:

```shell
cd frontend
npm run build
```

Optional targeted scan:

```shell
rg -n '[“”‘’]' frontend/src/pages/sop/ScriptWorkflowSOP.tsx
```

Expected result: no matches in `ScriptWorkflowSOP.tsx`.
