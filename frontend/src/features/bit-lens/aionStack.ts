/**
 * The assumed Aion stack — seven surfaces of the research platform BIT's AI
 * team operates, inferred from its public AI Engineer and Data Platform roles.
 *
 * This is deliberately a short list of buckets, not a specification. Its only
 * job is to give a daily Engineering Insight one thing to point at: which part
 * of their system today's development would land on.
 *
 * A map for judging relevance, not a claim about BIT's private architecture.
 */

export interface AionSurface {
  id: string
  name: string
  what: string
}

export const AION_SURFACES: readonly AionSurface[] = [
  {
    id: 'DATA',
    name: 'Data platform',
    what: 'Pipelines that ingest filings, transcripts, market and alternative data, and keep it queryable and clean.',
  },
  {
    id: 'RETR',
    name: 'Retrieval',
    what: 'Finding the right evidence in the research corpus — search, embeddings, ranking, filters.',
  },
  {
    id: 'EXTR',
    name: 'Extraction',
    what: 'Turning documents and text into structured, attributed fields an analyst can trace back to a source.',
  },
  {
    id: 'AGENT',
    name: 'Agents',
    what: 'Research skills that plan, use tools, run code and draft — the part BIT names publicly as Aion.',
  },
  {
    id: 'MODEL',
    name: 'Models and cost',
    what: 'Which model runs which task, with fallbacks, caching, and the token and dollar cost of each workflow.',
  },
  {
    id: 'EVAL',
    name: 'Evaluation',
    what: 'Knowing whether output is right — accuracy, hallucination, uncertainty, and regressions when something changes.',
  },
  {
    id: 'OPS',
    name: 'Operations',
    what: 'Running it safely in production — what an agent may touch, plus tracing, monitoring and failure recovery.',
  },
]
