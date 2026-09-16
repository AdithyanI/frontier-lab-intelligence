"""Logical data references shared by local checkouts and external storage.

Tracked inputs stay under the checkout's data/. Only raw, derived, and archive
use the configured data root. Stored references remain data/<class>/..., so
moving physical storage does not change evidence identity or provenance.
"""

from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
import plistlib
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTERNAL_CLASSES = frozenset({"raw", "derived", "archive"})


@lru_cache(maxsize=8)
def _configured_root(config_path: Path) -> Path:
    config = json.loads(config_path.read_text())
    if config.get("version") != 1:
        raise ValueError(f"Unsupported storage configuration: {config_path}")
    root = Path(config["data_root"]).expanduser()
    if not root.is_absolute() or not root.is_dir():
        raise ValueError(f"Configured data root must be an existing absolute directory: {root}")
    mount, expected_uuid = config.get("volume_mount"), config.get("volume_uuid")
    if bool(mount) != bool(expected_uuid):
        raise ValueError("Storage volume_mount and volume_uuid must be configured together")
    if mount:
        volume = Path(mount)
        if not volume.is_mount() or not root.resolve().is_relative_to(volume.resolve()):
            raise ValueError(f"Storage volume is not mounted at the configured location: {volume}")
        result = subprocess.run(
            ["/usr/sbin/diskutil", "info", "-plist", str(volume)],
            check=True, capture_output=True, timeout=10,
        )
        actual_uuid = plistlib.loads(result.stdout).get("VolumeUUID", "")
        if actual_uuid.lower() != str(expected_uuid).lower():
            raise ValueError(f"Storage volume UUID does not match: {volume}")
    return root.resolve()


def storage_root(*, repo_root: Path = REPO_ROOT) -> Path:
    """Load once per process; configured but unavailable storage fails closed.

    FLI_STORAGE_CONFIG selects a config file; '-' explicitly selects checkout
    storage for isolated tests and reviewer demos. No config means a normal
    portable checkout. Changing config requires restarting the process.
    """
    override = os.environ.get("FLI_STORAGE_CONFIG")
    if override == "-":
        return repo_root.resolve() / "data"
    config = Path(override).expanduser() if override else repo_root / "data/storage.local.json"
    if not override and not config.exists():
        return repo_root.resolve() / "data"
    return _configured_root(config.resolve())


def data_path(*parts: str, repo_root: Path = REPO_ROOT) -> Path:
    relative = Path(*parts)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("Data paths must name a class and remain inside data/")
    root = storage_root(repo_root=repo_root) if relative.parts[0] in EXTERNAL_CLASSES else repo_root / "data"
    return root / relative


def resolve_reference(value: str | Path, *, repo_root: Path = REPO_ROOT) -> Path:
    """Resolve a logical reference without searching alternate locations."""
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    if path.parts and path.parts[0] == "data":
        return data_path(*path.parts[1:], repo_root=repo_root).resolve()
    return (repo_root / path).resolve()


def reference(value: str | Path, *, repo_root: Path = REPO_ROOT) -> str:
    """Serialize relocated files using the same stable logical data reference."""
    path = Path(value).resolve()
    root = storage_root(repo_root=repo_root)
    if path.is_relative_to(root):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] in EXTERNAL_CLASSES:
            return (Path("data") / relative).as_posix()
    if path.is_relative_to(repo_root.resolve()):
        return path.relative_to(repo_root.resolve()).as_posix()
    return str(path)
