# Design System Workflow

This document defines the mandatory workflow for UI changes in Quiz Desktop App.

## 1. Inputs and source of truth

- Root DESIGN.md is the product-level visual constitution.
- design.md-0.1.0/README.md and design.md-0.1.0/docs/spec.md define format and lint rules.
- UI implementation must consume semantic tokens, not ad-hoc color values.

## 2. Required process for UI changes

1. Clarify scope: which screens/components are touched.
2. Update tokens and prose in DESIGN.md first.
3. Run lint:

```bash
npx @google/design.md lint DESIGN.md
```

1. If changing token semantics/meaning, run diff against previous snapshot:

```bash
npx @google/design.md diff DESIGN_old.md DESIGN.md
```

1. Update token adapters in ui/styles before editing component/view styles.
1. Validate affected UI via smoke tests.

## 3. Token usage policy

- Prefer semantic names such as primary, on-primary, border-light, muted-dark.
- Do not introduce direct hex values in views/dialogs/widgets when a token exists.
- If a new visual role is required, add token first, then implementation.

## 4. Quality gates

A UI task is complete only when:

- DESIGN.md lint has no error-level findings.
- No broken token references exist.
- Contrast for normal text meets WCAG AA.
- Changed screens render correctly in both light and dark themes.
- Related unit/smoke tests pass.

## 5. Incremental migration note

The current codebase still contains legacy QSS literals.
Migration strategy is incremental:

- Phase 1: centralize semantic token maps in ui/styles.
- Phase 2: replace hardcoded literals in high-traffic components.
- Phase 3: enforce token-only style checks in CI.
