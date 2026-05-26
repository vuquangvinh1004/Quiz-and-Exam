---
version: alpha
name: Quiz Desktop Clarity
description: Token-driven visual system for the Quiz Desktop App (PySide6).
colors:
  primary: "#1abc9c"
  secondary: "#2c3e50"
  tertiary: "#0e639c"
  neutral: "#f5f5f5"
  on-primary: "#ffffff"
  on-secondary: "#ecf0f1"
  on-tertiary: "#ffffff"
  on-neutral: "#212121"
  surface-light: "#ffffff"
  surface-dark: "#1e1e1e"
  border-light: "#d0d5dd"
  border-dark: "#3e3e42"
  muted-light: "#666666"
  muted-dark: "#aaaaaa"
  success: "#1f8f5f"
  warning: "#e8d44d"
  danger: "#c0392b"
typography:
  title-lg:
    fontFamily: Segoe UI
    fontSize: 20px
    fontWeight: 700
    lineHeight: 1.2
  body-md:
    fontFamily: Segoe UI
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.4
  label-sm:
    fontFamily: Segoe UI
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.3
rounded:
  sm: 4px
  md: 6px
  lg: 8px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
components:
  nav-button-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.sm}"
    padding: 10px
  table-selection:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
  input-default:
    backgroundColor: "{colors.surface-light}"
    textColor: "{colors.on-neutral}"
    rounded: "{rounded.sm}"
---

# Quiz Desktop Clarity

## Overview

Quiz Desktop Clarity is a pragmatic, high-legibility system for long quiz sessions.
It emphasizes comprehension speed, low visual noise, and confident action states.
Primary interactions are highlighted by a single accent role while core text remains calm.

## Colors

The palette uses one action accent and stable neutrals.

- Primary (#1abc9c): main action emphasis and selected state.
- Secondary (#2c3e50): structural anchor for side navigation.
- Tertiary (#0e639c): dark-theme action emphasis.
- Neutral (#f5f5f5): default light background.
- On-* tokens guarantee readable text on each semantic surface.

## Typography

Typography is intentionally conservative to reduce fatigue in dense quiz workflows.

- Title: 20px bold for screen/view headings.
- Body: 14px regular for default reading and forms.
- Label: 13px regular for metadata and helper text.

## Layout

Layout follows a simple desktop rhythm:

- Main app: fixed sidebar + flexible content area.
- Spacing scale is 4/8/16/24/32.
- Forms and controls align to the same vertical rhythm.

## Elevation & Depth

Depth is subtle and mostly communicated by borders, not large shadows.

- Cards and sections use border contrast.
- Selection and focus use color-state transitions, not heavy elevation.

## Shapes

Shape language is restrained and consistent.

- Inputs and buttons use small radii for clarity and density.
- Stat cards can use larger radius for grouping emphasis.

## Components

Key reusable component rules:

- Nav button active state must use primary + on-primary.
- Data table selection must align with primary accent.
- Input focus ring/border must be visible and theme-aware.
- Status and helper text must use muted semantic tokens.

## Do's and Don'ts

Do:

- Use semantic tokens, not ad-hoc hex values.
- Keep action emphasis to one dominant accent per screen.
- Preserve consistent spacing and radius scale.

Don't:

- Introduce new one-off colors when an existing token fits.
- Mix unrelated depth models or radii within one screen.
- Hide important state changes only by tiny color differences.
