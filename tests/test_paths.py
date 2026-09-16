import json
from pathlib import Path
import plistlib
import subprocess

import pytest

from fli import paths


@pytest.fixture(autouse=True)
def isolated_storage_config(monkeypatch):
    monkeypatch.delenv("FLI_STORAGE_CONFIG", raising=False)
    paths._configured_root.cache_clear()
    yield
    paths._configured_root.cache_clear()


def _write_config(repo_root, data_root, **values):
    config = repo_root / "data" / "storage.local.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        json.dumps({"version": 1, "data_root": str(data_root), **values})
    )
    return config


@pytest.mark.parametrize("data_class", ["raw", "derived", "archive"])
def test_external_data_keeps_logical_references_after_relocation(
    tmp_path, data_class
):
    repo_root = tmp_path / "checkout"
    external = tmp_path / "production"
    external.mkdir()
    _write_config(repo_root, external)
    physical = external / data_class / "evidence" / "snapshot.db"
    physical.parent.mkdir(parents=True)
    physical.write_bytes(b"preserved evidence")
    logical = f"data/{data_class}/evidence/snapshot.db"

    assert paths.data_path(
        data_class, "evidence", "snapshot.db", repo_root=repo_root
    ) == physical
    assert paths.resolve_reference(logical, repo_root=repo_root) == physical
    assert paths.reference(physical, repo_root=repo_root) == logical
    assert paths.resolve_reference(logical, repo_root=repo_root).read_bytes() == (
        b"preserved evidence"
    )
    assert not (repo_root / "data" / data_class).exists()


@pytest.mark.parametrize(
    "relative", ["fli.db", "registry/entities.json", "following/manifest.json", "digg/rank.json"]
)
def test_tracked_inputs_stay_in_checkout_with_external_storage(tmp_path, relative):
    repo_root = tmp_path / "checkout"
    external = tmp_path / "production"
    external.mkdir()
    _write_config(repo_root, external)
    tracked = repo_root / "data" / relative

    assert paths.data_path(relative, repo_root=repo_root) == tracked
    assert paths.resolve_reference(f"data/{relative}", repo_root=repo_root) == tracked
    assert paths.reference(tracked, repo_root=repo_root) == f"data/{relative}"


def test_clean_checkout_and_explicit_portable_override_use_checkout_data(
    tmp_path, monkeypatch
):
    repo_root = tmp_path / "checkout"
    assert paths.storage_root(repo_root=repo_root) == repo_root / "data"
    _write_config(repo_root, tmp_path / "unavailable-production")
    monkeypatch.setenv("FLI_STORAGE_CONFIG", "-")

    assert paths.data_path("derived", "feed.db", repo_root=repo_root) == (
        repo_root / "data" / "derived" / "feed.db"
    )


def test_explicit_missing_configuration_does_not_fall_back(tmp_path, monkeypatch):
    repo_root = tmp_path / "checkout"
    monkeypatch.setenv("FLI_STORAGE_CONFIG", str(tmp_path / "missing.json"))

    with pytest.raises(FileNotFoundError):
        paths.data_path("raw", "evidence.db", repo_root=repo_root)
    assert not (repo_root / "data" / "raw").exists()


def test_missing_configured_data_root_does_not_create_local_replacement(tmp_path):
    repo_root = tmp_path / "checkout"
    unavailable = tmp_path / "unmounted-production"
    _write_config(repo_root, unavailable)

    with pytest.raises(ValueError, match="existing absolute directory"):
        paths.data_path("raw", "evidence.db", repo_root=repo_root)
    assert not unavailable.exists()
    assert not (repo_root / "data" / "raw").exists()


def test_volume_identity_mismatch_fails_closed(tmp_path, monkeypatch):
    repo_root = tmp_path / "checkout"
    mount = tmp_path / "production-volume"
    external = mount / "Services" / "frontier-lab-intelligence"
    external.mkdir(parents=True)
    _write_config(
        repo_root,
        external,
        volume_mount=str(mount),
        volume_uuid="expected-volume-uuid",
    )
    monkeypatch.setattr(Path, "is_mount", lambda path: path == mount)
    calls = []

    def diskutil(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(
            args, 0, stdout=plistlib.dumps({"VolumeUUID": "different-volume-uuid"})
        )

    monkeypatch.setattr(paths.subprocess, "run", diskutil)

    with pytest.raises(ValueError, match="UUID does not match"):
        paths.storage_root(repo_root=repo_root)
    assert calls == [
        (
            ["/usr/sbin/diskutil", "info", "-plist", str(mount)],
            {"check": True, "capture_output": True, "timeout": 10},
        )
    ]
    assert not (repo_root / "data" / "raw").exists()


@pytest.mark.parametrize("relative", ["../outside.db", "raw/../../outside.db", "/raw/outside.db"])
def test_data_paths_reject_traversal_and_absolute_paths(tmp_path, relative):
    with pytest.raises(ValueError, match="remain inside data"):
        paths.data_path(relative, repo_root=tmp_path)
