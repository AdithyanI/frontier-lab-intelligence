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
    digg_p = sub.add_parser("digg", help="Scrape Digg rankings and top-follower edges.")
    digg_p.add_argument("--out", default="data/digg", help="Output directory.")
    digg_p.add_argument(
        "--profiles",
        type=int,
        default=20,
        help="Number of ranked people profiles to fetch for top-follower edges.",
    )
    digg_p.add_argument(
        "--include-companies",
        action="store_true",
        help="Fetch profile edges for company/org ranking rows too.",
    )
    digg_p.add_argument(
        "--workers",
        type=int,
        default=6,
        help="Concurrent profile fetches for top-follower edge extraction.",
    )
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

    if args.command == "digg":
        from fli import digg

        return digg.main(
            [
                "--out",
                args.out,
                "--profiles",
                str(args.profiles),
                "--workers",
                str(args.workers),
                *(["--include-companies"] if args.include_companies else []),
            ]
        )

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
