---
target: current Ranking visualization
total_score: 22
p0_count: 0
p1_count: 3
timestamp: 2026-07-12T08-33-28Z
slug: frontend-src-pages-ranking-tsx
---
# Ranking visualization critique

Target: `frontend/src/pages/Ranking.tsx`

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---:|---|
| 1 | Visibility of system status | 2/4 | Initial loading resembles an empty result; follower loading and failure are silent. |
| 2 | Match system / real world | 2/4 | “Trust” overclaims what a following-overlap metric proves. |
| 3 | User control and freedom | 3/4 | Selection, close, Escape, and filters work; view state is not shareable. |
| 4 | Consistency and standards | 3/4 | Strong visual system; orbit and filter semantics depart from familiar controls. |
| 5 | Error prevention | 2/4 | Read-only risk is low, but semantic misinterpretation is not prevented. |
| 6 | Recognition rather than recall | 2/4 | Users must remember distance, size, shape, fill, selection, and arc encodings. |
| 7 | Flexibility and efficiency | 2/4 | Search and stepping help; sorting, URL state, and orbit keyboard access are absent. |
| 8 | Aesthetic and minimalist design | 3/4 | Restrained and distinctive, but 300 marks plus 300 rows create avoidable noise. |
| 9 | Error recovery | 1/4 | Generic main error, swallowed follower failures, and no retry. |
| 10 | Help and documentation | 2/4 | Good explanation and legend; cohort definition, date, caveat, and method link are missing. |
| **Total** | | **22/40** | **Acceptable — significant improvements needed** |

## Anti-patterns verdict

This does not look like generic AI-generated SaaS. It avoids gradients,
glass, metric cards, soft-shadow card grids, and decorative chrome. The flat
white/ink/capital-blue system, mono data typography, editorial rules, ranked
list, and linked orbit/detail composition feel authored.

The deterministic Impeccable detector returned zero findings. That clean scan
does not cover the product and accessibility problems below. No browser overlay
was available; visual evidence came from the supplied screenshot, current
source/CSS, and live HTTP/API checks.

## Overall impression

The concept is memorable and the visual craft is strong. The ranked column is
the precise analytical instrument; the orbit is a compelling overview of the
shape of consensus. The biggest opportunity is to make the page semantically
honest and decision-oriented: following overlap is attention, not necessarily
trust, and a fund analyst ultimately needs change, implication, evidence, and a
next action.

Overall: **6.5/10 as a production analyst instrument; roughly 8/10 as a visual
concept.**

## What is working

1. **Distinctive, coherent instrument aesthetic.** Restrained palette, flat
   surfaces, Inter/Plex pairing, and low-decoration density fit the product.
2. **Strong overview-to-detail linkage.** Orbit selection, synchronized list,
   follower arcs, detail view, Escape, and arrow stepping create a thoughtful
   exploratory loop.
3. **Honest metric separation inside the detail view.** Cohort follows/share
   and raw followers remain distinct; person/organization and
   Registry/discovered states use text and shape as well as color.

## Priority issues

### [P1] “Trust” overclaims the metric

Following measures observed attention/overlap, not endorsement. Rename the
primary language around what is actually measured—“Who does the frontier
cohort follow?” or “Attention overlap”—and expose cohort definition, readable
date, method, and the caveat that follows can include monitoring or criticism.
Suggested command: `$impeccable clarify`.

### [P1] The visualization is not a complete accessible interaction

SVG marks are mouse-only; the orbit is exposed as one image; search has no
programmatic label; filters use incomplete tab semantics; selected and follower
loading states are not announced. Make the list the explicit accessible
equivalent or give marks focusable button semantics. Use a labeled search,
pressed-button/radiogroup filters, selected-state attributes, live status, and
larger targets. Suggested command: `$impeccable audit`.

### [P1] The page does not yet finish the analyst’s job

It shows a static topology, not what changed or why it matters. Lead with new
entrants, biggest movers, unusual convergence, portfolio/thesis links, and an
evidence path. Keep the full orbit as the investigation surface rather than
the final decision. Suggested command: `$impeccable shape`.

### [P2] Too much visual decoding for the answer

Three hundred marks and rows arrive at once, while distance, size, shape,
fill, blue selection, and arcs all encode different facts. Default to 30–50,
label the few exceptional points, remove nonmatches rather than merely dimming
them, add the missing size explanation, and give the list real columns.
Suggested command: `$impeccable distill`.

### [P2] Loading, failure, and empty states are ambiguous

The initial request appears as zero results; follower loading/failure is silent;
the primary error discards detail and offers no retry. Add structural loading,
compact tracing status, specific inline errors, Retry, and clearer no-match
copy. Suggested command: `$impeccable harden`.

## Persona red flags

**Alex, power user:** no sorting or rank-change view; state cannot be bookmarked
or shared; the list lacks column headers; arrow stepping starts only after
selection and is disclosed late.

**Sam, accessibility-dependent:** 300 SVG marks are not focusable; search lacks
a label; filter semantics are incomplete; selection is not announced; 300 row
buttons create an inefficient tab sequence; the close target is likely too
small.

**Fund analyst:** the page answers who is broadly followed, not what changed or
what affects a position; it lacks readable provenance, thesis/ticker linkage,
and a concrete investigation outcome.

## Minor observations

- Internal algorithm and snapshot IDs read like plumbing rather than useful provenance.
- `completed_at` exists but is not shown.
- “Top 300” can contain a position beyond 300 because tied score ranks and deterministic positions differ.
- The full-universe count is hard-coded in empty copy and can drift.
- The inset blue selected-row stripe is slightly inconsistent with the otherwise flat hairline language.

## Questions to consider

- If the orbit disappeared, what analyst decision would become impossible?
- Is “trust” defensible, or is “attention overlap” the credible claim?
- What are the three ranking changes a portfolio manager should know today?
- Should discovered accounts end in an “investigate why this moved” workflow?
