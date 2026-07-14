# AI Engineer conference source import — 2026-07-14

## Decision

Preserve the complete supported official conference sources, but admit only a
small deterministic first cohort: the first 20 unique X-addressable speakers
in the World's Fair 2026 official response. Conference inclusion is source
provenance, not a ranking boost, voting weight, or claim that these are the
best 20 people in AI.

## Pre-import coverage

The coverage audit ran before the Registry write:

- 945 records across four official sources.
- 878 unique names and 528 unique X handles.
- 101 X handles already in the active Registry; 427 were new; zero matched a
  rejected identity.
- 499 normalized company labels were available for later organization work.

Supported snapshots:

| Source | Records | X records | SHA-256 |
|---|---:|---:|---|
| AI Engineer World's Fair 2026 | 552 | 315 | `d05c46958f2a6cfa199dbc75e05f204e2b154fc8efe1c95279f8caccbafb4d32` |
| AI Engineer Europe 2026 | 162 | 103 | `949fc1b2c827f65e4f7b0140fef9f5db6333610f7c0f6394fa2ab2f3a1df922c` |
| AI Engineer World's Fair 2024 | 173 | 134 | `04722928a72ad601ad296c046bf67049cddb79d7f7dff427c60615e3537be02d` |
| AI Engineer Summit 2023 | 58 | 34 | `cffd5e2426d3f44b7b5738e476dc8ec896eb981f2ab01bd0b5357cd8149178bb` |

Raw responses live in ignored `data/raw/conference-sources/`; the tracked
manifest at `data/registry/conference-sources.json` binds IDs, URLs, formats,
and observation dates.

## Imported cohort

The stable source-order cohort was:

1. Abhishek Bhardwaj — `@abshkbh` — OpenAI
2. Adam Azzam — `@aaazzam` — Modal
3. Adam Huda — `@hudaman` — Uber
4. Addy Osmani — `@addyosmani` — no organization listed
5. Adi Singh — `@adisingh` — AgentMail
6. Ahmad Osman — `@theahmadosman` — Osmantic
7. Ahmed Ahres — `@boudatw` — Reactor
8. Ajay Prakash — `@ajay_prakash_ai` — Linkedin
9. Alex Atallah — `@alexatallah` — OpenRouter
10. Alex Bauer — `@alexdbauer` — Upside
11. Alex Cheema — `@alexocheema` — EXO Labs
12. Alex Hancock — `@alexjhancock` — Block
13. Alex Volkov — `@altryne` — W&B from CoreWeave
14. Alexander Embiricos — `@embirico` — OpenAI
15. Aman Gupta — `@aman2304` — Nubank
16. Amit Navindgi — `@amitnavindgi` — Zoox
17. Andrew Dai — `@andrewdai` — Elorian
18. Andrew Orobator — `@aorobator` — Reddit
19. Andrew Qu — `@andrewqu` — Vercel
20. Ang Li — `@angli_ai` — Simular

Four matched existing people; 16 people and 15 organizations were new. The
write produced 20 conference-speaker facts, 20 roles, 20 bios, 19 company
facts, and 19 dated listed affiliations. Re-running the command is idempotent
and does not revive previously rejected entities.

## Canonical boundary

Canonical person data is limited to name, X identity, conference-supplied
role, bio, company label, dated affiliation, and provenance. A verified
official organization website may be attached where the source clearly
provides one. LinkedIn, session titles, personal sites/blogs, and ambiguous
company X links remain raw-only. New people are monitorable, but cannot vote in
the frozen 2026-07-11 following snapshot.

Reproduce:

```bash
PYTHONPATH=src .venv/bin/python -m fli.cli conference-sources snapshot
PYTHONPATH=src .venv/bin/python -m fli.cli conference-sources audit
PYTHONPATH=src .venv/bin/python -m fli.cli conference-sources import --limit 20
```

