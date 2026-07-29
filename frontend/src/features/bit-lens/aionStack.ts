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
  scope: string
}

export const AION_SURFACES: readonly AionSurface[] = [
  {
    id: 'DATA',
    name: 'Data platform',
    what:
      'Pipelines that ingest filings, transcripts, market and alternative data, and keep it queryable and clean.',
    scope:
      'Ingestion adapters, scheduling and orchestration, lakehouse or warehouse storage, schema and data-quality checks, lineage, and the SQL and Python layer analysts and agents query.',
  },
  {
    id: 'RETR',
    name: 'Retrieval',
    what:
      'Finding the right evidence in the research corpus — search, embeddings, ranking, filters.',
    scope:
      'Chunking, embedding models, vector and keyword search, reranking, metadata filters by company, date and source type, and how much retrieval is needed given model context limits.',
  },
  {
    id: 'EXTR',
    name: 'Extraction',
    what:
      'Turning documents and text into structured, attributed fields an analyst can trace back to a source.',
    scope:
      'Prompt and schema design, structured output and function calling, document and table parsing, source spans and citation fidelity, and silent extraction error.',
  },
  {
    id: 'AGENT',
    name: 'Agents',
    what:
      'Research skills that plan, use tools, run code and draft — the part BIT names publicly as Aion.',
    scope:
      'Planning and multi-step execution, tool use, memory, reusable research skills, code sidecars, agent harnesses and protocols, and long-horizon reliability.',
  },
  {
    id: 'MODEL',
    name: 'Models and cost',
    what:
      'Which model runs which task, with fallbacks, caching, and the token and dollar cost of each workflow.',
    scope:
      'Model and reasoning-effort selection per task, price-performance changes, prompt caching and batching, context limits, fallbacks and version pinning, provider availability and deprecation.',
  },
  {
    id: 'EVAL',
    name: 'Evaluation',
    what:
      'Knowing whether output is right — accuracy, hallucination, uncertainty, and regressions when something changes.',
    scope:
      'Eval design and datasets, LLM-as-judge methods, hallucination and calibration measurement, human-in-the-loop review, regression testing across prompt and model changes, and benchmark transferability.',
  },
  {
    id: 'OPS',
    name: 'Operations',
    what:
      'Running it safely in production — what an agent may touch, plus tracing, monitoring and failure recovery.',
    scope:
      'Permissions and entitlements over sensitive or licensed data, scoped tool access and sandboxing for agents, audit trails, tracing across multi-step runs, latency and error monitoring, and incident recovery for scheduled jobs.',
  },
]
