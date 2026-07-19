#!/usr/bin/env python3
"""Restore the immutable reviewer snapshot and launch the app safely."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen
import webbrowser
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "data" / "demo-release.json"
CACHE_ROOT = REPO_ROOT / "tmp" / "demo-release"
INSTALL_MARKER = REPO_ROOT / "data" / "derived" / ".demo-release.json"
SCHEMA_VERSION = "fli-demo-release-v1"
TRUTHY = {"1", "true", "yes", "on"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(path: Path, *, require_url: bool = True) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Demo manifest is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Demo manifest is invalid JSON: {path}") from exc
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("Unsupported demo release manifest.")
    archive = manifest.get("archive") or {}
    required_archive = ("filename", "sha256", "bytes")
    if any(not archive.get(field) for field in required_archive):
        raise RuntimeError("Demo manifest has an incomplete archive contract.")
    if require_url and not archive.get("url"):
        raise RuntimeError("Demo manifest has no download URL.")
    roots = manifest.get("install_roots")
    if not isinstance(roots, list) or not roots:
        raise RuntimeError("Demo manifest has no install roots.")
    for value in roots:
        path_value = PurePosixPath(str(value))
        if (
            path_value.is_absolute()
            or ".." in path_value.parts
            or not str(path_value).startswith(("data/derived/", "data/raw/following/"))
        ):
            raise RuntimeError(f"Unsafe demo install root: {value}")
    return manifest


def _marker_matches(manifest: dict[str, Any]) -> bool:
    if not INSTALL_MARKER.is_file():
        return False
    try:
        marker = json.loads(INSTALL_MARKER.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if marker.get("archive_sha256") != manifest["archive"]["sha256"]:
        return False
    return all((REPO_ROOT / root).exists() for root in manifest["install_roots"])


def _download(manifest: dict[str, Any]) -> Path:
    archive = manifest["archive"]
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    destination = CACHE_ROOT / str(archive["filename"])
    expected_hash = str(archive["sha256"])
    expected_bytes = int(archive["bytes"])
    if destination.is_file():
        if destination.stat().st_size == expected_bytes and _sha256(destination) == expected_hash:
            print(f"Using verified cached snapshot: {destination}")
            return destination
        destination.unlink()

    partial = destination.with_suffix(destination.suffix + ".partial")
    partial.unlink(missing_ok=True)
    print(f"Downloading reviewer snapshot ({expected_bytes / 1_000_000:.1f} MB)…")
    request = Request(str(archive["url"]), headers={"User-Agent": "fli-demo/1"})
    downloaded = 0
    try:
        with urlopen(request, timeout=60) as response, partial.open("wb") as target:
            while chunk := response.read(1024 * 1024):
                target.write(chunk)
                downloaded += len(chunk)
                if downloaded and downloaded % (50 * 1024 * 1024) < len(chunk):
                    print(f"  {downloaded / 1_000_000:.0f} MB")
    except (OSError, URLError) as exc:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"Could not download the demo snapshot: {exc}") from exc
    if downloaded != expected_bytes or _sha256(partial) != expected_hash:
        partial.unlink(missing_ok=True)
        raise RuntimeError("Downloaded snapshot failed its size or SHA-256 check.")
    os.replace(partial, destination)
    return destination


def _safe_members(archive: zipfile.ZipFile, roots: list[str]) -> list[zipfile.ZipInfo]:
    allowed = tuple(f"{root.rstrip('/')}/" for root in roots)
    members: list[zipfile.ZipInfo] = []
    for member in archive.infolist():
        value = PurePosixPath(member.filename)
        mode = member.external_attr >> 16
        if value.is_absolute() or ".." in value.parts or (mode & 0o170000) == 0o120000:
            raise RuntimeError(f"Unsafe path in demo snapshot: {member.filename}")
        normalized = value.as_posix()
        if not any(normalized == root or normalized.startswith(prefix) for root, prefix in zip(roots, allowed)):
            raise RuntimeError(f"Unexpected path in demo snapshot: {member.filename}")
        members.append(member)
    return members


def _install_snapshot(manifest: dict[str, Any], archive_path: Path, *, force: bool) -> None:
    roots = [str(root).rstrip("/") for root in manifest["install_roots"]]
    existing = [root for root in roots if (REPO_ROOT / root).exists()]
    if existing and not force:
        joined = "\n  ".join(existing)
        raise RuntimeError(
            "Local runtime data already exists and was not created by this demo release. "
            "Use a clean checkout, or rerun with --force to replace only these release paths:\n  "
            + joined
        )

    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="extract-", dir=CACHE_ROOT))
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = _safe_members(archive, roots)
            print(f"Restoring {len(members):,} verified snapshot files…")
            archive.extractall(staging, members=members)
        for root in roots:
            source = staging / root
            if not source.exists():
                raise RuntimeError(f"Snapshot is missing install root: {root}")
        for root in roots:
            target = REPO_ROOT / root
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staging / root), str(target))
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    INSTALL_MARKER.parent.mkdir(parents=True, exist_ok=True)
    INSTALL_MARKER.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "release_id": manifest["release_id"],
                "archive_sha256": manifest["archive"]["sha256"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _ensure_venv(*, skip_install: bool) -> Path:
    if sys.version_info < (3, 13):
        raise RuntimeError("Frontier Lab Intelligence requires Python 3.13 or newer.")
    python = REPO_ROOT / ".venv" / "bin" / "python"
    if not python.is_file():
        print("Creating .venv…")
        subprocess.run([sys.executable, "-m", "venv", str(REPO_ROOT / ".venv")], check=True)
    if not skip_install:
        print("Installing the local application and dependencies…")
        subprocess.run(
            [str(python), "-m", "pip", "install", "-e", ".[dev]"],
            cwd=REPO_ROOT,
            check=True,
        )
    return python


def _already_serving(url: str) -> bool:
    try:
        with urlopen(url, timeout=3) as response:
            prefix = response.read(4096)
            return response.status == 200 and b"Frontier Lab Intelligence" in prefix
    except (OSError, URLError):
        return False


def _serve(python: Path, *, port: int, no_open: bool) -> int:
    url = f"http://127.0.0.1:{port}"
    if _already_serving(url):
        print(f"Frontier Lab Intelligence is already available at {url}")
        if not no_open:
            webbrowser.open(url)
        return 0

    env = dict(os.environ)
    env["FLI_READ_ONLY"] = "1"
    process = subprocess.Popen(
        [str(python), "-m", "fli.cli", "web", "--host", "127.0.0.1", "--port", str(port)],
        cwd=REPO_ROOT,
        env=env,
    )
    try:
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError("The local demo server exited before it became ready.")
            if _already_serving(url):
                print(f"Read-only reviewer demo: {url}")
                if not no_open:
                    webbrowser.open(url)
                return process.wait()
            time.sleep(0.1)
        raise RuntimeError("The local demo server did not become ready within 10 seconds.")
    except KeyboardInterrupt:
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--archive", type=Path, help="Use a local archive after verifying it against the manifest.")
    parser.add_argument("--force", action="store_true", help="Replace only the manifest's runtime-data paths.")
    parser.add_argument("--prepare-only", action="store_true", help="Restore data and install dependencies without starting the server.")
    parser.add_argument("--skip-install", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-open", action="store_true", help="Do not open the browser automatically.")
    parser.add_argument("--port", type=int, default=8797)
    args = parser.parse_args(argv)

    try:
        url = f"http://127.0.0.1:{args.port}"
        if not args.prepare_only and _already_serving(url):
            print(f"Frontier Lab Intelligence is already available at {url}")
            if not args.no_open:
                webbrowser.open(url)
            return 0
        manifest = _load_manifest(args.manifest, require_url=args.archive is None)
        if _marker_matches(manifest):
            print(f"Reviewer snapshot {manifest['release_id']} is already installed.")
        else:
            archive = args.archive.resolve() if args.archive else _download(manifest)
            if not archive.is_file():
                raise RuntimeError(f"Demo archive is missing: {archive}")
            if (
                archive.stat().st_size != int(manifest["archive"]["bytes"])
                or _sha256(archive) != str(manifest["archive"]["sha256"])
            ):
                raise RuntimeError("Local demo archive failed its size or SHA-256 check.")
            _install_snapshot(manifest, archive, force=args.force)
        python = _ensure_venv(skip_install=args.skip_install)
        if args.prepare_only:
            print("Reviewer demo is ready.")
            return 0
        return _serve(python, port=args.port, no_open=args.no_open)
    except (RuntimeError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
