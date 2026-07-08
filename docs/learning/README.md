# Learning Log — do first, then understand

This folder is the builder's learning surface for this project. Adi comes from
systems/production engineering, not data science. The case study deliberately
exercises data-science territory (scoring models, validation, ground truth,
signal-vs-noise). The contract here is **do → learn**, never learn → do:
concepts get captured when they are actually used in the code, not studied in
advance.

## Contract for agents working in this repo

Whenever the work uses a data-science or ML technique that is not obvious from
a systems-engineering background, add or extend an entry in this folder **in
the same change**. Trigger examples: choosing a scoring model, validation
strategy, inter-rater agreement, precision/recall trade-offs, calibration,
ranking metrics, baseline comparisons, train/test splits, ground-truth
construction.

Entry format — one file per concept, `NN-concept-name.md`, numbered in the
order they entered the project:

```markdown
# <Concept name>

**Where we used it:** <file/module + one line on the decision it drove>

**The problem it solves here:** <2-4 plain sentences, no jargon>

**How it works:** <short explanation in plain words; a small worked example
with our real data beats formulas>

**Why we chose it over alternatives:** <1-3 sentences>

**If asked about this at the on-site:** <the 30-second verbal answer>
```

Rules:

- Plain simple words. Assume a smart engineer who has never done DS.
- Tie every entry to the actual decision in this repo, not textbook generality.
- A tiny visualization (matplotlib PNG committed next to the entry, or an
  ASCII sketch) is welcome when it genuinely helps; never mandatory.
- Keep entries short. If an entry exceeds ~60 lines, it is trying to be a
  textbook; cut it.
- These entries feed two deliverables directly: the final report's "what you
  learned" section and the on-site discussion, where design choices and their
  justification will be probed.

## Index

(populated as entries are added)

| # | Concept | Used in |
| --- | --- | --- |
| 01 | Graph-derived discovery | `src/fli/digg.py` |
