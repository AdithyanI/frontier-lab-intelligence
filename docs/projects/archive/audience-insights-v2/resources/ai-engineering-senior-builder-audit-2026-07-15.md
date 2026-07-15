# AI Engineering senior-builder publication audit

Status: complete read-only product audit of the provisional corrected-history
chain for 2026-07-05 through 2026-07-13. No run, audit, or finalization store
was modified.

## Boundary and method

This audit applies a stricter question than schema or publication-audit
validity:

> Would a senior AI builder be glad this item interrupted their day because it
> changes a concrete experiment, implementation choice, benchmark, or
> reliability decision?

Every judgment below was checked against the frozen `candidate_item.packet_json`
source text in the named production database, not only the extracted claim or
the independent model audit. The reviewed chain uses the corrected-history AI
Engineering runs, including Jul 10 provider-safe r4. Jul 10 r2/r3 are not
eligible because their empty provider-fallback attempts have unknown (`NULL`)
proxy cost.

The chain remains operationally provisional: Jul 10 r4 adds
`candidate-69f29c9ddd4d63a9bc22`, while the current Jul 11-13 stores were built
without that exact predecessor in history. This report judges immutable item
quality; it does not certify chronological reconciliation.

The 16 base selections reduce to 12 after the already established adjacent
audit/finalization projections remove:

- Jul 8 `candidate-ee8addf937532bec7259` (unsupported claim that Robostral is
  open);
- Jul 9 `candidate-b1cbe3519ce14bb73dd0` (unsupported AI-safety implication);
- Jul 11 `candidate-c4b54c73387df0cb03c4` (MuScriptor action has no comparison
  baseline or pass/fail criterion); and
- Jul 12 `candidate-2b2606e90b036fd11398` (Codex Ultra reproduction has no
  measurable baseline or success/failure boundary).

The Jul 11 provider-safe r3 adjacent audit is therefore not currently passing.
MuScriptor must remain unpublished unless a new immutable item and corrected
suffix clear the exact audit boundary; this is an audit blocker, not an
editorial-veto candidate.

## Item-by-item judgment

### 2026-07-05 — `candidate-13f22bd2ecc72b96b4ef` — KEEP

- **Event:** `c38a91c6962485ff3ddd3bc229385afd8906096b441aa4f988d9f5098e98e9eb`
- **Claim:** `@yishan reproduced the evaluation framework's tests on GPT-5.5
  Pro using public medical datasets, finding quantitative improvement (79/100
  vs 69/100) but insufficient reliability for medical use under the paper's
  robustness criteria.`
- **Exact quote / source:** “The results are: the most capable models today
  (GPT-5.5 Pro) did outperform the best models from before (79/100 vs 69/100),
  but did not improve enough to be considered sufficient for reliable medical
  use.” — [@yishan](https://x.com/yishan/status/2070742742133780960)
- **Recommended action:** Use the open evaluation framework to rerun the
  radiology-image interpretation tests on current frontier models and compare
  pass/fail scores with this baseline.
- **Validation boundary:** Public datasets only; the reproduction excluded
  copyrighted JAMA/NEJM data and did not reproduce the qualitative robustness
  tests.
- **Senior judgment:** Genuinely useful. It combines an accessible evaluation
  artifact, a quantitative baseline, and an unusually honest negative result.
  Attribution is explicit and the raw post supports every material claim. No
  same-day or prior-history duplicate was found.

### 2026-07-06 — `candidate-cd16a217a33d0bcb478f` — KEEP

- **Event:** `f95364f6ae9a7537c8baa23137fd3de8325c931ed4b04aa5d1c82bfe21336474`
- **Claim:** `LMSYS reports that DSpark in SGLang achieves the best
  throughput/latency tradeoff on DeepSeek-V4-Flash across batch sizes 1 to 256
  and provides up to ~20% higher throughput under high concurrency compared to
  fixed budget verification.`
- **Exact quote / source:** “Across batch sizes 1 to 256, DSpark gives the best
  throughput/latency tradeoff on DeepSeek-V4-Flash, ahead of both MTP and
  non-spec. At high concurrency, dynamic scheduling provides up to ~20% higher
  throughput compared to a fixed budget, while maintaining high verification
  quality across workloads.” — [LMSYS](https://x.com/lmsysorg/status/2074176669108367549)
- **Recommended action:** Benchmark DSpark against MTP and non-speculative
  decoding on DeepSeek-V4-Flash at batch sizes 1-256, measuring latency,
  throughput, and verification quality under concurrency.
- **Validation boundary:** SGLang implementation, DeepSeek-V4-Flash, and the
  provider's hardware/configuration; replication must match those conditions.
- **Senior judgment:** Strong implementation signal. It names a serving method,
  comparators, workload, scale range, and performance target. Treat the numbers
  as LMSYS's first-party report until reproduced. It is not duplicated elsewhere
  in the chain.

### 2026-07-06 — `candidate-1c875ca125d1599c5203` — KEEP

- **Event:** `288ef528f1c6d3c695474d800f5f7621befe6b43ff8b2c74d4fe81b941a30c52`
- **Claim:** `fal reported that its Ideogram V4 Fast and Instant variants
  generate full images in 0.4 seconds (Instant) and one second (Fast) using the
  same prompts and parameters as the original, achieving up to 8x the speed.`
- **Exact quote / source:** “Ideogram V4 Fast and Instant are now available on
  fal ... Full images in 0.4 seconds on Instant and one second on Fast ... Same
  prompts and parameters as the original at up to 8x the speed” —
  [fal](https://x.com/fal/status/2074178998519665081)
- **Recommended action:** Run both variants on fal using the same prompts and
  parameters as the original and measure full-image latency.
- **Validation boundary:** fal's platform and undisclosed hardware; the original
  prompt/parameter set is referenced but not fully included in the post.
- **Senior judgment:** Useful as a bounded vendor-validation task for a
  latency-sensitive image pipeline, not as independent performance truth. The
  missing public test fixture weakens reproducibility but does not make the
  experiment meaningless. No duplicate was found.

### 2026-07-07 — `candidate-755f155e42c0112b5392` — KEEP

- **Event:** `41b70b7ee3cc8e3eb7be66e375da0f504db76b962a149dde74bf0e2a5d5fcbb0`
- **Claim:** `Anthropic documented that the Jacobian lens (J-lens) technique
  identifies a J-space in Claude where internal representations are reportable,
  modifiable, and used for deliberate reasoning, and demonstrated this through
  interventions that alter model outputs and detect hidden goals or
  fabrications.`
- **Exact quote / source:** “Claude can report on these representations ... It
  can also modulate them on request ... Claude uses its J-space for internal
  reasoning.” — [Anthropic, “A global workspace in language
  models”](https://www.anthropic.com/research/global-workspace)
- **Recommended action:** Apply Anthropic's open-source J-lens implementation to
  an open-weight model and test reportability, modifiability, and causal use in
  multi-step reasoning.
- **Validation boundary:** Claude-specific architecture and training;
  vocabulary-aligned single-token representations can miss non-verbalizable or
  multi-token concepts.
- **Senior judgment:** High-value research lead with an accessible method and
  crisp falsifiable tests. The displayed quote supports the J-space properties;
  the same frozen primary artifact separately documents intervention, prompt
  injection, fabricated-data, and hidden-goal experiments. That latter material
  should ideally be part of the displayed exact passage, but it is not a
  third-party or causal upgrade. No duplicate was found.

### 2026-07-07 — `candidate-7dcde26092d5b33cf662` — KEEP

- **Event:** `3e683e05c9cac039fb57c6888dd3b25ed479ef04764679042de8fbfe59efd69e`
- **Claim:** `Viv Trivedy reported that adjusting the harness by hill-climbing
  correctness metrics and traces achieved a 13.7% lift over the base harness on
  Terminal Bench 2.0.`
- **Exact quote / source:** “On Terminal Bench 2.0, we found that simply
  adjusting the harness by hill-climbing correctness metrics & traces to
  understand behavior gave us a big 13.7% lift over the base harness.” —
  [Viv Trivedy, “Improving Agents is a Data Mining
  Problem”](http://x.com/i/article/2073138207986966528)
- **Recommended action:** Reproduce the trace-informed harness search on
  Terminal Bench 2.0 and test for a 13.7% lift over the base harness.
- **Validation boundary:** One benchmark and one described search method;
  generalization depends on similar environments and trace distributions.
- **Senior judgment:** Strong and specific. A senior agent builder could use
  this to prioritize trace mining and harness search before fine-tuning. It
  differs from the Jul 10 adaptive-taxonomy item: this is harness hill-climbing,
  while Jul 10 is a dynamic failure-taxonomy/judge intervention.

### 2026-07-07 — `candidate-8f6f2de0b249419bc166` — KEEP

- **Event:** `617983f58b2b244841a3869a9191c46a78a3d43699123757ce315d3964d3ac7b`
- **Claim:** `DoorDash reported that Kimi K2.6 + Fable 5 vastly outperforms
  their current Sonnet 4.6 + Opus 4.8 harness at a cheaper cost when evaluated
  on their DashBench benchmark for code review.`
- **Exact quote / source:** “With DashBench we’ve seen Kimi K2.6 + Fable 5
  vastly outperform our current Sonnet 4.6 + Opus 4.8 harness at a cheaper
  cost.” — [DoorDash AI](https://x.com/aiatdoordash/status/2074245510450528534)
- **Recommended action:** Compare those two ensembles on representative pull
  requests using issue-detection rate and cost per PR.
- **Validation boundary:** DoorDash's internal PR distribution and DashBench;
  external use requires comparable code, exact model versions, and a consistent
  evaluation procedure.
- **Senior judgment:** Useful first-party model-routing evidence. The immutable
  claim correctly attributes DoorDash's report and does not invent the missing
  magnitude. The action is executable on the reader's own benchmark even though
  DashBench itself is private. No duplicate was found.

### 2026-07-08 — `candidate-9d908ab849dea6c90ded` — KEEP

- **Event:** `beaf19ab8c13849a0368675d0bca4e90d51f4aafcf73cbf36ae063fe69232ef2`
- **Claim:** `Artificial Analysis reports that Grok 4.5 in Grok Build scores 76
  on the Artificial Analysis Coding Agent Index, on par with GPT-5.5 (xhigh) in
  Codex and just below Fable 5 (max) in Claude Code, and at a small fraction of
  the token usage and price.`
- **Exact quote / source:** “Grok 4.5 in Grok Build scores 76 on the Artificial
  Analysis Coding Agent Index, on par with GPT-5.5 (xhigh) in Codex and just
  below Fable 5 (max) in Claude Code, and at a small fraction of the token usage
  and price.” — [Artificial Analysis](https://x.com/artificialanlys/status/2074956932289282087)
- **Recommended action:** Benchmark the named models/harnesses on the Coding
  Agent Index workloads and compare score, total tokens, and price.
- **Validation boundary:** Artificial Analysis methodology, Grok Build harness,
  exact model versions, task distribution, and contemporary pricing.
- **Senior judgment:** Keep as explicitly third-party comparative evidence, not
  a product fact from xAI. It gives a concrete model-selection experiment and
  raw efficiency numbers. The Jul 13 Grok repository-upload candidate is a
  separate event and remains excluded. No history duplicate was found.

### 2026-07-08 — `candidate-99caee99682d01670b9d` — VETO

- **Event:** `761d9cb2a6addc74be7ab43ad619cb890dfedc7c503780b9dda8ca4ee6216169`
- **Claim:** `Nous Research announces that Hermes Agent is now available in the
  Cloud, with a setup process requiring two clicks and taking 60 seconds after
  selecting a model and server size.`
- **Exact quote / source:** “Setup couldn't be simpler: pick a model and a
  server size. Two clicks and 60 seconds later, your agent is live.” —
  [Nous Research](https://x.com/nousresearch/status/2074878754485043333)
- **Recommended action:** Repeat the portal onboarding and time the interval to
  a live agent.
- **Validation boundary:** Nous Portal, selected model/server size, network,
  server load, and hardware.
- **Senior judgment:** Insufficient decision value. This is product-availability
  marketing whose experiment is only timing a two-click onboarding flow. It
  contains no implementation method, reliability characteristic, workload,
  meaningful comparison, or production acceptance criterion. A senior builder
  can learn it by visiting the product page; it does not earn a daily insight.
  The adjacent audit passes mechanically, so an explicit editorial sidecar is
  required rather than an audit override.

### 2026-07-09 — `candidate-2e96676419f142745cf6` — VETO

- **Event:** `30607d48305f2a38106429751b4933000f75efb13ba8d125e1c7260cfd47b180`
- **Claim:** `The Cerebras DevX team reported that Gemma 4 31B on Cerebras
  completes a 60-page document analysis task in 1.79 seconds, a 17× speedup
  over GPU providers.`
- **Exact quote / source:** “From input to output, the full response returned in
  1.79 seconds on Cerebras, compared to almost 25 seconds on GPU providers, a
  17× speedup on Cerebras.” — [Cerebras DevX, “First Look @ Gemma 4 on
  Cerebras”](http://x.com/i/article/2074968959510773760)
- **Recommended action:** Reproduce the 60-page task with identical prompts,
  batching, and system configuration and verify 1.79 seconds / 17×.
- **Validation boundary:** Gemma 4 31B on Cerebras WSE-3 plus the team's prompt
  and system optimizations; performance varies by model, hardware, data, and
  system design.
- **Senior judgment:** Analytical overstatement in the immutable source/item.
  `25 / 1.79` is approximately `14×`, not `17×`, and “GPU providers” is an
  unnamed comparison with no exposed hardware or serving configuration. The
  proposed “identical” reproduction is therefore impossible from the frozen
  evidence. The underlying article has useful implementation advice, but this
  selected headline comparison cannot be presented as a defensible benchmark.
  The adjacent audit passes mechanically, so removal requires an explicit
  editorial sidecar.

### 2026-07-10 — `candidate-7f90561db3a20b241c12` — KEEP

- **Event:** `3ec21bbb2ca40fcfefd149b2d27054c8f50b1b486cf2d1203af9d266d9437709`
- **Claim:** `The authors reported that their adaptive failure taxonomy used
  with a Best-of-N Judge achieved 89.9% on Terminal Bench 2 with Opus 4.6 /
  Forgecode harness, outperforming fixed taxonomies by 15%.`
- **Exact quote / source:** “On Terminal Bench 2 we get 89.9% with Opus 4.6 /
  Forgecode harness and the adaptive taxonomy used with a Best-of-N Judge,
  outperforming fixed taxonomies by 15%.” —
  [@alexgdimakis](https://x.com/alexgdimakis/status/2075607072389861389)
- **Recommended action:** Benchmark adaptive versus fixed taxonomies on
  Terminal Bench 2 with the named model, harness, and Best-of-N judge.
- **Validation boundary:** One benchmark, model, harness, and judge
  configuration; other tasks and systems may differ.
- **Senior judgment:** Excellent builder signal. It names a concrete test-time
  technique, baseline class, benchmark, system configuration, and target. It is
  related to, but not redundant with, the Jul 7 trace-guided harness-search
  result.

### 2026-07-10 — `candidate-69f29c9ddd4d63a9bc22` — KEEP

- **Event:** `92b637ae981d3dc7ffe343aa8a0e7e0464fb04af3a66a249d721c73920c6bb22`
- **Claim:** `We’re releasing new Qwen3.6 quants that run 2.5× faster on your
  GPU. Qwen3.6-27B NVFP4 runs on 24GB VRAM. 35B-A3B can hit 17,561 tok/s
  (B200).`
- **Exact quote / source:** “Qwen3.6-27B NVFP4 runs on 24GB VRAM. 35B-A3B can
  hit 17,561 tok/s (B200).” —
  [Unsloth](https://x.com/unslothai/status/2075566124687892597)
- **Recommended action:** Reproduce the 35B-A3B throughput and 27B NVFP4 memory
  footprint under the corresponding quantization/hardware conditions.
- **Validation boundary:** Vendor-reported NVFP4 configuration and B200 for the
  throughput number; other accelerators and quantization schemes may differ.
- **Senior judgment:** Keep, with a visible provenance caveat. The numbers are
  concrete deployment-feasibility targets. The immutable first-person claim and
  “Confirms” wording in `why_it_matters` are looser than ideal, and the 24GB
  memory statement is not explicitly tied to B200; the source author displayed
  beside the item and a reproduction-first action prevent this from becoming an
  independent factual assertion. This new r4 item changes later history and is
  why Jul 11-13 must be rebuilt.

### 2026-07-13 — `candidate-7df4fb2fff1103a2a1c3` — KEEP

- **Event:** `9c08799f942eeaadc5e854c4c2c968518c839b33df6f73a92d414411bf00682c`
- **Claim:** `The author observed that initializing a MNIST classifier with a
  face image results in the face remaining visible after training across
  various configurations including different initializations, weight decay
  values, learning rates, and optimizers.`
- **Exact quote / source:** “i trained a MNIST classifier initialized to my face
  and you can still see me at the end works across inits, weight decay, LR,
  optimizers” — [@willdepue](https://x.com/willdepue/status/2076581570782056523)
- **Recommended action:** Recreate the MNIST/face initialization and vary
  initialization, weight decay, learning rate, and optimizer to check whether
  the visible pattern persists.
- **Validation boundary:** MNIST, the face-image initialization method, and the
  tested hyperparameters; no generalization to other data or architectures.
- **Senior judgment:** Coherent as a small, surprising, inexpensive experiment
  about persistence in learned weights. “Visible” is a qualitative success
  boundary and the security/robustness implication is exploratory rather than
  established, but both are clearly hedged. Keep it as an experiment lead, not
  a general training-dynamics result. No duplicate was found.

## Explicit exclusion checks

- Jul 13 `candidate-74bba40c993c25bb961a` is **not** in
  `publication_selection`. Its exact third-party GitHub investigation was
  written as unqualified xAI product fact; item review fails claim fidelity and
  epistemic discipline, and the adjacent adjudication is `would_not_enter`.
  It remains excluded.
- The Jul 13 MNIST persistence item is internally coherent at its stated narrow
  boundary and remains included.

## Release recommendation

- Provisional mechanically effective set before this audit: **12** items.
- Additional senior editorial vetoes prepared here: **2** items (Hermes Cloud,
  Cerebras 17× benchmark).
- Senior-approved content set if the exact chronological chain is rebuilt and
  all adjacent audits/finalizations validate: **10** items.
- Outstanding release blocker: rebuild Jul 11-13 from the Jul 10 provider-safe
  r4 history and keep MuScriptor out unless a new exact item clears the adjacent
  publication audit.

The two review JSON files next to this report are inputs only. Applying them is
the parent reconciler's decision and must create immutable adjacent
`publication-finalization-v1` sidecars; this audit did not do so.
