# Design System: Charm Studio

## 1. Visual Theme & Atmosphere

Charm Studio follows **Canonical's enterprise open-source aesthetic** — clean, professional, and trustworthy. The interface is structured and hierarchical, prioritising information density without visual clutter. The overall vibe is **"Focused Professional"**: generous whitespace, flat elevation, precise sharp-to-softly-rounded geometry, and a restricted palette anchored by Canonical Orange. A dark, terminal-style log panel provides contrast and reinforces the developer-tool identity.

- **Platform**: Web, Desktop-first (split-panel layout)
- **Framework**: Vanilla Framework CSS (Canonical design system) + React 18
- **Style mood**: Minimal, polished, structured, trustworthy

---

## 2. Color Palette & Roles

| Role | Name | Hex | Usage |
|---|---|---|---|
| **Brand / Primary Action** | Canonical Orange | `#E95420` | Primary buttons, active nav indicator, key CTAs |
| **Page Background** | Off-White Canvas | `#F5F5F5` | Main page background |
| **Surface / Card Background** | Pure White | `#FFFFFF` | Cards, panels, form fields |
| **Sidebar Background** | Light Cool Grey | `#F7F7F7` | Sidebar background, secondary surfaces |
| **Primary Text** | Near-Black | `#111111` | Headings, labels, primary body copy |
| **Secondary Text** | Medium Grey | `#666666` | Subtext, timestamps, helper text |
| **Border / Divider** | Light Grey | `#CDCDCD` | Card borders, input borders, dividers |
| **Status: Pending** | Neutral Grey | `#757575` | Pending chip background / text |
| **Status: Running** | Information Blue | `#0066CC` | Running chip, polling spinner accent |
| **Status: Done / Success** | Success Green | `#0E8420` | Done chip, result banner accent, positive notifications |
| **Status: Failed / Negative** | Error Red | `#C7162B` | Failed chip, error banner, negative button, red border on failed stage |
| **Status: Cancelled / Caution** | Caution Amber | `#F99B11` | Cancelled chip, caution notification |
| **Terminal Background** | Deep Charcoal | `#1A1A1A` | Terminal-style log panel (`<pre>` block) background |
| **Terminal Text** | Soft White-Green** | `#D4F1C0` | Stdout text in log panel |
| **Terminal Error Text** | Soft Red | `#FF8080` | Stderr text in log panel |

---

## 3. Typography Rules

- **Font Family**: Ubuntu (Canonical's system font) — load via `@font-face` or Ubuntu Google Font
- **Headings**: Ubuntu Medium (500 weight) — stage names, section titles, navigation brand
- **Body / Labels**: Ubuntu Regular (400 weight) — form labels, descriptions, body copy
- **Monospace / Log**: Ubuntu Mono — terminal log panel (`<pre>` block), code-like values
- **Base size**: 16px
- **Heading scale**:
  - H1 (brand): 24px, Ubuntu Medium — NavigationBar title "charm.studio"
  - H2 (section): 20px, Ubuntu Medium — View titles ("Import Project", "Pipeline Progress")
  - H3 (component): 16px, Ubuntu Medium — Stage card names ("analyze", "pack", "deploy")
  - Body: 14px, Ubuntu Regular
  - Small / meta: 12px, Ubuntu Regular — timestamps, helper text

---

## 4. Component Stylings

### Navigation Bar
- Full-width sticky top bar, 64px height
- White (`#FFFFFF`) background with a 1px bottom border (`#CDCDCD`)
- Brand name "charm.studio" left-aligned in Ubuntu Medium, 18px
- Flat elevation — no shadow; the border provides separation

### Sidebar (History Panel)
- Fixed-width (280px), full viewport height, flush with the top nav
- Background: `#F7F7F7`; right border: 1px solid `#CDCDCD`
- **"New import" button**: Ghost/secondary style, full-width, Canonical Orange text, sharp corners
- **History items**: Clickable rows with subtle hover background (`#E5E5E5`), padding 12px 16px
  - Label (repo name): 14px Ubuntu Medium, `#111111`
  - Timestamp: 12px Ubuntu Regular, `#666666`
  - Status chip: pill-shaped (`border-radius: 12px`), 12px Ubuntu Regular, coloured by status (see palette)
- Active/selected history item: left accent border 3px Canonical Orange (`#E95420`)

### Buttons
- **Primary (submit, positive)**: Canonical Orange background (`#E95420`), white text, sharp corners (`border-radius: 2px`), no shadow. Hover: slightly darker orange (`#C34113`)
- **Negative (cancel pipeline)**: Red background (`#C7162B`), white text, sharp corners
- **Secondary / Ghost**: White background, 1px `#CDCDCD` border, `#111111` text, sharp corners
- **Disabled state**: 60% opacity, `cursor: not-allowed`
- **Loading state**: Inline spinner replaces button label, button disabled

### Form Inputs & Tabs
- **Tab strip (ImportView)**: Underline-style tabs (Vanilla `p-tabs`), active tab has a 2px Canonical Orange bottom border, label in Ubuntu Medium
- **Input fields**: White background, 1px `#CDCDCD` border, sharp corners, 40px height, 14px Ubuntu Regular
- **Validation error state**: Red border (`#C7162B`), inline error text below field in 12px red
- **Form layout**: Single-column, 16px spacing between fields, max-width 640px centred in main panel

### Stage Cards (PipelineView)
- White card with 1px `#CDCDCD` border, slight rounded corners (`border-radius: 4px`), 16px padding
- Whisper-soft elevation: `box-shadow: 0 1px 4px rgba(0,0,0,0.08)`
- **Failed state**: Red left border accent 4px (`#C7162B`) and overall border changes to red
- Stage name: H3 Ubuntu Medium
- Status chip: pill-shaped, colour-coded (see palette)
- Elapsed time: 12px Ubuntu Regular, `#666666`, right-aligned
- Log accordion: Vanilla-style collapsible with a chevron icon; collapsed by default

### Log Panel (Terminal)
- `<pre>` block inside each stage card accordion
- Background: `#1A1A1A` (deep charcoal), border-radius: 2px
- Font: Ubuntu Mono, 13px, line-height 1.6
- Stdout: `#D4F1C0`; Stderr: `#FF8080`
- Scrollable, max-height 240px, auto-scrolls to bottom while running

### Notifications & Banners
- **Result Banner (success)**: White card with a 4px left border in Success Green (`#0E8420`), ✅ icon, key-value pairs for Charm/Rock/Model/App paths
- **Error Banner**: White card with 4px left border in Error Red (`#C7162B`), error string in `#C7162B`
- **Caution (cancel)**: Vanilla `p-notification--caution` — amber left border (`#F99B11`), amber icon
- **Inline form error**: Vanilla `p-notification--negative` — compact, inside the form

---

## 5. Layout Principles

- **Application shell**: Two-column split (`l-application` + `l-aside` from Vanilla Framework)
  - Left: fixed 280px sidebar (history)
  - Right: fluid main content area
- **Main panel content**: Max-width 800px, horizontally centred within the main area, 32px vertical padding
- **Whitespace**: 24px standard gap between cards/sections; 16px internal component padding
- **Grid**: Vanilla's grid system for any responsive adjustments; desktop-first, no mobile breakpoints required initially
- **Visual hierarchy**: Flat → colour-coded chips → status borders. No decorative illustrations; all visual signals are functional.

---

## 6. Key Screen Inventory

| Screen | Key UI Elements |
|---|---|
| **ImportView** | Tab strip (Git / Bitbucket / URL), form fields, submit button with spinner, inline error notification |
| **PipelineView (running)** | Three stage cards (analyze/pack/deploy) with colour-coded chips, live elapsed timers, Cancel button (negative), log accordions |
| **PipelineView (done)** | Result Banner with artefact paths, stage cards all green, log accordions available |
| **PipelineView (failed)** | Error Banner, failed stage card with red border, other stages showing their final state |
| **PipelineView (cancelled)** | Caution notification, stage cards frozen at last known state |

---

💡 **Tip**: When calling `generate_screen_from_text`, include the palette tokens and atmosphere above. Reference "Canonical Vanilla Framework aesthetic — clean, professional, desktop split-panel layout with Ubuntu typography" to guide the generator.
