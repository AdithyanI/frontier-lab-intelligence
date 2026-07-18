import asyncio
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from fli.insights.codex_app_server import CodexAppServerClient, CodexTaskError
from fli.insights.codex_app_server import _app_server_command


OBJECTIVE = "Publish the cited daily brief."


@dataclass(frozen=True)
class _SendStep:
    method: str
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    before_response: tuple[dict[str, Any], ...] = ()
    after_response: tuple[dict[str, Any], ...] = ()
    responds: bool = True
    on_send: Callable[[dict[str, Any]], None] | None = field(
        default=None, compare=False
    )


class _ScriptedTransport:
    def __init__(self, steps: list[_SendStep]) -> None:
        self._steps = deque(steps)
        self._incoming: deque[dict[str, Any]] = deque()
        self.sent: list[dict[str, Any]] = []
        self.transcript: list[str] = []
        self.closed = False

    async def send(self, message: dict[str, Any]) -> None:
        self.sent.append(message)
        method = str(message.get("method") or "")
        self.transcript.append(f"send:{method}")
        assert self._steps, f"unexpected send: {message}"
        step = self._steps.popleft()
        assert method == step.method
        if step.responds:
            assert "id" in message
        else:
            assert "id" not in message
        if step.on_send is not None:
            step.on_send(message)
        self._incoming.extend(step.before_response)
        if step.responds:
            response: dict[str, Any] = {"id": message["id"]}
            if step.error is not None:
                response["error"] = step.error
            else:
                response["result"] = step.result or {}
            self._incoming.append(response)
        self._incoming.extend(step.after_response)

    async def receive(self, timeout_seconds: float) -> dict[str, Any]:
        assert timeout_seconds > 0
        assert self._incoming, "script has no message for receive()"
        message = self._incoming.popleft()
        label = str(message.get("method") or f"response:{message.get('id')}")
        self.transcript.append(f"receive:{label}")
        return message

    async def close(self) -> None:
        self.closed = True

    def assert_exhausted(self) -> None:
        assert not self._steps
        assert not self._incoming


def _notification(method: str, params: dict[str, Any]) -> dict[str, Any]:
    return {"method": method, "params": params}


def _thread_result(
    repo_root: Path,
    *,
    thread_id: str = "thread-1",
    turns: list[dict[str, Any]] | None = None,
    status: str = "idle",
    model: str = "gpt-5.6-sol",
    reasoning_effort: str = "xhigh",
    service_tier: str | None = None,
) -> dict[str, Any]:
    return {
        "thread": {
            "id": thread_id,
            "cwd": str(repo_root),
            "turns": turns or [],
            "status": {"type": status},
        },
        "cwd": str(repo_root),
        "instructionSources": [str(repo_root / "AGENTS.md")],
        "model": model,
        "reasoningEffort": reasoning_effort,
        "serviceTier": service_tier,
    }


def _checkpoint_guard(
    checkpoints: list[dict[str, Any]], expected_statuses: list[str]
) -> Callable[[dict[str, Any]], None]:
    def guard(_message: dict[str, Any]) -> None:
        assert [item["status"] for item in checkpoints] == expected_statuses

    return guard


def _run_task(
    tmp_path: Path,
    transport: _ScriptedTransport,
    *,
    thread_id: str | None = None,
    checkpoints: list[dict[str, Any]] | None = None,
    model: str | None = None,
    reasoning_effort: str | None = None,
    service_tier: str | None = None,
) -> dict[str, Any]:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(exist_ok=True)
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text("# Test skill\n")

    async def transport_factory() -> _ScriptedTransport:
        return transport

    client = CodexAppServerClient(
        repo_root=repo_root,
        transport_factory=transport_factory,
        goal_poll_seconds=0.01,
    )
    return asyncio.run(
        client.run_task(
            name="Daily intelligence 2026-07-18",
            objective=OBJECTIVE,
            prompt="Use the prepared routing run.",
            skill_path=skill_path,
            timeout_seconds=1.0,
            model=model,
            reasoning_effort=reasoning_effort,
            service_tier=service_tier,
            thread_id=thread_id,
            checkpoint=checkpoints.append if checkpoints is not None else None,
        )
    )


def test_new_task_uses_safe_rpc_order_and_checkpoints_ids_immediately(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    checkpoints: list[dict[str, Any]] = []
    turn_completed = _notification(
        "turn/completed",
        {"turn": {"id": "turn-1", "status": "completed"}},
    )
    transport = _ScriptedTransport(
        [
            _SendStep("initialize", result={}),
            _SendStep("initialized", responds=False),
            _SendStep(
                "thread/start",
                result=_thread_result(repo_root),
                on_send=_checkpoint_guard(checkpoints, ["thread_starting"]),
            ),
            _SendStep(
                "thread/name/set",
                result={},
                on_send=_checkpoint_guard(
                    checkpoints, ["thread_starting", "thread_created"]
                ),
            ),
            _SendStep("thread/goal/get", result={"goal": None}),
            _SendStep("turn/start", result={"turn": {"id": "turn-1"}}),
            _SendStep(
                "thread/goal/set",
                result={"goal": {"status": "active"}},
                after_response=(turn_completed,),
                on_send=_checkpoint_guard(
                    checkpoints,
                    ["thread_starting", "thread_created", "turn_started"],
                ),
            ),
            _SendStep(
                "thread/goal/get", result={"goal": {"status": "complete"}}
            ),
        ]
    )

    result = _run_task(
        tmp_path, transport, checkpoints=checkpoints
    )

    request_methods = [
        message["method"] for message in transport.sent if "id" in message
    ]
    assert request_methods == [
        "initialize",
        "thread/start",
        "thread/name/set",
        "thread/goal/get",
        "turn/start",
        "thread/goal/set",
        "thread/goal/get",
    ]
    goal_get_sends = [
        index
        for index, item in enumerate(transport.transcript)
        if item == "send:thread/goal/get"
    ]
    assert transport.transcript.index("receive:turn/completed") < goal_get_sends[-1]
    assert [item["status"] for item in checkpoints] == [
        "thread_starting",
        "thread_created",
        "turn_started",
        "running",
        "finished",
    ]
    assert checkpoints[1]["thread_id"] == "thread-1"
    assert checkpoints[2]["turn_id"] == "turn-1"
    assert result == {
        "thread_id": "thread-1",
        "thread_name": "Daily intelligence 2026-07-18",
        "turn_id": "turn-1",
        "turn_status": "completed",
        "goal_status": "complete",
        "turns_started": 1,
        "requested_settings": {
            "model": None,
            "reasoning_effort": None,
            "service_tier": None,
        },
        "settings": {
            "model": "gpt-5.6-sol",
            "reasoning_effort": "xhigh",
            "service_tier": None,
        },
        "instruction_sources": [str(repo_root / "AGENTS.md")],
    }
    transport.assert_exhausted()
    assert transport.closed


def test_new_task_applies_explicit_model_effort_and_priority_tier(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    turn_completed = _notification(
        "turn/completed",
        {"turn": {"id": "turn-1", "status": "completed"}},
    )

    def assert_thread_start(message: dict[str, Any]) -> None:
        params = message["params"]
        assert params["model"] == "gpt-5.6-terra"
        assert params["serviceTier"] == "priority"
        assert "effort" not in params
        assert params["config"] == {"model_reasoning_effort": "ultra"}

    def assert_turn_start(message: dict[str, Any]) -> None:
        params = message["params"]
        assert params["model"] == "gpt-5.6-terra"
        assert params["effort"] == "ultra"
        assert params["serviceTier"] == "priority"

    transport = _ScriptedTransport(
        [
            _SendStep("initialize", result={}),
            _SendStep("initialized", responds=False),
            _SendStep(
                "thread/start",
                result=_thread_result(
                    repo_root,
                    model="gpt-5.6-terra",
                    reasoning_effort="ultra",
                    service_tier="priority",
                ),
                on_send=assert_thread_start,
            ),
            _SendStep("thread/name/set", result={}),
            _SendStep("thread/goal/get", result={"goal": None}),
            _SendStep(
                "turn/start",
                result={"turn": {"id": "turn-1"}},
                on_send=assert_turn_start,
            ),
            _SendStep(
                "thread/goal/set",
                result={"goal": {"status": "active"}},
                after_response=(turn_completed,),
            ),
            _SendStep("thread/goal/get", result={"goal": {"status": "complete"}}),
        ]
    )

    result = _run_task(
        tmp_path,
        transport,
        model="gpt-5.6-terra",
        reasoning_effort="ultra",
        service_tier="priority",
    )

    assert result["settings"] == {
        "model": "gpt-5.6-terra",
        "reasoning_effort": "ultra",
        "service_tier": "priority",
    }
    assert _app_server_command("codex") == (
        "codex",
        "app-server",
        "--stdio",
        "--enable",
        "goals",
    )
    transport.assert_exhausted()


def test_new_task_rejects_unapplied_reasoning_effort(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    transport = _ScriptedTransport(
        [
            _SendStep("initialize", result={}),
            _SendStep("initialized", responds=False),
            _SendStep(
                "thread/start",
                result=_thread_result(repo_root, reasoning_effort="xhigh"),
                on_send=lambda message: (
                    message["params"].get("config")
                    == {"model_reasoning_effort": "ultra"}
                    or pytest.fail("thread/start must request the reasoning override")
                ),
            ),
        ]
    )

    with pytest.raises(CodexTaskError) as raised:
        _run_task(tmp_path, transport, reasoning_effort="ultra")

    assert raised.value.code == "E_CODEX_SETTINGS_NOT_APPLIED"
    assert [message["method"] for message in transport.sent] == [
        "initialize",
        "initialized",
        "thread/start",
    ]
    transport.assert_exhausted()


def test_resume_validates_frozen_settings_without_overriding_changed_task(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    transport = _ScriptedTransport(
        [
            _SendStep("initialize", result={}),
            _SendStep("initialized", responds=False),
            _SendStep(
                "thread/resume",
                result=_thread_result(
                    repo_root,
                    thread_id="thread-existing",
                    model="gpt-5.6-sol",
                    reasoning_effort="ultra",
                    service_tier="priority",
                ),
                on_send=lambda message: (
                    message["params"] == {"threadId": "thread-existing"}
                    or pytest.fail("resume must not mutate thread settings")
                ),
            ),
        ]
    )

    with pytest.raises(CodexTaskError) as raised:
        _run_task(
            tmp_path,
            transport,
            thread_id="thread-existing",
            model="gpt-5.6-sol",
            reasoning_effort="xhigh",
            service_tier="priority",
        )

    assert raised.value.code == "E_CODEX_SETTINGS_MISMATCH"
    assert [message["method"] for message in transport.sent] == [
        "initialize",
        "initialized",
        "thread/resume",
    ]
    transport.assert_exhausted()


def test_resume_checks_goal_ownership_before_any_task_mutation(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    transport = _ScriptedTransport(
        [
            _SendStep("initialize", result={}),
            _SendStep("initialized", responds=False),
            _SendStep(
                "thread/resume",
                result=_thread_result(
                    repo_root,
                    thread_id="thread-reused",
                    status="idle",
                ),
            ),
            _SendStep(
                "thread/goal/get",
                result={
                    "goal": {
                        "status": "active",
                        "objective": "A different user-owned goal.",
                    }
                },
            ),
        ]
    )

    with pytest.raises(CodexTaskError) as raised:
        _run_task(tmp_path, transport, thread_id="thread-reused")

    assert raised.value.code == "E_CODEX_GOAL_MISMATCH"
    assert [message["method"] for message in transport.sent] == [
        "initialize",
        "initialized",
        "thread/resume",
        "thread/goal/get",
    ]
    transport.assert_exhausted()


def test_native_continuation_does_not_send_another_turn_start(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    first_turn_completed = _notification(
        "turn/completed",
        {"turn": {"id": "turn-1", "status": "completed"}},
    )
    second_turn_started = _notification(
        "turn/started",
        {"turn": {"id": "turn-2", "status": "inProgress"}},
    )
    second_turn_completed = _notification(
        "turn/completed",
        {"turn": {"id": "turn-2", "status": "completed"}},
    )
    transport = _ScriptedTransport(
        [
            _SendStep("initialize", result={}),
            _SendStep("initialized", responds=False),
            _SendStep("thread/start", result=_thread_result(repo_root)),
            _SendStep("thread/name/set", result={}),
            _SendStep("thread/goal/get", result={"goal": None}),
            _SendStep("turn/start", result={"turn": {"id": "turn-1"}}),
            _SendStep(
                "thread/goal/set",
                result={"goal": {"status": "active"}},
                after_response=(first_turn_completed,),
            ),
            _SendStep(
                "thread/goal/get",
                result={"goal": {"status": "active"}},
                before_response=(second_turn_started,),
                after_response=(second_turn_completed,),
            ),
            _SendStep(
                "thread/goal/get", result={"goal": {"status": "complete"}}
            ),
        ]
    )

    result = _run_task(tmp_path, transport)

    assert [message["method"] for message in transport.sent].count("turn/start") == 1
    assert result["turn_id"] == "turn-2"
    assert result["turn_status"] == "completed"
    assert result["goal_status"] == "complete"
    assert result["turns_started"] == 2
    transport.assert_exhausted()
    assert transport.closed


def test_resuming_active_goal_does_not_start_or_set_another_turn(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    turn_completed = _notification(
        "turn/completed",
        {"turn": {"id": "turn-existing", "status": "completed"}},
    )
    transport = _ScriptedTransport(
        [
            _SendStep("initialize", result={}),
            _SendStep("initialized", responds=False),
            _SendStep(
                "thread/resume",
                result=_thread_result(
                    repo_root,
                    thread_id="thread-existing",
                    turns=[{"id": "turn-existing", "status": "inProgress"}],
                    status="active",
                ),
            ),
            _SendStep(
                "thread/goal/get",
                result={"goal": {"status": "active", "objective": OBJECTIVE}},
                after_response=(turn_completed,),
            ),
            _SendStep(
                "thread/goal/get",
                result={"goal": {"status": "complete", "objective": OBJECTIVE}},
            ),
        ]
    )

    result = _run_task(tmp_path, transport, thread_id="thread-existing")

    sent_methods = [message["method"] for message in transport.sent]
    assert "thread/start" not in sent_methods
    assert "turn/start" not in sent_methods
    assert "thread/goal/set" not in sent_methods
    assert result["thread_id"] == "thread-existing"
    assert result["turn_id"] == "turn-existing"
    assert result["goal_status"] == "complete"
    assert result["turns_started"] == 1
    transport.assert_exhausted()
    assert transport.closed


def test_terminal_goal_refreshes_stale_turn_activity_from_persisted_thread(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    transport = _ScriptedTransport(
        [
            _SendStep("initialize", result={}),
            _SendStep("initialized", responds=False),
            _SendStep(
                "thread/resume",
                result=_thread_result(
                    repo_root,
                    thread_id="thread-existing",
                    turns=[{"id": "turn-interrupted", "status": "inProgress"}],
                    status="active",
                ),
            ),
            _SendStep(
                "thread/goal/get",
                result={"goal": {"status": "complete", "objective": OBJECTIVE}},
            ),
            _SendStep(
                "thread/read",
                result=_thread_result(
                    repo_root,
                    thread_id="thread-existing",
                    turns=[
                        {"id": "turn-interrupted", "status": "interrupted"},
                        {"id": "turn-continuation", "status": "completed"},
                    ],
                    status="idle",
                ),
            ),
        ]
    )

    result = _run_task(tmp_path, transport, thread_id="thread-existing")

    assert result["thread_id"] == "thread-existing"
    assert result["turn_id"] == "turn-continuation"
    assert result["turn_status"] == "completed"
    assert result["goal_status"] == "complete"
    assert result["turns_started"] == 2
    assert [message["method"] for message in transport.sent].count("thread/read") == 1
    transport.assert_exhausted()
    assert transport.closed


def test_resumed_task_without_goal_fails_without_starting_another_turn(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    transport = _ScriptedTransport(
        [
            _SendStep("initialize", result={}),
            _SendStep("initialized", responds=False),
            _SendStep(
                "thread/resume",
                result=_thread_result(
                    repo_root,
                    thread_id="thread-reused",
                    status="idle",
                ),
            ),
            _SendStep("thread/goal/get", result={"goal": None}),
        ]
    )

    with pytest.raises(CodexTaskError) as raised:
        _run_task(tmp_path, transport, thread_id="thread-reused")

    assert raised.value.code == "E_CODEX_GOAL_MISSING"
    assert "turn/start" not in [message["method"] for message in transport.sent]
    transport.assert_exhausted()
    assert transport.closed


def test_cwd_mismatch_fails_closed_and_closes_transport(tmp_path: Path) -> None:
    wrong_root = tmp_path / "wrong-repo"
    wrong_root.mkdir()
    transport = _ScriptedTransport(
        [
            _SendStep("initialize", result={}),
            _SendStep("initialized", responds=False),
            _SendStep("thread/start", result=_thread_result(wrong_root)),
        ]
    )

    with pytest.raises(CodexTaskError) as raised:
        _run_task(tmp_path, transport)

    assert raised.value.code == "E_CODEX_CWD_MISMATCH"
    assert raised.value.retryable is False
    transport.assert_exhausted()
    assert transport.closed


def test_rpc_error_is_stable_and_closes_transport(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    transport = _ScriptedTransport(
        [
            _SendStep("initialize", result={}),
            _SendStep("initialized", responds=False),
            _SendStep("thread/start", result=_thread_result(repo_root)),
            _SendStep(
                "thread/name/set",
                error={"code": -32601, "message": "method unavailable"},
            ),
        ]
    )

    with pytest.raises(CodexTaskError) as raised:
        _run_task(tmp_path, transport)

    assert raised.value.code == "E_CODEX_RPC"
    assert raised.value.message == "thread/name/set failed: method unavailable"
    assert raised.value.retryable is False
    transport.assert_exhausted()
    assert transport.closed


def test_discard_archived_task_clears_goal_before_permanent_delete(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    transport = _ScriptedTransport(
        [
            _SendStep("initialize", result={}),
            _SendStep("initialized", responds=False),
            _SendStep(
                "thread/unarchive",
                result={"thread": {"id": "obsolete-thread"}},
            ),
            _SendStep("thread/goal/get", result={"goal": {"status": "active"}}),
            _SendStep("thread/goal/clear", result={"cleared": True}),
            _SendStep("thread/delete", result={}),
        ]
    )

    async def transport_factory() -> _ScriptedTransport:
        return transport

    client = CodexAppServerClient(
        repo_root=repo_root,
        transport_factory=transport_factory,
    )
    result = asyncio.run(
        client.discard_task(thread_id="obsolete-thread", timeout_seconds=1.0)
    )

    assert result == {
        "thread_id": "obsolete-thread",
        "goal_cleared": True,
        "deleted": True,
    }
    assert [message["method"] for message in transport.sent] == [
        "initialize",
        "initialized",
        "thread/unarchive",
        "thread/goal/get",
        "thread/goal/clear",
        "thread/delete",
    ]
    transport.assert_exhausted()
    assert transport.closed
