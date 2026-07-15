from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/build-log.py"


def entry(title: str, *, day: str = "2026-07-15") -> dict[str, str]:
    return {
        "date": day,
        "title": title,
        "intent": f"Intent for {title}",
        "action": f"Action for {title}",
        "evidence": f"Evidence for {title}",
        "impact_next": f"Impact for {title}",
        "tools_spend": "Local validation; $0.",
    }


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module_name = f"build_log_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    build_log_dir = tmp_path / "docs/references/build-log"
    archive_dir = build_log_dir / "archive"
    archive_dir.mkdir(parents=True)
    current = build_log_dir / "current.jsonl"
    current.touch()
    markdown = tmp_path / "docs/references/build-log.md"
    markdown.write_text(
        "# Build Log\n\n## Build Timeline\n\nOld timeline.\n\n"
        "## Learning Notes\n\nPreserved notes.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "BUILD_LOG_DIR", build_log_dir)
    monkeypatch.setattr(module, "ARCHIVE_DIR", archive_dir)
    monkeypatch.setattr(module, "CURRENT", current)
    monkeypatch.setattr(module, "MD", markdown)
    monkeypatch.setattr(module, "LOCK", tmp_path / "tmp/build-log.lock")
    return module


def add_args(value: dict[str, str]) -> list[str]:
    return [
        "add",
        "--date",
        value["date"],
        "--title",
        value["title"],
        "--intent",
        value["intent"],
        "--action",
        value["action"],
        "--evidence",
        value["evidence"],
        "--impact-next",
        value["impact_next"],
        "--tools-spend",
        value["tools_spend"],
    ]


def test_add_emits_json_and_exact_retry_is_idempotent(client, capsys: pytest.CaptureFixture[str]):
    value = entry("Milestone complete")

    assert client.main(add_args(value)) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["schema_version"] == "1.0"
    assert first["command"] == "build-log add"
    assert first["status"] == "ok"
    assert first["error"] is None
    assert first["data"]["appended"] is True

    assert client.main(add_args(value)) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["data"]["appended"] is False
    assert len(client.CURRENT.read_text(encoding="utf-8").splitlines()) == 1


def test_usage_failure_is_structured_and_nonzero(client, capsys: pytest.CaptureFixture[str]):
    assert client.main(["add", "--title", "Incomplete"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["command"] == "build-log add"
    assert result["status"] == "error"
    assert result["data"] is None
    assert result["error"]["code"] == "E_USAGE"
    assert result["error"]["retryable"] is False

    oversized = entry("Too verbose")
    oversized["action"] = "x" * 4_001
    assert client.main(add_args(oversized)) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["error"]["code"] == "E_ENTRY_TOO_LARGE"
    assert client.CURRENT.read_text(encoding="utf-8") == ""


def test_recent_search_validate_and_render_are_bounded(client, capsys: pytest.CaptureFixture[str]):
    archive = client.ARCHIVE_DIR / "000001-2026-07-14.jsonl"
    archive.write_text(json.dumps(entry("Archived routing", day="2026-07-14")) + "\n", encoding="utf-8")
    client.CURRENT.write_text(
        json.dumps(entry("Current routing")) + "\n" + json.dumps(entry("UI polish")) + "\n",
        encoding="utf-8",
    )

    assert client.main(["recent", "--limit", "2"]) == 0
    recent = json.loads(capsys.readouterr().out)
    assert [item["title"] for item in recent["data"]["entries"]] == ["Current routing", "UI polish"]

    assert client.main(["search", "routing", "--limit", "1"]) == 0
    search = json.loads(capsys.readouterr().out)
    assert search["data"]["match_count"] == 2
    assert [item["title"] for item in search["data"]["entries"]] == ["Current routing"]

    assert client.main(["validate"]) == 0
    validation = json.loads(capsys.readouterr().out)
    assert validation["data"]["entry_count"] == 3
    assert validation["data"]["source_count"] == 2

    assert client.main(["render"]) == 0
    rendered = json.loads(capsys.readouterr().out)
    assert rendered["data"]["changed"] is True
    markdown = client.MD.read_text(encoding="utf-8")
    assert markdown.index("Archived routing") < markdown.index("Current routing")
    assert "| Date | Outcome / intent |" in markdown
    assert "**Archived routing**" in markdown
    assert "Preserved notes." in markdown

    assert client.main(["recent", "--limit", "51"]) == 2
    failure = json.loads(capsys.readouterr().out)
    assert failure["error"]["code"] == "E_INVALID_LIMIT"


def test_add_rotates_large_current_shard_under_lock(client, monkeypatch: pytest.MonkeyPatch, capsys):
    client.CURRENT.write_text(json.dumps(entry("Before rotation")) + "\n", encoding="utf-8")
    monkeypatch.setattr(client, "CURRENT_MAX_BYTES", 1)

    assert client.main(add_args(entry("After rotation"))) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["rotated_to"].endswith("000001-2026-07-15.jsonl")
    assert [record.entry["title"] for record in client.load_records()] == [
        "Before rotation",
        "After rotation",
    ]


def test_plain_mode_is_explicit_operator_output(client, capsys: pytest.CaptureFixture[str]):
    client.CURRENT.write_text(json.dumps(entry("Visible summary")) + "\n", encoding="utf-8")

    assert client.main(["--plain", "recent", "--limit", "1"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "2026-07-15 — Visible summary\n"
    assert captured.err == ""

    assert client.main(["--plain", "search", "missing"]) == 0
    assert capsys.readouterr().out == "No matching build-log entries.\n"

    assert client.main(["search", "--", "--plain"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"


def test_rotated_archives_keep_explicit_sequence_order(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(client, "CURRENT_MAX_BYTES", 1)
    client.CURRENT.write_text(json.dumps(entry("First shard")) + "\n", encoding="utf-8")
    first = client.rotate_current_if_needed()
    assert first and first.name == "000001-2026-07-15.jsonl"

    client.CURRENT.write_text(
        json.dumps(entry("Second shard start"))
        + "\n"
        + json.dumps(entry("Second shard end", day="2026-07-16"))
        + "\n",
        encoding="utf-8",
    )
    second = client.rotate_current_if_needed()
    assert second and second.name == "000002-2026-07-15--2026-07-16.jsonl"
    assert [record.entry["title"] for record in client.load_records()] == [
        "First shard",
        "Second shard start",
        "Second shard end",
    ]
