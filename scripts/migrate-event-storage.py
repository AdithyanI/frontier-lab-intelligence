#!/usr/bin/env python3
"""Migrate active derived stores to Event-native storage names."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fli.evidence import events as event_store
from fli.evidence import feed as feed_store
from fli.evidence.artifacts import store as artifact_store
from fli.insights import editorial_runs
from fli.routing import runs as routing_runs


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate artifact, routing, and editorial SQLite storage in place."
    )
    parser.add_argument(
        "--artifact-db", type=Path, default=artifact_store.DEFAULT_DB
    )
    parser.add_argument("--feed-db", type=Path, default=feed_store.DEFAULT_FEED_DB)
    parser.add_argument(
        "--events-db", type=Path, default=event_store.DEFAULT_EVENTS_DB
    )
    parser.add_argument(
        "--routing-root", type=Path, default=routing_runs.DEFAULT_RUN_ROOT
    )
    parser.add_argument(
        "--editorial-db", type=Path, default=editorial_runs.DEFAULT_DB
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    routing_databases = sorted(args.routing_root.glob("*/routing.db"))
    artifact_schema_migrated = artifact_store.migrate_store(args.artifact_db)
    active_import = artifact_store.import_feed_events(
        db_path=args.artifact_db,
        feed_db=args.feed_db,
        events_db=args.events_db,
    )
    result = {
        "schema": "event-storage-migration-v1",
        "artifact_store": {
            "path": str(args.artifact_db),
            "schema_migrated": artifact_schema_migrated,
            "active_import": {
                "import_run_id": active_import["import_run_id"],
                "selection_policy": active_import["selection_policy"],
                "candidate_count": active_import["expected_candidate_count"],
                "reused": active_import["reused"],
            },
        },
        "routing_stores": {
            "root": str(args.routing_root),
            "database_count": len(routing_databases),
            "migrated_count": sum(
                routing_runs.migrate_run_storage(path)
                for path in routing_databases
            ),
        },
        "editorial_store": {
            "path": str(args.editorial_db),
            "migrated": editorial_runs.migrate_editorial_store(
                args.editorial_db
            ),
        },
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
