"""CLI entrypoint. Pipeline stages become subcommands as they land."""

import argparse

from fli import __version__


def main(argv: list[str] | None = None) -> int:
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
        "audience-routing", help="Route Evidence envelopes by audience."
    )
    audience_routing_p.add_argument("audience_routing_args", nargs=argparse.REMAINDER)
    x_daily_collection_p = sub.add_parser(
        "x-daily-collection",
        help="Plan or resume date-complete Registry X collection.",
    )
    x_daily_collection_p.add_argument(
        "collection_args", nargs=argparse.REMAINDER
    )
    evidence_refresh_p = sub.add_parser(
        "evidence-refresh",
        help="Refresh Evidence, envelopes, and primary artifacts end to end.",
    )
    evidence_refresh_p.add_argument("--through", required=True)
    evidence_refresh_p.add_argument("--days", type=int, default=9)
    evidence_refresh_p.add_argument("--workers", type=int, default=32)
    evidence_refresh_p.add_argument("--artifact-limit", type=int, default=None)
    evidence_refresh_p.add_argument("--x-article-limit", type=int, default=None)
    evidence_refresh_p.add_argument("--skip-collection", action="store_true")
    evidence_refresh_p.add_argument("--no-reader-fallback", action="store_true")
    evidence_refresh_p.add_argument("--no-view-warmup", action="store_true")
    evidence_refresh_p.add_argument(
        "--view-base-url", default="http://127.0.0.1:8797"
    )
    evidence_refresh_p.add_argument("--key-file")
    evidence_refresh_p.add_argument("--json", action="store_true")
    artifacts_p = sub.add_parser(
        "artifacts", help="Catalog and fetch canonical external artifacts."
    )
    artifacts_p.add_argument("artifact_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    if args.command == "web":
        import uvicorn

        uvicorn.run("fli.web.app:app", host=args.host, port=args.port)
        return 0

    if args.command == "fetch":
        from fli import fetch, store

        conn = store.connect(args.db) if args.db else store.connect()
        fetch.fetch_all(conn)
        for row in store.raw_counts(conn):
            print(f"total: {row['lab']:10s} {row['source']:7s} {row['n']}")
        return 0

    if args.command == "labs":
        from fli import labs

        return labs.main(
            [
                args.action,
                *(["--db", args.db] if args.db else []),
            ]
        )

    if args.command == "channels":
        from fli import channels

        return channels.main(
            [
                args.action,
                *(["--db", args.db] if args.db else []),
            ]
        )

    if args.command == "registry":
        from fli import registry

        return registry.main(args.registry_args)

    if args.command == "sources":
        from fli import sources

        return sources.main(args.source_args)

    if args.command == "conference-sources":
        from fli import conference_sources

        return conference_sources.main(args.conference_source_args)

    if args.command == "following-snapshot":
        from fli import following_snapshots

        return following_snapshots.main(args.snapshot_args)

    if args.command == "following-ranking":
        from fli import following_rankings

        return following_rankings.main(args.ranking_args)

    if args.command == "entity-kinds":
        from fli import entity_kinds

        return entity_kinds.main(args.entity_kind_args)

    if args.command == "relevance-audit":
        from fli import relevance

        return relevance.main(args.relevance_args)

    if args.command == "registry-evaluation":
        from fli import registry_evaluation_runs

        return registry_evaluation_runs.main(args.evaluation_args)

    if args.command == "signal-feed":
        from fli import signal_feed

        return signal_feed.main(args.feed_args)

    if args.command == "signal-events":
        from fli import signal_events

        return signal_events.main(args.event_args)

    if args.command == "audience-routing":
        from fli import audience_routing_runs

        return audience_routing_runs.main(args.audience_routing_args)

    if args.command == "x-daily-collection":
        from fli import x_daily_collection

        return x_daily_collection.main(args.collection_args)

    if args.command == "evidence-refresh":
        from fli import evidence_refresh

        refresh_args = [
            "--through",
            args.through,
            "--days",
            str(args.days),
            "--workers",
            str(args.workers),
        ]
        if args.artifact_limit is not None:
            refresh_args.extend(["--artifact-limit", str(args.artifact_limit)])
        if args.x_article_limit is not None:
            refresh_args.extend(["--x-article-limit", str(args.x_article_limit)])
        if args.skip_collection:
            refresh_args.append("--skip-collection")
        if args.no_reader_fallback:
            refresh_args.append("--no-reader-fallback")
        if args.no_view_warmup:
            refresh_args.append("--no-view-warmup")
        refresh_args.extend(["--view-base-url", args.view_base_url])
        if args.key_file:
            refresh_args.extend(["--key-file", args.key_file])
        if args.json:
            refresh_args.append("--json")
        return evidence_refresh.main(refresh_args)

    if args.command == "artifacts":
        from fli import artifacts

        return artifacts.main(args.artifact_args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
