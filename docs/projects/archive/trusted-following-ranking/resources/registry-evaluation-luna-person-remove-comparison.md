# Luna-High Comparison — Person Removal Cohort

Date: 2026-07-12

This run re-evaluated all 192 people that GPT-5.4-mini-high recommended for
removal. It reused the exact stored profile and ordered 20-post evidence from
the source run, made zero TwitterAPI.io requests, and did not mutate the
Registry.

## Result

| Luna decision | Count | Share |
| --- | ---: | ---: |
| Keep | 119 | 62.0% |
| Remove | 60 | 31.3% |
| Review | 13 | 6.8% |

Luna therefore overturned 132 of the 192 mini-model removal recommendations.
It searched for 147 entities (76.56%), using 251 web-search actions and
recording 3,376 sources. The run used 2,567,173 input tokens, zero cached
tokens, and 130,899 output tokens. LiteLLM-reported cost was `$3.371936`.
All 192 rows completed with zero terminal failures in about 4.5 minutes.

191 current results used `gpt-5.6-luna`; `@timnitgebru` again took LiteLLM's
configured `claude-sonnet-4-6` fallback. The fallback is explicit in the run
database rather than hidden.

## Highest-followed comparison sample

| Person | Luna | Short reading |
| --- | --- | --- |
| Jeff Bezos | remove | Spaceflight/general commentary, not recurring AI signal |
| Eric Topol | remove | Biomedical focus; frontier-AI signal judged insufficient |
| Bill Gurley | keep | Recurring analysis of AI competition, economics, and policy |
| Austen Allred | review | AI operating role, but recent original signal is unclear |
| Justin Kan | remove | Personal/startup promotion rather than sustained AI work |
| Zeynep Tufekci | remove | Broad public commentary rather than focused AI intelligence |
| Travis Kalanick | review | Physical-AI relevance, but public evidence is thin |
| Matthew Prince | remove | Mostly personal/general output |
| shadcn | remove | Frontend tooling with incidental AI references |
| 宝玉 / `@dotey` | keep | Sustained model, agent, coding-tool, and workflow analysis |
| Bill Gross | remove | Promotional and generic AI-productivity content |
| Jarred Sumner | remove | Bun/runtime output; Anthropic role absent from supplied evidence |
| Grady Booch | remove | Broad commentary without sustained frontier-AI output |
| Timnit Gebru | remove | Social/political AI-industry criticism under the current rubric |
| Zephyr | review | Frontier-AI focus, but original signal remains uncertain |
| Joscha Bach | keep | Durable research program in AGI and cognitive architectures |
| Alfredo Canziani | keep | Recurring deep-learning research and technical education |
| Will Manidis | remove | Finance/culture feed with occasional AI observations |
| Pedro Domingos | keep | Sustained original ML and frontier-AI commentary |
| Panos Panay | remove | Corporate product promotion rather than original analysis |

## Jarred Sumner failure analysis

The exact input had a null bio and 20 posts dominated by Bun v1.4, its Rust
rewrite, Node.js compatibility, Web Streams, JSON parsing, source maps, and
React Compiler performance. Only one post mentioned Claude. Luna did not invoke
web search for this identity, so neither model received evidence that Sumner
had joined Anthropic.

This is an evidence-boundary failure, not a reason to apply the mini result or
to assume a larger model will recover missing facts. Before removing prominent
or ambiguous people, the workflow needs durable role evidence or an explicit
web-grounded verification step. The 60 Luna-agreed removals remain review
candidates, not automatic Registry mutations.
