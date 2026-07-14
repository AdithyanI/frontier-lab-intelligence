# Design

Seeded 2026-07-08 pre-implementation; rewritten same day after the v2 UI
shipped. Register: **product** (see PRODUCT.md). Source of truth for tokens:
`frontend/src/tokens.css`.

## Mood

Editorial instrument. A fund's annual report crossed with a live terminal:
bold typographic hierarchy, big tabular numerals, capital-blue as the one
working accent on paper-white ground. The interface states its numbers with
confidence and otherwise stays out of the way — the drama belongs to the
intelligence, never the chrome.

## Theme

Light. Scene: an analyst scans the digest at a desk in office daylight,
between meetings, deciding in seconds what deserves a click. Dense text on
paper-bright ground reads fastest in that light; dark mode would be styling
for the engineers building it, not the users reading it.

## Color

Strategy: **restrained** — neutrals + the BIT capital-blue family, accent
≤10% of any surface. The product's value is noise suppression; the palette
practices it.

Anchored to BIT's own brand (extracted from bitcap.com's Webflow tokens
2026-07-08): alpha-black `#151515` as ink, capital-blue `#5bc5f2` /
`#4391b4` / `#235165` as the accent family. Their coin-sand appears only at
whisper strength (`#f4f1ea`) as a row-hover / band tint — we do not copy
their sand marketing surfaces (wrong register for a tool) or Akkurat LL
(licensed; Inter is the working grotesque).

```css
:root {
  /* ground */
  --bg:            #ffffff;   /* pure white, no hidden warmth */
  --surface:       #f7f7f6;   /* raised panels, pills, captions */
  --sand:          #f4f1ea;   /* BIT coin-sand at whisper strength — hovers, bands */
  --border:        #e4e4e2;   /* hairlines */
  --border-strong: #151515;   /* structural rules — the editorial line */

  /* text */
  --ink:       #151515;   /* BIT alpha-black */
  --ink-soft:  #434343;
  --muted:     #6b6b68;

  /* brand — BIT capital-blue family */
  --blue:      #5bc5f2;   /* fills, marks, large accents (not for text) */
  --blue-mid:  #4391b4;   /* lines, secondary accents */
  --blue-ink:  #235165;   /* link text, kickers — AA-safe on white */

  /* semantics (data, not decoration) */
  --positive:  #2e7d4f;
  --negative:  #a13333;
}
```

Rules:

- `--blue` is a shape color (node fills, brand mark, funnel stage), never
  body-text color; text-on-white blue is always `--blue-ink`.
- Structural rules use `--border-strong` (ink) — full-bleed 1px lines that
  divide the page like an editorial layout. Soft hairlines use `--border`.
- Score/severity is never color-only — always paired with a number or label.
- White text on ink and blue-ink fills. Dark text on white/sand/blue-500.

## Typography

- **UI + prose:** Inter (system-ui fallback). Weights 400/500/600 only.
- **Data + provenance:** IBM Plex Mono for numbers, timestamps, source IDs,
  table headers, and compact method metadata.
- Display: clamp(34–56px), weight 600, letter-spacing −0.025em, for the one
  statement a page gets to make. Big stats in mono at 26–40px.
- Body 15–16px, line-height 1.55, max measure ~60ch.
- Page headers begin with one direct title and one short, useful subtitle. Do
  not add a route-restating kicker or repeat counts already present in nearby
  controls. Operational identifiers and formulas belong in a compact Method
  disclosure or the canonical Architecture explanation.
- Tabular numerals everywhere numbers column-align.

## Layout

- App shell: 64px top bar (brand mark + pill nav), full-bleed ink rule
  beneath. No sidebar — pages own their full width. Show only working routes;
  unavailable future destinations do not occupy the navigation.
- Home is an editorial split: statement + hero numerals on the left, live
  pipeline rail on the right, divided by an ink rule.
- Density first: tables and lists over cards. Cards only where an item is
  genuinely a self-contained unit (a report), never for lists of insights.
- Diagrams are hand-built inline SVG in brand colors with mono captions —
  never rendered-markdown or generic diagram-tool output.
- Spacing scale: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 72.
- Architecture sections use descriptive headings, not decorative sequence
  numbers. Numbers remain only where order itself carries meaning.
- Provenance line (source, date, entity) sits directly under every insight
  title in mono — first-class, not a footnote.
- **Desktop-first (2026-07-09):** the primary target is the desktop view
  (analyst at a desk). Design and polish desktop; mobile/responsive polish is
  deferred until Adi asks — don't spend effort making SVG diagrams reflow for
  small screens yet.

## Components (current + anticipated)

- **Pipeline rail:** stage node (blue = live, outlined = in progress), name,
  mono state, one-line summary, live mono counts.
- **Entity registry table:** mono uppercase headers, sand row hover, pill
  search + All/People/Organizations/Unsure/Rejected segmented filter with live
  counts, load-more; rejected rows expose their reason in the table, while
  active rows show identity + truthful kind and open a detail card.
  All, People, and Organizations are reach-ranked views: People shows X
  followers, Organizations shows combined X followers, and All retains Type
  alongside combined X followers. Each defaults to descending by the visible
  total; the follower header is a full-width, keyboard-accessible control that
  toggles ascending/descending order. These views hide channel handles to keep
  rows calm; every channel remains searchable
  and available in the detail card. Missing follower observations display as
  an em dash and sort last. Rejected remains a reason-bearing review view.
  Internal source seeds such as the curated `labs` table do not create public
  kinds, badges, or filters.
- **Entity detail card:** native `<dialog>` opened on row click — type pill,
  name, observed bio, and a flat platform matrix that groups every channel by
  X, website, GitHub, or blog. Multiple X accounts are equal links on
  one row; there is no privileged footer CTA. Preserve bio line breaks; label
  source-truncated snapshots honestly; bound long content with internal
  scrolling while keeping close access fixed. Daily-score/ranking evidence stays
  out of this identity surface.
- **Diagram canvas:** ink-ruled frame, inline SVG, mono caption bar on
  surface ground.
- **Evidence Feed:** default to the decision-ready `Kept` / `Score` view.
  Date navigation shows the newest seven available complete UTC days in one
  ruled row; explicit older/newer controls page through non-overlapping
  seven-date windows while keeping the selected column where possible. At
  narrower desktop widths, date labels compact without wrapping while counts
  remain visible; the same seven-cell structure appears as a quiet skeleton
  during the initial date request so the page does not jump from an empty rail.
  The persistent left rail shows the event's stable daily score rank across all
  evidence for the selected day (`#1`, `#2`, ...), never the composite decimal.
  Audit filters and search hide rows without restarting that rank. Clicking it opens one
  anchored, non-modal disclosure with the daily score, its exact score-producing
  member post, raw component values, within-day percentiles, weights, and
  limitations. Rank is scope-aware: a future weekly view labels a weekly rank;
  it must not average incomparable daily scores.
  Audit and sort are compact labeled disclosures rather than persistent
  segmented bars; each option remains one click away and audit counts stay
  visible inside the menu. Search shares their 44px square hairline treatment
  but remains a separate left-aligned input; the paired Audit/Sort controls
  anchor the right edge. They stack only on narrow screens. Per-envelope triage rationale is collapsed by
  default behind a quiet `View reason` disclosure so evidence remains the
  primary reading surface.
- **Artifact index:** a flat, ruled list over the canonical artifact catalog.
  Within the selected source day, order by the best originating Feed rank; if
  several accepted envelopes reveal the same artifact, the smallest rank wins.
  This is inherited provenance, not a second artifact score. Keep the default
  row to Feed rank, artifact title and host, fetch-oriented type, source, and a
  compact source time. When one Feed envelope reveals several canonical
  artifacts, keep them as separate expandable rows but show their shared rank
  once in one continuous left rail. Equal ranks from different envelopes do
  not visually merge. Native `<details>` expansion reveals
  the canonical URL, a link back to the exact ranked Feed envelope that
  disclosed it, retrieval state, and snapshot provenance. The Feed envelope
  remains the evidence workspace and owns the onward X link; Artifacts does
  not duplicate that context. A single
  Feed-style date navigator filters by the UTC day of the source post that
  revealed the artifact, never by retrieval time; this is an inspection aid,
  not an independent artifact relevance model. Do not add summaries, cards,
  or additional filters until a cited-insight consumer proves the need.
- **Insight row (anticipated):** title, why-flagged rationale, score (mono),
  provenance line, persona tag; expandable.
- **Score breakdown:** inputs and weights are visible only on demand from the
  Feed rank. Trust through inspectability without making the decimal the primary
  reading cue (PRODUCT.md #3).

## Motion

Near-none. State transitions (hover, expand) at 150ms ease-out. No entrance
animations, no staggered reveals — analysts open this dozens of times a day.
`prefers-reduced-motion`: transitions become instant.

## Anti-checklist (from PRODUCT.md anti-references)

- No gradient anything. No glassmorphism. No metric-card grids.
- No identical card grids. No side-stripe accents on list items.
- No decorative charts — every chart answers a question a user actually has.
- No rendered-markdown pages posing as product UI.
