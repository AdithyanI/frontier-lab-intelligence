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
    entity_kinds_p = sub.add_parser(
        "entity-kinds", help="Classify provisional entity structure."
    )
    entity_kinds_p.add_argument("entity_kind_args", nargs=argparse.REMAINDER)
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

    if args.command == "entity-kinds":
        from fli import entity_kinds

        return entity_kinds.main(args.entity_kind_args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
