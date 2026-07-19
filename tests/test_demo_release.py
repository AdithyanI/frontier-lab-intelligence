from importlib import util
from pathlib import Path
import sys
import zipfile

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _demo_module():
    spec = util.spec_from_file_location("fli_demo_script", REPO_ROOT / "scripts/demo.py")
    assert spec and spec.loader
    module = util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_tracked_demo_manifest_is_complete_and_content_addressed():
    demo = _demo_module()
    manifest = demo._load_manifest(REPO_ROOT / "data/demo-release.json")

    archive = manifest["archive"]
    assert len(archive["sha256"]) == 64
    assert archive["sha256"] in archive["url"]
    assert archive["bytes"] > 0
    assert manifest["contents"]["raw_provider_responses_included"] is False
    assert manifest["contents"]["delivery_credentials_included"] is False


def test_demo_archive_rejects_path_traversal(tmp_path):
    demo = _demo_module()
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../outside.txt", "unsafe")

    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(RuntimeError, match="Unsafe path"):
            demo._safe_members(archive, ["data/derived/example"])
