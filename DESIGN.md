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
  controls. Operational identifiers and ranking rules belong in a compact Method
  disclosure or the canonical Architecture explanation.
- Tabular numerals everywhere numbers column-align.

## Layout

- App shell: 64px top bar (brand mark + pill nav), full-bleed ink rule
  beneath. No sidebar — pages own their full width. Show only working routes;
  unavailable future destinations do not occupy the navigation. The six
  top-level destinations are Insights, Evidence, Network, How it works, BIT
  Lens, and System. Insights is the first navigation item and the default
  landing route because the audience-ready brief is the clearest statement of
  product value. How it works is the reviewer walkthrough that connects the
  assignment to the live product.
  BIT Lens holds the public client context used to translate frontier evidence
  into fund-specific research questions. Its ruled secondary navigation keeps
  the auditable **Company universe** used by the Investment pass separate from
  the long-form **Research brief**. Company universe is the first and default
  view. Both remain separate from generated daily Insights. System groups two
  technical views: **Architecture** is the
  current implementation map, and **Status** is the live published checkpoint.
- Registry and Ranking share one top-level **Network** destination because they
  are two views of the same source system. Ranking is the first and default
  subview because it is the clearest demonstration of network discovery;
  Registry follows as the screened identity audit view. A third **Add Profile**
  subview owns manual admission as an operator action. Use one ruled secondary
  navigation for all three, not another row of top-level pills.
- Feed and Artifacts share one top-level **Evidence** destination
  because they are two inspection views over the same evidence layer. Feed is
  the first and default subview: the `/evidence/feed` product view owns daily
  Development-rank disclosure and exact Event provenance, while the lower-level
  raw Feed ledger remains unranked. Artifacts follows as the canonical source
  and retrieval-provenance index derived from selected Feed evidence. Keep the two
  object types in separate ruled views; do not blend events and artifacts into
  one list.
- Home is an editorial split: statement + hero numerals on the left, live
  pipeline rail on the right, divided by an ink rule.
- Density first: tables and lists over cards. Cards only where an item is
  genuinely a self-contained unit (a report), never for lists of insights.
- Diagrams are hand-built inline SVG in brand colors with mono captions —
  never rendered-markdown or generic diagram-tool output.
- Spacing scale: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 72.
- Architecture sections use descriptive headings, not decorative sequence
  numbers. Numbers remain only where order itself carries meaning. Separate
  chapters with one full-width ink hairline centered in the vertical rhythm;
  do not add a trailing rule after the final chapter.
- Secondary navigation uses one full-width ruled strip across workspaces and
  Architecture. Routed views use the ink-filled active cell; in-page chapter
  anchors remain neutral because they do not replace the current view.
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
  All, People, and Organizations default to the stable Registry-wide **Network
  support** order. Each metric cell shows only the entity's stable ordinal among
  active Registry entities (`#24`) so the table remains scannable. Hovering a
  metric reveals its compact underlying count in place; opening the entity
  profile shows the exact count and rank together. Search, kind filters, and
  pagination only hide rows; they never recompute this rank. The separate
  sortable **Network support** column follows the same rank-first disclosure.
  Support is
  the union of distinct active Registry entities following any represented X
  account owned by the target entity; self-support is excluded. The global
  account tiebreak position appears only in Ranking as candidate discovery.
  Neither ordinal is a new score, and the scopes remain explicit.
  Both numeric headers are full-width, keyboard-accessible sort controls. These views hide channel handles to keep
  rows calm; every channel remains searchable
  and available in the detail card. Missing follower observations display as
  an em dash and sort last. Rejected remains a reason-bearing review view.
  Internal source seeds such as the curated `labs` table do not create public
  kinds, badges, or filters.
- **Registry profile intake:** `Add Profile` is an explicit Network subview next
  to Ranking and Registry. It presents one full-width operator form with a
  single X URL field and two plain admission paths:
  `Screen normally` and `Add directly`. Direct admission reveals one required
  reason field. Keep the collection limitation visible, make long-running
  evaluation state explicit, and return the existing/active/rejected reason in
  place. Do not introduce a feature-specific password control; whole-site
  access owns authentication when enabled.
- **Entity detail card:** native `<dialog>` opened on row click — type pill,
  name, observed bio, and a flat platform matrix that groups every channel by
  X, website, GitHub, or blog. Multiple X accounts are equal links on
  one row; there is no privileged footer CTA. Preserve bio line breaks; label
  source-truncated snapshots honestly; bound long content with internal
  scrolling while keeping close access fixed. Daily-ranking evidence stays
  out of this identity surface.
- **Diagram canvas:** ink-ruled frame, inline SVG, mono caption bar on
  surface ground.
- **Evidence Feed:** default to the grouping-first `All` / `Rank` view.
  `Relevant` is a derived display state—Engineering, Investment, or both—not
  a separate model judgment. It stays available for later routing inspection
  but never triggers downstream work.
  Date navigation shows the newest seven available complete UTC days in one
  ruled row; explicit older/newer controls page through non-overlapping
  seven-date windows while keeping the selected column where possible. At
  narrower desktop widths, date labels compact without wrapping while counts
  remain visible; the same seven-cell structure appears as a quiet skeleton
  during the initial date request so the page does not jump from an empty rail.
  The selected UTC audit day is URL-backed and shared across Feed, Primary
  artifacts, and Insights. Switching between those views preserves the day;
  when a target view has no data for it, keep the date and show an honest empty
  state rather than silently selecting a different day.
  The persistent left rail shows the Development's stable daily rank across all
  evidence for the selected day (`#1`, `#2`, ...). Status filters and search
  hide rows without restarting that rank. Clicking it opens one anchored,
  non-modal disclosure with the union of distinct trusted Registry participants
  across every source Event, mean participant network position, maximum
  one-source-post public interactions, the deciding layer, and limitations.
  Original authors, quote authors, and reposters count once per Development.
  These are ordered tiebreak layers, not a composite decimal or weighted score. Rank is
  scope-aware: a future weekly view labels a weekly rank; it must not average
  ranks from different daily candidate sets.
  Status and sort are compact labeled disclosures rather than persistent
  segmented bars; each option remains one click away and routing counts stay
  visible inside the menu. Status begins with `All`, which removes the routing
  filter without inventing another evaluation state, followed by Relevant,
  Not relevant, and Not evaluated. Search shares their 44px square hairline treatment
  but remains a separate left-aligned input; the Status/Sort controls
  anchor the right edge. They stack only on narrow screens. Each Development
  row names its display post, reports the number of source posts and
  amplifiers, and keeps every exact source post under one disclosure. Use
  one `Posts about this Development` section heading and mark only the representative row
  `Shown in Feed`; do not repeat a category label on every row or call the
  count “independent sources,” because it counts posts rather than people.
  Inside that evidence disclosure, one subordinate
  `Preview what audience analysis reads` control assembles the exact
  deterministic routing input on demand without calling a model. Its compact
  ledger separates source posts, same-author updates, and retrieved artifacts
  sent for meaning from trusted reaction activity used only for rank. The
  complete rendered input remains one deeper, default-collapsed audit view.
  Per-Development routing rationale is collapsed by
  default behind a quiet `View reasons` disclosure so evidence remains the
  primary reading surface. A routed Development shows neutral hairline `ENG`
  and/or `INV` marks, or the quiet `Neither audience`
  state when both judgments are negative. The disclosure presents only the
  two audience-specific decisions and reasons. Unrouted or stale Developments
  show no routing status.
- **Artifact index:** a flat, ruled list over the canonical artifact catalog.
  Within the selected source day, order by the inherited Development rank.
  This is inherited provenance, not a second artifact score. Keep the default
  row to Feed rank, artifact title and host, fetch-oriented type, and source.
  Keep content status and the exact source timestamp inside the expansion so
  the scan surface stays crisp. When one Development reveals several canonical
  artifacts, keep them as separate expandable rows but show their shared rank
  once in one continuous left rail. Equal ranks from different Developments do
  not visually merge. Native `<details>` expansion reveals
  the canonical URL, a link back to the exact source Event inside the ranked
  Development that disclosed it, content status, and snapshot provenance. The status is
  one of text ready, not extracted, not supported yet, extracting, retry needed,
  or unavailable; expanded provenance explains that state in plain language
  rather than exposing an internal error code. The Feed Development
  remains the evidence workspace, while the exact Event owns the onward X link; Artifacts does
  not duplicate that context. A single
  Feed-style date navigator filters by the UTC day of the source post that
  revealed the artifact, never by retrieval time; this is an inspection aid,
  not an independent artifact relevance model. Ready rows expose the exact
  normalized text snapshot behind a second, default-collapsed Preview control
  inside the existing provenance expansion,
  with its format, character count, and one link to the complete text response;
  catalogued-only rows do not imply that content was retrieved. Do not add
  summaries, cards, or additional filters until a cited-insight consumer proves
  the need.
- **Audience Insights:** one URL-backed company-aware Investment reader.
  Investment is the only current Insight generator. The AI Engineering tab
  remains visible because routing exists for that audience, but it shows an
  explicit unavailable state instead of legacy content. Each date reads one
  complete published cohort from the backend. `Kept`, `Suppressed`, and `All`
  are views over that same current store; the SPA never combines old and new
  schemas.

  Each Development keeps its application-owned Feed rank and leads with the
  agent-written investment headline, `What changed`, and `Portfolio
  read-through`. Company read-throughs are collapsed by default. Their summary
  exposes the company, ticker, direction, and concise impact. Expansion reveals
  the causal mechanism, affected business driver, size basis, what remains
  unproven, and what to check next. `How the agent got here` separately shows
  the company screening and memo-opening decisions. It is audit detail, not
  permanent reading chrome.

  Sources are deterministic application links, not model-authored URLs. The
  source disclosure links to the exact Feed Development, original post, each
  available artifact, and company memo. It also exposes a quiet `Copy ID`
  control for precise review. Honest zero/thin cohorts remain available and are
  never padded.

  A 44px hairline `Download PDF` action sits at the top-right of the page header
  and follows the selected date and audience. It is enabled only for a complete
  published Investment cohort and exposes preparing, downloaded, and
  actionable error states without shifting the header. A quieter 44px `Send
  brief` action sits directly beside it. It opens one anchored flat panel with
  Slack and email choices, masked destination, audience/date/content-scope
  summary, and an explicit final confirmation. Slack sends every cited Insight
  plus the PDF link. Email sends up to five Insights plus the PDF attachment.
  Provider secrets and delivery metadata never enter the reading surface.

  The exported A4 workbook uses the same paper-white, ink, capital-blue,
  flat-rule language. Its opening combines the report title, audience/date, and
  a ranked list of clickable Insight titles. Each title jumps to one
  decision-analysis page followed by a deterministic source ledger. PDF text
  remains vector and selectable, with an embedded mixed-script fallback for
  citation titles outside WinAnsi.
- **BIT Lens:** two ruled views of one public client-context workspace. The
  **Research brief** remains a text-first public-research briefing without
  diagrams, dashboards, or collapsed holding detail. It preserves the full
  outside-in research in a linear reading order: flagship mandate and terms;
  dated portfolio disclosures and the latest complete audited holdings; the
  current top ten with explicit BIT-thesis, BIT-commentary, and analyst-inference
  grades; BIT's public Thesis → Edge → Signal → Key Move grammar; Volume × Price
  × Mix × Margin company analysis; alternative data, Aion, human investment
  judgment, and Devil's Advocate review; the resulting Investment-insight
  standard; contradictions, unknowns, and a source ledger. The **Company
  universe** is a searchable, filterable, expandable ledger derived from the
  canonical Investment context packet. It keeps all 37 sourced profiles in one
  candidate universe because relevance is decided for each Event, not by a
  permanent company label. Each expanded row
  leads with one compact **Context used by the agent** block: the business
  model, operating drivers, and known AI exposures that cold-start Event
  analysis. These exposures are starting hypotheses, not a closed taxonomy or
  relevance score. Detailed opportunity, risk, and
  watchpoint research remains available through one subordinate disclosure,
  while source-graded BIT views, research limits, company sources, and
  disclosure history stay visibly separate. The UI never shows or ranks by an
  AI-pathway count. The view opens directly on one compact disclosure note and
  the working controls; it does not repeat the BIT Lens title with a second
  landing header or a statistics band. Its three-control row remains Search
  context, Disclosure, and Sort, with the two menus using the
  same editorial menu grammar as Evidence. Each collapsed company row
  shows exactly one dated reference weight: the 30 June 2026 current top-ten
  weight when available, otherwise the 31 December 2025 audited weight marked
  `Last confirmed`. Expanded Disclosure history keeps both dated public values
  when both exist; the canonical API likewise preserves the reference date,
  basis, and current-confirmation state alongside both disclosure records.
  The candidate universe is prior retrieval context, never proof that a
  specific Event affects a company.
  Use ordinary prose,
  descriptive headings, lists, and flat tables only where rows make exact dates
  or weights easier to compare. Keep body copy at 16px with a 72ch maximum and
  all claims dated or qualified. Never imply access to the complete current
  portfolio, internal forecasts, cost bases, position targets, or automated
  trade decisions.
- **Rank explanation:** the ordered evidence layers and deciding layer are
  visible only on demand from the Feed rank. Trust comes from inspectability
  without inventing a synthetic number (PRODUCT.md #3).
- **System guide:** the default System view maps the original assignment to one
  five-step path through the working product: choose, collect, rank, judge, and
  publish. Each step links to its real proof surface. End with the exact audit
  path and a clear split between implemented behavior and future work; do not
  turn the page into a second dashboard or repeat volatile counts.
- **System status:** a read-only, API-derived checkpoint view. Lead with data
  currency, observation time, and the operator-run refresh model, then use one
  ruled table for Registry, collection, Feed/Events, artifacts, routing, and
  Insights. Separate "data through" from "last update" and never claim host,
  database, or scheduler health that the current product APIs do not prove.

## Motion

Near-none. State transitions (hover, expand) at 150ms ease-out. No entrance
animations, no staggered reveals — analysts open this dozens of times a day.
`prefers-reduced-motion`: transitions become instant.

## Anti-checklist (from PRODUCT.md anti-references)

- No gradient anything. No glassmorphism. No metric-card grids.
- No identical card grids. No side-stripe accents on list items.
- No decorative charts — every chart answers a question a user actually has.
- No rendered-markdown pages posing as product UI.
