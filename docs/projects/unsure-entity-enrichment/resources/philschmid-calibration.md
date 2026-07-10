# `@philschmid` web-enrichment calibration

> Historical discarded calibration. Adi explicitly removed this stray
> candidate and all of its local evidence on 2026-07-10. No staged enrichment
> row or canonical Registry entity remains.

Captured 2026-07-10 through the shared LiteLLM `gpt-5.6-luna` route. This is a
staged calibration result, not a canonical Registry promotion.

## Stage 0: deterministic selection

- Entity ID: `2604`
- Canonical kind before and after: `unsure`
- Selection rule: the web runner accepts only current X-backed `unsure`
  entities.

## Stage 1: profile-only classifier

Exact model input:

```json
{
  "handle": "philschmid",
  "display_name": "@philschmid",
  "bio": null,
  "profile_url": "https://x.com/philschmid"
}
```

Contract:

- Model: `gpt-5.6-luna`
- Reasoning: `medium`
- Prompt: `entity-kind-v2`
- Input SHA-256:
  `b3c8a2629e47d7419b89c72c5122238116b9c31285366d32562a3c46ca73d638`

Stored output:

```json
{
  "classification": "unsure",
  "reason": "The profile provides only a handle-like display name and no biography, so there is insufficient evidence to determine whether it represents an individual or an organization."
}
```

This is the intended abstention: stage one was prohibited from using outside
knowledge.

## Stage 2: required hosted web search

The same four-field JSON input was sent with:

- Prompt: `entity-kind-web-v1`
- Model/reasoning: `gpt-5.6-luna` / `medium`
- Tool: `{"type":"web_search","search_context_size":"medium"}`
- Tool choice: `required`
- Included evidence: `web_search_call.action.sources`
- Output contract: the same strict `classification` + `reason` schema
- Maximum output: 600 tokens
- Storage: disabled at the provider; observable evidence is stored locally
- LiteLLM tags: app, pipeline, web-enrichment job, single calibration scope,
  prompt version, and run ID `8`

Observed hosted action:

```json
[
  {
    "type": "search",
    "query": "site:x.com/philschmid philschmid"
  }
]
```

## Staged output

```json
{
  "classification": "person",
  "reason": "The handle matches Philipp Schmid, whose personal website and Hugging Face profile identify him as an individual technical lead and machine-learning professional."
}
```

Usage and cost:

- Input tokens: `8,698`
- Output tokens: `160`
- LiteLLM-reported cost: `$0.009658`
- Runner estimate: `$0.009658`
- Status: completed; zero errors

## Consulted sources

The hosted tool returned 17 deduplicated URLs:

1. `https://www.philschmid.de/`
2. `https://huggingface.co/philschmid`
3. `https://philippschmidt.org/`
4. `https://www.fcb.ch/pages/news?category=2`
5. `https://www.philschmid.de/philipp-schmid`
6. `https://github.com/philschmid`
7. `https://huggingface.co/philschmid/activity/community`
8. `https://philippschmid.org/?page_id=7`
9. `https://github.com/hieggAI/`
10. `https://philippschmidt.org/about.html`
11. `https://me.sh/profile/philipp-schmid`
12. `https://www.olympics.com/en/athletes/schmid-4`
13. `https://grokipedia.com/page/philipp_schmid`
14. `https://philippschmid.org/?page_id=2`
15. `https://ai.fantasy.co/interviews/philipp-schmid`
16. `https://www.philippschmid.dev/`
17. `https://aws.amazon.com/blogs/machine-learning/author/awsnaushphilippschmidamazon-com/`

## Review

The label is convincing because the result names the matching personal site and
Hugging Face identity, both present in the returned source set. The search also
returned unrelated namesakes and weak sources. `sources_json` therefore proves
what the tool consulted, but the structured final message supplied no
`url_citation` annotations, so it does not mechanically bind the reason to a
minimal evidence subset. Decide whether the full pass needs that stronger
binding before promotion.
