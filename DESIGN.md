# Design

Seeded 2026-07-08, pre-implementation. Re-run `$impeccable document` once the
web UI exists to capture real tokens. Register: **product** (see PRODUCT.md).

## Mood

Research terminal at a Berlin fund. Quiet precision: deep harbor-blue
instruments on clean paper, one brass signal-light for the things that matter.
The interface is an instrument, not a brochure — the drama belongs to the
intelligence, never the chrome.

## Theme

Light. Scene: an analyst scans the digest at a desk in office daylight,
between meetings, deciding in seconds what deserves a click. Dense text on
paper-bright ground reads fastest in that light; dark mode would be styling
for the engineers building it, not the users reading it.

## Color

Strategy: **restrained** — neutrals + one primary, accent ≤10% of any surface.
The product's value is noise suppression; the palette practices it.

```css
:root {
  /* ground */
  --bg:      oklch(1.000 0.000 0);      /* pure white, no hidden warmth */
  --surface: oklch(0.972 0.004 230);    /* raised panels, table stripes */
  --border:  oklch(0.900 0.008 230);    /* hairlines */

  /* text */
  --ink:     oklch(0.220 0.020 230);    /* body — ≥7:1 on bg */
  --muted:   oklch(0.500 0.018 230);    /* secondary — ≥4.5:1 on bg */

  /* brand */
  --primary: oklch(0.450 0.086 230);    /* deep cobalt — nav, links, actions; white text on fills */
  --accent:  oklch(0.640 0.130 75);     /* brass — alerts, high-signal flags only; white text on fills */

  /* semantics (data, not decoration) */
  --signal-high: var(--accent);
  --positive:    oklch(0.560 0.100 155);
  --negative:    oklch(0.520 0.140 25);
}
```

Rules:

- The accent is earned: it marks genuinely high-signal items (alert-worthy
  insights, threshold-crossing scores). If brass appears more than a few
  times per screen, the filtering failed before the UI did.
- Score/severity is never color-only — always paired with a number or label.
- White text on primary and accent fills. Dark text only on pale/neutral fills.

## Typography

- **UI + prose:** Inter (system-ui fallback). Weights 400/500/600 only.
- **Data + provenance:** a mono for scores, timestamps, tickers, source IDs —
  IBM Plex Mono or JetBrains Mono, one of them, never both.
- Body 15–16px, line-height 1.55, max measure 70ch.
- Headings: same family, weight 600, tight scale (1.25 ratio); this is a
  tool, not editorial. `text-wrap: balance` on headings.
- Tabular numerals (`font-variant-numeric: tabular-nums`) everywhere numbers
  column-align: score tables, token counts, dates.

## Layout

- App shell: slim left nav (register / insights / reports / settings),
  content column max ~1100px. No dashboard hero, no metric cards.
- Density first: tables and lists over cards. Cards only where an item is
  genuinely a self-contained unit (a report), never for lists of insights.
- Spacing scale: 4 / 8 / 12 / 16 / 24 / 32 / 48. Section rhythm from spacing,
  not dividers-everywhere.
- Provenance line (source, date, entity) sits directly under every insight
  title in mono — first-class, not a footnote.

## Components (anticipated)

- **Insight row:** title, one-line why-flagged rationale, score (mono), provenance
  line, persona tag. Expandable for full extraction detail.
- **Entity page:** lab or person; identity-resolution facts, tracked channels,
  recent scored contributions.
- **Score breakdown:** always inspectable — inputs and weights visible on
  demand next to any score. Trust through inspectability (PRODUCT.md #3).
- **Report view:** rendered digest, print/PDF-clean stylesheet.
- **Alert config:** thresholds per persona/channel.

## Motion

Near-none. State transitions (expand row, panel open) at 150–200ms ease-out.
No entrance animations, no staggered reveals — analysts open this dozens of
times a day. `prefers-reduced-motion`: transitions become instant.

## Anti-checklist (from PRODUCT.md anti-references)

- No gradient anything. No glassmorphism. No hero metrics.
- No identical card grids. No side-stripe accents on list items.
- No decorative charts — every chart answers a question a user actually has.
