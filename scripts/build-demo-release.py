#!/usr/bin/env python3
"""Build a minimal, immutable reviewer snapshot from the current local stores."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
from typing import Any
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE_ID = "fli-demo-2026-07-19"
FOLLOWING_ID = "registry-following-2026-07-14-aie-worldsfair-v2"
SCHEMA_VERSION = "fli-demo-release-v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _connect_readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)


def _backup(source: Path, target: Path) -> None:
    if not source.is_file():
        raise RuntimeError(f"Required release store is missing: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    source_conn = _connect_readonly(source)
    target_conn = sqlite3.connect(target)
    try:
        source_conn.backup(target_conn)
    finally:
        target_conn.close()
        source_conn.close()


def _published_runs(events_path: Path) -> tuple[str, str]:
    conn = _connect_readonly(events_path)
    try:
        row = conn.execute(
            """SELECT publication.event_run_id, run.feed_run_id
               FROM signal_publication publication
               JOIN event_run run ON run.run_id = publication.event_run_id
               WHERE publication.singleton = 1"""
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise RuntimeError("Signal publication has no current Event/Feed run.")
    return str(row[0]), str(row[1])


def _release_feed(source: Path, target: Path, run_id: str) -> None:
    _backup(source, target)
    conn = sqlite3.connect(target)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        for table in ("feed_relation", "feed_run_post", "feed_anchor", "feed_post"):
            conn.execute(f"DELETE FROM {table} WHERE run_id <> ?", [run_id])
        conn.execute("DELETE FROM feed_run WHERE run_id <> ?", [run_id])
        # The reader needs normalized text and provenance fields, not duplicate
        # provider response bodies. Raw evidence remains outside the public demo.
        conn.execute("UPDATE feed_post SET raw_json = '{}' WHERE run_id = ?", [run_id])
        conn.commit()
        conn.execute("VACUUM")
        conn.execute("PRAGMA integrity_check")
    finally:
        conn.close()


def _release_events(source: Path, target: Path, run_id: str) -> None:
    _backup(source, target)
    conn = sqlite3.connect(target)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        for table in ("event_link", "event_member", "event_day", "event_anchor", "event_cluster"):
            conn.execute(f"DELETE FROM {table} WHERE run_id <> ?", [run_id])
        conn.execute("DELETE FROM event_run WHERE run_id <> ?", [run_id])
        conn.commit()
        conn.execute("VACUUM")
        conn.execute("PRAGMA integrity_check")
    finally:
        conn.close()


def _release_analysis(source: Path, target: Path) -> None:
    _backup(source, target)
    conn = sqlite3.connect(target)
    try:
        # Bios are not part of any reviewer query. Removing them avoids shipping
        # duplicate profile prose while preserving the complete ranked universe.
        conn.execute("UPDATE graph_node SET bio = NULL")
        conn.execute("DELETE FROM ranking_comparison")
        conn.execute("DELETE FROM ranking_diagnostics")
        conn.commit()
        conn.execute("VACUUM")
        conn.execute("PRAGMA integrity_check")
    finally:
        conn.close()


def _release_following(source: Path, target: Path) -> None:
    if not source.is_file():
        raise RuntimeError(f"Required release store is missing: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    try:
        conn.execute("ATTACH DATABASE ? AS source", [source.resolve().as_posix()])
        for table in ("snapshot_run", "snapshot_lineage", "source_fetch", "edge"):
            conn.execute(f"CREATE TABLE {table} AS SELECT * FROM source.{table}")
        conn.execute("CREATE UNIQUE INDEX idx_source_fetch_x_id ON source_fetch(source_x_id)")
        conn.execute("CREATE INDEX idx_edge_target ON edge(target_x_id, source_x_id)")
        conn.execute("CREATE INDEX idx_edge_source ON edge(source_x_id, target_x_id)")
        conn.commit()
        conn.execute("DETACH DATABASE source")
        conn.execute("VACUUM")
        conn.execute("PRAGMA integrity_check")
    finally:
        conn.close()


def _routing_paths() -> list[Path]:
    paths: set[Path] = set()
    queries = (
        (REPO_ROOT / "data/derived/insights/insights.db", "SELECT DISTINCT source_routing_db FROM insight_run"),
        (REPO_ROOT / "data/derived/daily-intelligence/editorial.db", "SELECT DISTINCT source_routing_db FROM editorial_run"),
    )
    for database, query in queries:
        conn = _connect_readonly(database)
        try:
            paths.update(REPO_ROOT / str(row[0]) for row in conn.execute(query))
        finally:
            conn.close()
    return sorted(paths)


def _zip_tree(staging: Path, output: Path) -> tuple[int, int]:
    file_count = 0
    uncompressed_bytes = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as archive:
        for path in sorted(staging.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(staging).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2026, 7, 19, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            with path.open("rb") as source, archive.open(info, "w", force_zip64=True) as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)
            file_count += 1
            uncompressed_bytes += path.stat().st_size
    return file_count, uncompressed_bytes


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()


def build(*, release_id: str, output: Path, manifest_output: Path, force: bool) -> dict[str, Any]:
    work_root = REPO_ROOT / "tmp" / "demo-release"
    staging = work_root / "stage"
    if output.exists() and not force:
        raise RuntimeError(f"Release archive already exists: {output}")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    output.unlink(missing_ok=True)

    events_source = REPO_ROOT / "data/derived/signal-events/events.db"
    event_run_id, feed_run_id = _published_runs(events_source)
    _release_feed(
        REPO_ROOT / "data/derived/signal-feed/feed.db",
        staging / "data/derived/signal-feed/feed.db",
        feed_run_id,
    )
    _release_events(
        events_source,
        staging / "data/derived/signal-events/events.db",
        event_run_id,
    )
    _release_analysis(
        REPO_ROOT / f"data/derived/following/{FOLLOWING_ID}/analysis.db",
        staging / f"data/derived/following/{FOLLOWING_ID}/analysis.db",
    )
    _release_following(
        REPO_ROOT / f"data/raw/following/{FOLLOWING_ID}/snapshot.db",
        staging / f"data/raw/following/{FOLLOWING_ID}/snapshot.db",
    )

    for relative in (
        "data/derived/artifacts/artifacts.db",
        "data/derived/insights/insights.db",
        "data/derived/daily-intelligence/editorial.db",
    ):
        _backup(REPO_ROOT / relative, staging / relative)
    shutil.copytree(
        REPO_ROOT / "data/derived/artifacts/text",
        staging / "data/derived/artifacts/text",
    )
    for source in _routing_paths():
        relative = source.relative_to(REPO_ROOT)
        _backup(source, staging / relative)

    install_roots = [
        f"data/derived/following/{FOLLOWING_ID}",
        f"data/raw/following/{FOLLOWING_ID}",
        "data/derived/signal-feed",
        "data/derived/signal-events",
        "data/derived/artifacts",
        "data/derived/audience-routing",
        "data/derived/insights",
        "data/derived/daily-intelligence",
    ]
    file_count, uncompressed_bytes = _zip_tree(staging, output)
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "release_id": release_id,
        "source_commit": _git_head(),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "archive": {
            "filename": output.name,
            "url": None,
            "sha256": _sha256(output),
            "bytes": output.stat().st_size,
        },
        "install_roots": install_roots,
        "contents": {
            "file_count": file_count,
            "uncompressed_bytes": uncompressed_bytes,
            "event_run_id": event_run_id,
            "feed_run_id": feed_run_id,
            "following_snapshot_id": FOLLOWING_ID,
            "raw_provider_responses_included": False,
            "delivery_credentials_included": False,
        },
    }
    manifest_output.parent.mkdir(parents=True, exist_ok=True)
    manifest_output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shutil.rmtree(staging)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-id", default=DEFAULT_RELEASE_ID)
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "tmp/demo-release/fli-demo-2026-07-19.zip")
    parser.add_argument("--manifest-output", type=Path, default=REPO_ROOT / "tmp/demo-release/release.json")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        manifest = build(
            release_id=args.release_id,
            output=args.output.resolve(),
            manifest_output=args.manifest_output.resolve(),
            force=args.force,
        )
    except (OSError, RuntimeError, sqlite3.Error, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}")
        return 1
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
