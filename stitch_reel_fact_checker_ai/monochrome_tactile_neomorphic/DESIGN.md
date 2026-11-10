---
name: Monochrome Tactile Neomorphic
colors:
  surface: '#f7f9fc'
  surface-dim: '#d8dadd'
  surface-bright: '#f7f9fc'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f7'
  surface-container: '#eceef1'
  surface-container-high: '#e6e8eb'
  surface-container-highest: '#e0e3e6'
  on-surface: '#191c1e'
  on-surface-variant: '#46464b'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f4'
  outline: '#77777b'
  outline-variant: '#c7c6cb'
  surface-tint: '#5e5e62'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#1b1b1f'
  on-primary-container: '#848387'
  inverse-primary: '#c7c6ca'
  secondary: '#5d5f5f'
  on-secondary: '#ffffff'
  secondary-container: '#dfe0e0'
  on-secondary-container: '#616363'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#1f1b16'
  on-tertiary-container: '#8a827c'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e3e2e6'
  primary-fixed-dim: '#c7c6ca'
  on-primary-fixed: '#1b1b1f'
  on-primary-fixed-variant: '#46464a'
  secondary-fixed: '#e2e2e2'
  secondary-fixed-dim: '#c6c6c7'
  on-secondary-fixed: '#1a1c1c'
  on-secondary-fixed-variant: '#454747'
  tertiary-fixed: '#ebe1d9'
  tertiary-fixed-dim: '#cec5be'
  on-tertiary-fixed: '#1f1b16'
  on-tertiary-fixed-variant: '#4c4640'
  background: '#f7f9fc'
  on-background: '#191c1e'
  surface-variant: '#e0e3e6'
typography:
  headline-xl:
    fontFamily: Space Grotesk
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.03em
  headline-xl-mobile:
    fontFamily: Space Grotesk
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Space Grotesk
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 22px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '500'
    lineHeight: 24px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: Space Grotesk
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 18px
    letterSpacing: 0.02em
  label-md:
    fontFamily: Space Grotesk
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.04em
  label-sm:
    fontFamily: Space Grotesk
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.06em
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-tablet: 1.5rem
  gutter-desktop: 2rem
  margin: 1.25rem
  margin-tablet: 2rem
  margin-desktop: 3rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.25rem
---

## Brand & Style

This design system expresses a fusion of modern soft tactile neumorphism and ultra-glossy obsidian luxury. Created for high-tier fintech and wealth management interfaces, the aesthetic evokes precision, architectural solidity, and elevated prestige. It eliminates color noise entirely in favor of an exacting, high-contrast monochrome hierarchy.

The visual direction juxtaposes two tactile sensory poles:
1. **Porcelain Neumorphism:** Pale, matte surfaces with sculpted embossed and debossed depths, evoking stone, molded polymer, and clean industrial clay.
2. **Glossy Obsidian Glass:** Jet-black surfaces carrying liquid specular highlights, subtle radial refractions, and deep internal gloss, reminiscent of polished obsidian or luxury credit cards.

By eliminating chromatic distractions, every interface transition relies on light, physical elevation, and confident typography to project absolute trust, stability, and surgical financial control.

## Colors

The palette operates in strict high-contrast monochrome. Color expression comes exclusively from luminance, shadow diffusion, and translucent highlights.

- **Primary (`#0D0E11`):** Deep obsidian black. Used for primary CTAs, active payment card surfaces, hero metrics, and dominant typography.
- **Secondary (`#FFFFFF`):** Pure optical white. Serves as top-left ambient specular highlights, crisp foreground text on dark cards, and elevated card fill layers.
- **Neutral Canvas (`#F2F4F7`):** Soft porcelain neutral. Forms the baseline canvas from which extruded neumorphic elements emerge.
- **Subtle Muted Tones:** 
  - Neutral Subdued (`#6B7280` / `#9CA3AF`) for secondary labels, inactive timeframes, and helper captions.
  - Recessed Track Surface (`#E5E8ED`) for debossed sliders, inactive progress channels, and inset search inputs.
  - Gloss Highlight (`rgba(255, 255, 255, 0.15)` to `rgba(255, 255, 255, 0.03)`) for fluid-glass surface reflections across obsidian cards.

## Typography

The type system pairs **Space Grotesk** for numerical values, navigational headers, and structural labels with **Plus Jakarta Sans** for clear, legible financial lists and body communications.

- **Numerics & Display:** Space Grotesk provides technical geometric structure, ensuring account amounts, currency values, and percentages align with computational precision.
- **Body & Microcopy:** Plus Jakarta Sans introduces humanist clarity, keeping smaller labels and card metadata legible even at subtle opacity stops.
- **Tracking Discipline:** Headings utilize tight negative letter spacing (`-0.02em` to `-0.03em`) for a sculpted architectural presence, while micro labels carry expanded tracking (`+0.04em` to `+0.06em`) for effortless scanability on porcelain surfaces.

## Layout & Spacing

The layout model relies on soft, spacious padding to let neumorphic shadows spread without intersecting neighboring containers.

- **Grid Architecture:** 
  - Mobile (viewport &lt; 768px): Single-column vertical stream, `margin: 1.25rem`, `gutter: 1rem`.
  - Tablet (viewport 768px - 1024px): 6-column fluid grid, `margin-tablet: 2rem`, `gutter-tablet: 1.5rem`.
  - Desktop (viewport &gt; 1024px): 12-column layout centered at max-width 1200px, `margin-desktop: 3rem`.
- **Rhythm & Safe Distance:** Neumorphic drop shadows require at least `space-md` (16px) clearance around cards to prevent shadow clipping and overlapping blur mud. Micro elements inside cards maintain uniform `space-md` internal padding, while card modules separate by `space-lg` (24px) to `space-xl` (36px).

## Elevation & Depth

Visual hierarchy uses dual-light neumorphic projection paired with glossy specular reflections:

### 1. Extruded Porcelain Surfaces (Embossed)
Elements rising from the `#F2F4F7` ground use a dual directional light model simulating an ambient light source at 135 degrees (top-left):
- **Deep Outer Drop Shadow:** `8px 12px 24px rgba(0, 0, 0, 0.06), 2px 4px 8px rgba(0, 0, 0, 0.03)`
- **Top-Left Specular Refraction:** `-6px -6px 16px rgba(255, 255, 255, 0.95)`
- **Border Treatment:** A subtle 1px border `rgba(255, 255, 255, 0.7)` on top and `rgba(0, 0, 0, 0.02)` on bottom to reinforce physical edge catch.

### 2. Recessed Sockets (Debossed / Inset)
Used for inputs, search trays, and toggle tracks to indicate recessed touch targets:
- **Inner Shadow:** `inset 3px 3px 6px rgba(0, 0, 0, 0.08), inset -3px -3px 6px rgba(255, 255, 255, 0.9)`
- **Fill:** `#EBEFF5`

### 3. Obsidian Gloss Surfaces
High-priority interactive credit cards, spending modules, and primary buttons use deep obsidian glass:
- **Fill:** Solid `#0D0E11` layered with a multi-stop pseudo-gloss gradient: `radial-gradient(ellipse 120% 80% at 70% -20%, rgba(255, 255, 255, 0.22) 0%, rgba(255, 255, 255, 0.03) 45%, transparent 70%)`.
- **Shadow:** `0 16px 32px -8px rgba(0, 0, 0, 0.35), 0 4px 12px rgba(0, 0, 0, 0.15)`.
- **Edge Highlight:** 1px stroke with top-weighted sheen `linear-gradient(180deg, rgba(255, 255, 255, 0.35) 0%, rgba(255, 255, 255, 0.05) 100%)`.

## Shapes

The design system embraces an ultra-curved, tactile pill geometry (`roundedness: 3`).

- **Base Cards & Modules:** 28px to 32px corner radius (`rounded-2xl` / `rounded-3xl`), giving credit cards and statistics containers a polished, pebble-like contour.
- **Buttons, Chips & Inputs:** Full pill curvature (`border-radius: 9999px` or minimum 20px on small elements).
- **Bar Charts & Visual Data:** Chart bars feature generously rounded caps (minimum 12px pill radius on active columns) to reinforce the tactile, soft-edged nature of the entire interface.

## Components

### Buttons
- **Primary Action (Obsidian Pill):** Full pill (`9999px`), solid `#0D0E11` background, white Space Grotesk text, subtle top specular border. Padding: `16px 28px`. Hover/Active: transforms with slight inward scale (`scale(0.98)`) and deeper ambient shadow.
- **Neumorphic Soft Button:** White-to-porcelain surface fill, extruded soft shadow (`4px 6px 12px rgba(0,0,0,0.05)`, `-4px -4px 10px rgba(255,255,255,0.9)`), black icon or typography. Pressed state inverts to debossed inner shadow.
- **Icon Quick Action:** Circular 48x48px neumorphic extruded disk with centered monochrome glyph.

### Cards & Modules
- **Obsidian Credit Card:** 32px corner radius, `#0D0E11` with fluid glass reflection arc across upper half. Contains masked account digits (`•••• 8160`), bold typography, chip icon, and balance summary.
- **Porcelain Metric Card:** `#FFFFFF` or `#F7F8FA` background, extruded with soft dual drop shadows. Contains rounded visual bar charts or spending allocation rings.
- **Horizontal Transaction Cell:** Full-width rounded card (24px radius) with soft drop shadow, obsidian or porcelain avatar disk on the left, primary description, category subtitle, and right-aligned Space Grotesk currency value.

### Inputs & Sliders
- **Search & Text Input:** Pill-shaped debossed channel (`inset 2px 3px 6px rgba(0,0,0,0.06), inset -2px -3px 6px rgba(255,255,255,0.85)`), `#EAEFF5` surface fill, placeholder in `#9CA3AF`. Left-aligned monochrome search icon.
- **Tactile Amount Slider:** Debossed horizontal channel containing a solid obsidian pill slider thumb that casts an elevated shadow (`0 4px 10px rgba(0,0,0,0.25)`).

### Chips & Avatars
- **Preset Value Chips:** Full pill buttons with dual states:
  - *Inactive:* White porcelain with soft outer shadow, muted black text.
  - *Active:* Solid obsidian black with crisp white text.
- **Avatar Transfer Ring:** Circular portrait (52x52px) bordered with a soft 3px white cushion ring and ambient neumorphic elevation. Add-recipient button features a debossed plus (+) circle.

### Data Visualizations
- **Monochrome Bar Histogram:** Variable-height vertical pill bars. Inactive/ambient days use porcelain/gray pills (`#D1D5DB`); active/peak days feature elevated solid obsidian pills (`#0D0E11`) with rounded top and bottom caps.
- **Tactile Spending Rings / Pie Charts:** High-contrast monochrome divisions with subtle inner bevels to mimic carved liquid glass.