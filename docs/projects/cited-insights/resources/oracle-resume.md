# Five-Record Extraction Oracle — Resume Packet

Purpose: let a cold implementation agent resume the submission-critical
extraction experiment without rebuilding upstream data, guessing which run is
current, or broadening scope.

## Frozen inputs

- Day: `2026-07-11`
- Feed run:
  `adb2b4949de74a7a3120e71b62366acfcdca0656d0b49c07af10d4e5323f7f96`
- Published event run:
  `f8999fcd2b674bf46557023ec8dcab2ac4a8bc115fea8158b4b713a276b588a9`
- Triage run:
  `triage-v2.2-canonical-v8-2026-07-11-top1000`
- Triage DB:
  `data/derived/cited-insights/triage/triage-v2.2-canonical-v8-2026-07-11-top1000/triage.db`
- Event DB: `data/derived/signal-events/events.db`
- Artifact DB: `data/derived/artifacts/artifacts.db`

Do not select a newer-looking directory by filename. Verify the event
publication pointer before reading envelopes:

```bash
sqlite3 -header -column data/derived/signal-events/events.db \
  'SELECT * FROM signal_publication;'
```

## Oracle records

All five are human-labeled strong candidates and are `keep` in the frozen
triage run.

| Rank | Subject | Oracle post ID | Event ID | Representative post ID | Available strengthening |
| ---: | --- | --- | --- | --- | --- |
| 4 | Ethan Knight — Sol Ultra proof claim | `2075643450196971805` | `4eea8e96c4ba717b4ef2246b9ebaf3ef7849a00f484e95132a62210fa8e25e3a` | same as oracle post | No external artifact is linked. The authored X claim remains eligible primary evidence; an inspectable proof artifact would strengthen it. |
| 10 | Mira Murati — Thinking Machines worldview | `2075621073308311701` | `cb7a2c49717c7a53ab6a21f8706ee1c219ab3702b7686283a2c3a1f4ccf8e9ce` | `1945166365834535247` | Canonical article fetched successfully: `https://thinkingmachines.ai/blog/the-future-worth-building-is-human/`; clean-text SHA begins `09ce8ccb5159`. |
| 12 | Thibault Sottiaux — post-launch corrections | `2075641131002700120` | `dfaad8312be2f0be95c48a72dd46455ac8d701b64a33fd53092a266dd1c3fdb8` | same as oracle post | No external artifact is linked. The first-hand correction can support a claim about what the author reported; do not generalize beyond it. |
| 18 | Sebastian Raschka — price/performance comparison | `2075982283509571666` | `c0d7fe525b4cf4c4079a52e68734395dd56309341594d3a4691c4a1f1f7b868f` | same as oracle post | No external artifact is linked. The authored comparison can be cited as the author's observation; benchmark or harness evidence would strengthen broader performance claims. |
| 32 | Karan Singhal — GPT-5.6 health evaluation | `2075689779937833302` | `eb08b978f54de0e97583c258568326cab53045d269a8ee06ad06a4e07e094dec` | `2075686461693898868` | No external artifact is linked. First-party X can support what the author reports about the evaluation; preserve every methodology caveat in the supplied thread. |

The representative post can differ from the human-selected post because exact
event projection chooses one stable structural representative. Preserve the
oracle post as evidence; do not replace it silently with the representative.

## Inspect without network calls

Inspect the frozen triage inputs and decisions:

```bash
sqlite3 -header -column \
  data/derived/cited-insights/triage/triage-v2.2-canonical-v8-2026-07-11-top1000/triage.db \
  "SELECT current_rank, event_id, root_post_id, decision, reason
   FROM triage_item
   WHERE event_id IN (
     '4eea8e96c4ba717b4ef2246b9ebaf3ef7849a00f484e95132a62210fa8e25e3a',
     'cb7a2c49717c7a53ab6a21f8706ee1c219ab3702b7686283a2c3a1f4ccf8e9ce',
     'dfaad8312be2f0be95c48a72dd46455ac8d701b64a33fd53092a266dd1c3fdb8',
     'c0d7fe525b4cf4c4079a52e68734395dd56309341594d3a4691c4a1f1f7b868f',
     'eb08b978f54de0e97583c258568326cab53045d269a8ee06ad06a4e07e094dec'
   ) ORDER BY current_rank;"
```

Inspect artifact observations already associated with the five posts:

```bash
sqlite3 -header -column data/derived/artifacts/artifacts.db \
  "SELECT o.source_external_id AS post_id, a.artifact_kind, a.canonical_url
   FROM artifact_observation o
   JOIN artifact a ON a.artifact_id = o.artifact_id
   WHERE o.source_external_id IN (
     '2075643450196971805', '2075689779937833302',
     '2075621073308311701', '2075982283509571666',
     '2075641131002700120'
   ) ORDER BY post_id, canonical_url;"
```

Use `fli artifacts summary --no-input` and
`fli artifacts inspect-fetches --no-input` for operator-level inspection.
Do not rerun the broad importer or fetch queue merely to work on these five.

## Expected hand-written oracle

Before writing extraction framework code, create one expected record per row
under a new dated resource in this project. Each record must say:

1. either `insight` or `no_extractable_insight`;
2. one falsifiable claim when the supplied evidence supports it;
3. one exact supporting span from an authored first-party X post or an
   available external artifact;
4. why the claim matters;
5. separate investment and AI-engineering implications, clearly marked as
   analysis rather than source fact.

Authored first-party X is primary only for the author or organization's own
work, release, or observation. Related replies, quotes, and retweets remain
context unless their own authorship makes them primary for the claim being
made. Do not force five insights: `no_extractable_insight` is correct when the
accepted envelope still cannot support a safe concrete claim.

## Expansion gate

Do not run a day-wide extraction until:

- the five expected records have been manually reviewed;
- every insight's quoted span is found in one frozen X or artifact input;
- application code—not the model—binds the matching post/artifact ID and URL;
- the model output contains no runner-owned post, artifact, citation, source,
  day, or run IDs;
- rerunning the five inputs is idempotent and makes no duplicate model calls;
- LiteLLM tags, response usage, cached tokens, cost, and errors are persisted;
- the schema contains only fields used by the Insights surface, briefing, or
  evaluation.

After that proof, run 2026-07-11 and one blind day. Do not reopen Registry,
ranking, broad source ingestion, or semantic clustering unless an oracle miss
demonstrates a concrete dependency.
