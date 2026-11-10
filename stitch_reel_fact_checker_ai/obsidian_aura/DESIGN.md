---
name: Obsidian Aura
colors:
  surface: '#131316'
  surface-dim: '#131316'
  surface-bright: '#39393c'
  surface-container-lowest: '#0e0e11'
  surface-container-low: '#1c1b1e'
  surface-container: '#201f22'
  surface-container-high: '#2a2a2d'
  surface-container-highest: '#353438'
  on-surface: '#e5e1e5'
  on-surface-variant: '#c6c5d5'
  inverse-surface: '#e5e1e5'
  inverse-on-surface: '#313033'
  outline: '#908f9e'
  outline-variant: '#454653'
  surface-tint: '#bdc2ff'
  primary: '#bdc2ff'
  on-primary: '#131e8c'
  primary-container: '#818cf8'
  on-primary-container: '#101b8a'
  inverse-primary: '#4953bc'
  secondary: '#c0c1ff'
  on-secondary: '#1000a9'
  secondary-container: '#3131c0'
  on-secondary-container: '#b0b2ff'
  tertiary: '#4edea3'
  on-tertiary: '#003824'
  tertiary-container: '#00aa76'
  on-tertiary-container: '#003522'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e0e0ff'
  primary-fixed-dim: '#bdc2ff'
  on-primary-fixed: '#000767'
  on-primary-fixed-variant: '#2f3aa3'
  secondary-fixed: '#e1e0ff'
  secondary-fixed-dim: '#c0c1ff'
  on-secondary-fixed: '#07006c'
  on-secondary-fixed-variant: '#2f2ebe'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#131316'
  on-background: '#e5e1e5'
  surface-variant: '#353438'
typography:
  display:
    fontFamily: Plus Jakarta Sans
    fontSize: 40px
    fontWeight: '600'
    lineHeight: 48px
    letterSpacing: -0.03em
  display-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 38px
    letterSpacing: -0.025em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 22px
    fontWeight: '500'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '500'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: -0.005em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0.01em
  mono-code:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: -0.01em
  mono-label:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.06em
  caption:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-mobile: 0.75rem
  margin: 1.5rem
  margin-mobile: 1.25rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

The design system establishes an atmospheric, contemplative, and technologically uncompromising aesthetic. Built for discerning operators, researchers, and high-signal thinkers, it eliminates generic artificial intelligence tropes—banishing glowing neon circuits, robotic avatars, cartoonish sparkle icons, and claustrophobic chip clusters. 

The aesthetic is grounded in **Obsidian Editorial Minimalism with Ambient Chromatic Depths**. It treats the OLED display as pure void space: infinite obsidian black (#050507) punctuated by whisper-quiet smoked indigo and violet gradients bleeding organically beneath ultra-fine frosted glass surfaces. Precision comes from typographic scale, hairline structural divisions, and generous spatial discipline rather than dense visual ornamentation. Interactions should feel deliberate, quiet, and weighted with authority.

## Colors

The palette operates under absolute chromatic restraint to preserve pure OLED black balance and prevent visual fatigue:

- **Canvas Base:** `#050507` (True Obsidian). Never dilute the root background with mid-tone gray washes.
- **Glass / Surface Layers:** `rgba(18, 18, 23, 0.65)` layered over deep, diffuse atmospheric underglows with `backdrop-filter: blur(24px)`.
- **Primary Accents:** Muted electric indigo (`#818CF8`) and refined violet (`#6366F1`), reserved strictly for primary actions, subtle focus states, and verified metadata anchors.
- **Aura Ambient Underglows:** Gradients of `#4338CA` and `#312E81` locked strictly to low opacities (`0.06` to `0.14`) with ultra-wide radial spreads (180px–320px blur).
- **Text & Content Hierarchy:**
  - High-Contrast Primary: `#F9FAFB` (98% luminance white).
  - Secondary / Supporting: `#8E8E93` (Cool Muted Gray).
  - Tertiary / Subtle Meta: `#636366` (Smoked Lead).
- **Critical / Larp Alert:** Deep blood rose ground `rgba(76, 5, 25, 0.20)`, bordered by hairline `rgba(244, 63, 94, 0.20)`, with surgical red text (`#FB7185` and `#F43F5E`).
- **Verified / Truth Accents:** Pristine emerald (`#10B981`), used strictly for cryptographically confirmed states and affirmative metrics.
- **Hairline Dividers & Glass Borders:** `rgba(255, 255, 255, 0.06)` for standard separation; `rgba(255, 255, 255, 0.09)` for active interactive bounds.

## Typography

Typography prioritizes high-clarity reading dynamics, combining the sculpted geometry of Plus Jakarta Sans for titles with the industrial neutrality of Inter for extended discourse. JetBrains Mono serves as an editorial instrument to render cryptographic hashes, temporal logs, precision telemetry, and section tags.

- **Headlines:** Set tight with deliberate negative letter spacing to yield crisp density against OLED voids.
- **Body:** Generous line heights ensure uninterrupted cognitive scanning. Avoid pure white for long-form reading; default to `#E5E7EB` on obsidian bases to minimize ocular strain.
- **Monospace Metadata:** Uppercase micro-labels in JetBrains Mono (`mono-label`) establish strict editorial hierarchy without requiring decorative chip badges or rounded stickers.

## Layout & Spacing

The layout philosophy follows a strict fluid canvas model built upon an 8pt base grid with a 4pt sub-grid for minute micro-alignments:

- **Mobile Canvas:** A 4-column fluid structure flanked by `1.25rem` (20px) outer edge margins, expanding to `1.5rem` (24px) on tablet viewports.
- **Negative Space Ratio:** Vertical rhythm relies on deliberate spatial intervals (`space-xl` and `space-lg`) between logical blocks rather than heavy separator cards or bounding boxes. Let content breathe against the deep obsidian canvas.
- **Reflow & Docking:** Critical navigation and trigger actions dock within safe areas at the screen base, rendered with blurred backdrop shields (`rgba(5, 5, 7, 0.85)` + 20px blur) to prevent hard clipping over scrolling text.

## Elevation & Depth

Visual hierarchy abandons traditional drop shadows, directional skeuomorphism, and opaque card stack tiers. Depth is achieved via **diffuse ambient radiance and multi-layered atmospheric translucency**:

1. **Layer 0 (Canvas Void):** `#050507` baseline.
2. **Layer 1 (Atmospheric Plasma Aura):** Low-frequency radial gradients (`rgba(99, 102, 241, 0.08)` to `rgba(67, 56, 202, 0.03)`) positioned contextually behind high-signal insights and core interactions, bleeding directly into the obsidian baseline without hard geometric bounds.
3. **Layer 2 (Smoked Obsidian Glass):** `rgba(18, 18, 23, 0.60)` surfaces treated with `backdrop-filter: blur(20px)` and framed by ultra-fine hairline outlines (`1px solid rgba(255, 255, 255, 0.06)`).
4. **Layer 3 (Floating Controls & Sheets):** Elevated contextual elements use `rgba(24, 24, 31, 0.80)`, 28px blur, and an ultra-soft ambient shadow (`0 20px 40px -15px rgba(0, 0, 0, 0.7)` combined with `0 0 1px 1px rgba(255, 255, 255, 0.08)`).

## Shapes

The design system employs an architectural curvature standard. Roundedness level 2 enforces a structured, tailored feel (8px baseline corners on standard elements, 16px on structural cards, and 24px on major bottom sheets):

- **Structural Cards & Panels:** `rounded-lg` (16px) produces a balanced silhouette that feels engineered rather than bubbly or toy-like.
- **Inputs & Action Triggers:** 10px to 12px radii ensure tactile comfort without degrading into generic pill shapes.
- **Continuous Curvature:** All corner geometry must employ iOS-style squircle smoothing (`corner-smoothing: 60%` or continuous corner radius) to eliminate optical pinching at line junctions.

## Components

### Buttons & Interactive Triggers
- **Primary:** High-contrast solid pure white (`#FFFFFF`) with deep obsidian typography (`#050507`, weight 600). Hover/Active state shifts to muted indigo tint (`#E0E7FF`). Never use bright gradient buttons.
- **Secondary:** Smoked glass background (`rgba(255, 255, 255, 0.04)`), hairline outline (`rgba(255, 255, 255, 0.08)`), white text (`#F9FAFB`).
- **Ghost / Tertiary:** Borderless, clean typography in `#8E8E93`, shifting to `#FFFFFF` on active press.

### Cards & Intelligence Panels
- Translucent smoked charcoal plate (`rgba(18, 18, 23, 0.55)`), 16px radius, enclosed by a microscopic hairline border (`rgba(255, 255, 255, 0.06)`).
- When a panel contains active intelligence or verified truth assertions, place a deep violet ambient gradient underglow beneath the surface plate rather than rendering glowing outlines or neon banners.

### Form Inputs & Prompts
- Background: `rgba(255, 255, 255, 0.03)`. Hairline border: `rgba(255, 255, 255, 0.08)`.
- Typography: Inter 14px (`#F9FAFB`) with placeholder copy subdued to `#636366`.
- Focus state: Subtle shift of the hairline border to `rgba(129, 140, 248, 0.40)` with zero fuzzy outer glow halos.

### Metadata Labels & Status Indication (Zero-Pill Architecture)
- Replaces generic rounded badge pills with clean monospace typographical pairings.
- Example: A status indicator is composed of a micro 4px square or diamond dot (`#10B981` or `#FB7185`) followed directly by `mono-label` uppercase tracking text (`VERIFIED // CONFIRMED` or `DISCORDANCE // DETECTED`). No surrounding pill container.

### Critical Alert / Larp Banner
- Background: `rgba(76, 5, 25, 0.16)`.
- Hairline Border: `rgba(244, 63, 94, 0.22)`.
- Accent & Copy: High-contrast red typography (`#FB7185`) paired with JetBrains Mono telemetry timestamps.

### Lists & Activity Feeds
- Completely borderless item rows separated purely by vertical space (`space-md`) or ultra-faint divider lines (`rgba(255, 255, 255, 0.04)`).
- Interactive touch targets exhibit a momentary smoked wash (`rgba(255, 255, 255, 0.03)`) upon press feedback.