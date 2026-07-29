"""CLI entrypoint. Pipeline stages become subcommands as they land."""

import argparse
import sys

from fli import __version__


def main(argv: list[str] | None = None) -> int:
    raw_args = list(argv) if argv is not None else sys.argv[1:]
    if raw_args and raw_args[0] == "evidence-refresh":
        from fli.evidence import refresh as evidence_refresh

        return evidence_refresh.main(raw_args[1:])
    if raw_args and raw_args[0] == "prompt-cache-canary":
        from fli.diagnostics import prompt_cache

        return prompt_cache.main(raw_args[1:])
    if raw_args and raw_args[0] == "insights":
        from fli.insights import cli as insight_cli

        return insight_cli.main(raw_args[1:])
    parser = argparse.ArgumentParser(
        prog="fli",
        description="Frontier Lab Intelligence pipeline.",
    )
    parser.add_argument("--version", action="version", version=f"fli {__version__}")
    sub = parser.add_subparsers(dest="command")
    web = sub.add_parser("web", help="Serve the web UI.")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8500)
    fetch_p = sub.add_parser("fetch", help="Fetch raw public output for tracked labs.")
    fetch_p.add_argument("--db", default=None, help="Path to SQLite DB.")
    labs_p = sub.add_parser("labs", help="Hand-curated lab registry.")
    labs_p.add_argument("action", choices=["seed", "summary"])
    labs_p.add_argument("--db", default=None, help="Path to SQLite DB.")
    channels_p = sub.add_parser("channels", help="Entity/channel model.")
    channels_p.add_argument("action", choices=["sync", "summary"])
    channels_p.add_argument("--db", default=None, help="Path to SQLite DB.")
    registry_p = sub.add_parser("registry", help="Registry identity curation.")
    registry_p.add_argument("registry_args", nargs=argparse.REMAINDER)
    sources_p = sub.add_parser("sources", help="Curated source importers.")
    sources_p.add_argument("source_args", nargs=argparse.REMAINDER)
    conference_sources_p = sub.add_parser(
        "conference-sources",
        help="Snapshot, audit, or import curated conference speakers.",
    )
    conference_sources_p.add_argument(
        "conference_source_args", nargs=argparse.REMAINDER
    )
    following_snapshot_p = sub.add_parser(
        "following-snapshot", help="Local outgoing-follow snapshot storage."
    )
    following_snapshot_p.add_argument("snapshot_args", nargs=argparse.REMAINDER)
    following_ranking_p = sub.add_parser(
        "following-ranking", help="Derived ranking over a frozen follow snapshot."
    )
    following_ranking_p.add_argument("ranking_args", nargs=argparse.REMAINDER)
    entity_kinds_p = sub.add_parser(
        "entity-kinds", help="Classify provisional entity structure."
    )
    entity_kinds_p.add_argument("entity_kind_args", nargs=argparse.REMAINDER)
    relevance_p = sub.add_parser(
        "relevance-audit", help="Web-grounded Registry relevance audit."
    )
    relevance_p.add_argument("relevance_args", nargs=argparse.REMAINDER)
    registry_evaluation_p = sub.add_parser(
        "registry-evaluation", help="Cached combined kind and Registry evaluation."
    )
    registry_evaluation_p.add_argument("evaluation_args", nargs=argparse.REMAINDER)
    signal_feed_p = sub.add_parser(
        "signal-feed", help="Materialize the deterministic X evidence Feed."
    )
    signal_feed_p.add_argument("feed_args", nargs=argparse.REMAINDER)
    signal_events_p = sub.add_parser(
        "signal-events", help="Group exact structural Feed evidence."
    )
    signal_events_p.add_argument("event_args", nargs=argparse.REMAINDER)
    audience_routing_p = sub.add_parser(
        "audience-routing", help="Route Evidence Events by audience."
    )
    audience_routing_p.add_argument("audience_routing_args", nargs=argparse.REMAINDER)
    insights_p = sub.add_parser(
        "insights", help="Run and inspect durable audience Insight generation."
    )
    insights_p.add_argument("insights_args", nargs=argparse.REMAINDER)
    daily_rank_p = sub.add_parser(
        "daily-rank", help="Evaluate the versioned daily Event ranking."
    )
    daily_rank_p.add_argument("daily_rank_args", nargs=argparse.REMAINDER)
    x_daily_collection_p = sub.add_parser(
        "x-daily-collection",
        help="Plan or resume date-complete Registry X collection.",
    )
    x_daily_collection_p.add_argument(
        "collection_args", nargs=argparse.REMAINDER
    )
    evidence_refresh_p = sub.add_parser(
        "evidence-refresh",
        help="Refresh Feed Events and source artifacts end to end.",
        add_help=False,
    )
    evidence_refresh_p.add_argument("refresh_args", nargs=argparse.REMAINDER)
    artifacts_p = sub.add_parser(
        "artifacts", help="Catalog and fetch canonical external artifacts."
    )
    artifacts_p.add_argument("artifact_args", nargs=argparse.REMAINDER)
    prompt_cache_p = sub.add_parser(
        "prompt-cache-canary",
        help="Verify reusable-prefix caching through LiteLLM.",
    )
    prompt_cache_p.add_argument("prompt_cache_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(raw_args)

    if args.command == "web":
        import uvicorn

        uvicorn.run("fli.web.app:app", host=args.host, port=args.port)
        return 0

    if args.command == "fetch":
        from fli import store
        from fli.ingestion import public_sources as fetch

        conn = store.connect(args.db) if args.db else store.connect()
        fetch.fetch_all(conn)
        for row in store.raw_counts(conn):
            print(f"total: {row['lab']:10s} {row['source']:7s} {row['n']}")
        return 0

    if args.command == "labs":
        from fli.registry import seeds as labs

        return labs.main(
            [
                args.action,
                *(["--db", args.db] if args.db else []),
            ]
        )

    if args.command == "channels":
        from fli.registry import channels

        return channels.main(
            [
                args.action,
                *(["--db", args.db] if args.db else []),
            ]
        )

    if args.command == "registry":
        from fli.registry import store as registry

        return registry.main(args.registry_args)

    if args.command == "sources":
        from fli.ingestion import sources

        return sources.main(args.source_args)

    if args.command == "conference-sources":
        from fli.ingestion import conference as conference_sources

        return conference_sources.main(args.conference_source_args)

    if args.command == "following-snapshot":
        from fli.network import snapshots as following_snapshots

        return following_snapshots.main(args.snapshot_args)

    if args.command == "following-ranking":
        from fli.network import rankings as following_rankings

        return following_rankings.main(args.ranking_args)

    if args.command == "entity-kinds":
        from fli.registry import classification as entity_kinds

        return entity_kinds.main(args.entity_kind_args)

    if args.command == "relevance-audit":
        from fli.registry import relevance

        return relevance.main(args.relevance_args)

    if args.command == "registry-evaluation":
        from fli.registry import evaluation_runs as registry_evaluation_runs

        return registry_evaluation_runs.main(args.evaluation_args)

    if args.command == "signal-feed":
        from fli.evidence import feed as signal_feed

        return signal_feed.main(args.feed_args)

    if args.command == "signal-events":
        from fli.evidence import events as signal_events

        return signal_events.main(args.event_args)

    if args.command == "audience-routing":
        from fli.routing import runs as audience_routing_runs

        return audience_routing_runs.main(args.audience_routing_args)

    if args.command == "insights":
        from fli.insights import cli as insight_cli

        return insight_cli.main(args.insights_args)

    if args.command == "daily-rank":
        from fli.scoring import evaluation

        return evaluation.main(args.daily_rank_args)

    if args.command == "x-daily-collection":
        from fli.ingestion.x import collection as x_daily_collection

        return x_daily_collection.main(args.collection_args)

    if args.command == "evidence-refresh":
        from fli.evidence import refresh as evidence_refresh

        return evidence_refresh.main(args.refresh_args)

    if args.command == "artifacts":
        from fli.evidence.artifacts import cli as artifacts

        return artifacts.main(args.artifact_args)

    if args.command == "prompt-cache-canary":
        from fli.diagnostics import prompt_cache

        return prompt_cache.main(args.prompt_cache_args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
