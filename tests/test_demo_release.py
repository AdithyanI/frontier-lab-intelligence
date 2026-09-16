from importlib import util
import json
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


@pytest.mark.parametrize("arguments", [[], ["--prepare-only", "--force"]])
def test_demo_rejects_external_production_checkout_before_any_work(
    tmp_path, monkeypatch, capsys, arguments
):
    demo = _demo_module()
    checkout = tmp_path / "checkout"
    data = checkout / "data"
    data.mkdir(parents=True)
    external = tmp_path / "production"
    external.mkdir()
    evidence = external / "preserved-evidence.txt"
    evidence.write_text("Keep the production corpus intact.")
    config = data / "storage.local.json"
    config.write_text(json.dumps({"version": 1, "data_root": str(external)}))
    config_before = config.read_bytes()
    monkeypatch.delenv("FLI_STORAGE_CONFIG", raising=False)
    monkeypatch.setattr(demo, "REPO_ROOT", checkout)
    monkeypatch.setattr(sys, "path", list(sys.path))

    def unexpected_work(*args, **kwargs):
        pytest.fail("The production guard must run before any demo work.")

    for name in (
        "_already_serving", "_load_manifest", "_download", "_install_snapshot",
        "_ensure_venv", "_serve",
    ):
        monkeypatch.setattr(demo, name, unexpected_work)

    assert demo.main(arguments) == 1
    assert "Use a clean checkout for the reviewer demo" in capsys.readouterr().err
    assert config.read_bytes() == config_before
    assert list(data.iterdir()) == [config]
    assert evidence.read_text() == "Keep the production corpus intact."
    assert list(external.iterdir()) == [evidence]
