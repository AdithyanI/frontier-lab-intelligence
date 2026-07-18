"""Minimal Codex App Server client for persisted daily-intelligence tasks."""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


TERMINAL_GOAL_STATUSES = {
    "blocked",
    "budgetLimited",
    "cleared",
    "complete",
    "paused",
    "usageLimited",
}
APP_SERVER_STREAM_LIMIT_BYTES = 16 * 1024 * 1024


class CodexTaskError(RuntimeError):
    """Stable failure raised by the App Server boundary."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        hint: str,
        retryable: bool,
        exit_code: int,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.retryable = retryable
        self.exit_code = exit_code


class AppServerTransport(Protocol):
    async def send(self, message: dict[str, Any]) -> None: ...

    async def receive(self, timeout_seconds: float) -> dict[str, Any]: ...

    async def close(self) -> None: ...


class StdioAppServerTransport:
    """One short-lived newline-delimited JSON-RPC App Server process."""

    def __init__(self, process: asyncio.subprocess.Process) -> None:
        self.process = process
        self.stderr_lines: deque[str] = deque(maxlen=30)
        self._stderr_task = asyncio.create_task(self._drain_stderr())

    @classmethod
    async def open(
        cls,
        *,
        repo_root: Path,
        codex_binary: str = "codex",
    ) -> StdioAppServerTransport:
        process = await asyncio.create_subprocess_exec(
            codex_binary,
            "app-server",
            "--stdio",
            "--enable",
            "goals",
            cwd=str(repo_root),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=APP_SERVER_STREAM_LIMIT_BYTES,
        )
        return cls(process)

    async def _drain_stderr(self) -> None:
        if self.process.stderr is None:
            return
        while line := await self.process.stderr.readline():
            self.stderr_lines.append(line.decode(errors="replace").rstrip())

    async def send(self, message: dict[str, Any]) -> None:
        if self.process.stdin is None or self.process.returncode is not None:
            raise CodexTaskError(
                code="E_CODEX_EXITED",
                message="Codex App Server exited before the request was sent.",
                hint="Inspect the App Server stderr and resume the same daily run.",
                retryable=True,
                exit_code=4,
            )
        payload = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
        self.process.stdin.write(f"{payload}\n".encode())
        await self.process.stdin.drain()

    async def receive(self, timeout_seconds: float) -> dict[str, Any]:
        if self.process.stdout is None:
            raise CodexTaskError(
                code="E_CODEX_PROTOCOL",
                message="Codex App Server stdout is unavailable.",
                hint="Verify the installed Codex CLI and resume the same daily run.",
                retryable=True,
                exit_code=4,
            )
        try:
            line = await asyncio.wait_for(
                self.process.stdout.readline(), timeout=timeout_seconds
            )
        except TimeoutError:
            raise
        except ValueError as error:
            raise CodexTaskError(
                code="E_CODEX_MESSAGE_TOO_LARGE",
                message="Codex App Server emitted a message above the stream limit.",
                hint="Resume the persisted task after increasing the client stream limit.",
                retryable=True,
                exit_code=4,
            ) from error
        if not line:
            return_code = await self.process.wait()
            detail = " | ".join(self.stderr_lines)
            raise CodexTaskError(
                code="E_CODEX_EXITED",
                message=f"Codex App Server exited with code {return_code}.",
                hint=(
                    f"Resume the same daily run after inspecting: {detail}"
                    if detail
                    else "Resume the same daily run and inspect Codex CLI diagnostics."
                ),
                retryable=True,
                exit_code=4,
            )
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise CodexTaskError(
                code="E_CODEX_PROTOCOL",
                message="Codex App Server returned invalid JSON.",
                hint="Upgrade or repair the local Codex CLI, then resume the same run.",
                retryable=False,
                exit_code=4,
            ) from error
        if not isinstance(value, dict):
            raise CodexTaskError(
                code="E_CODEX_PROTOCOL",
                message="Codex App Server returned a non-object message.",
                hint="Upgrade or repair the local Codex CLI, then resume the same run.",
                retryable=False,
                exit_code=4,
            )
        return value

    async def close(self) -> None:
        if self.process.stdin is not None and not self.process.stdin.is_closing():
            self.process.stdin.close()
        if self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except TimeoutError:
                self.process.kill()
                await self.process.wait()
        if not self._stderr_task.done():
            self._stderr_task.cancel()
        await asyncio.gather(self._stderr_task, return_exceptions=True)


TransportFactory = Callable[[], Awaitable[AppServerTransport]]
ProgressCallback = Callable[[str, str], None]
CheckpointCallback = Callable[[dict[str, Any]], None]


@dataclass
class _TaskState:
    thread_id: str | None = None
    turn_id: str | None = None
    turn_status: str | None = None
    goal_status: str | None = None
    turn_in_progress: bool = False
    turns_started: int = 0


class CodexAppServerClient:
    """Create or resume one named goal-backed Codex task."""

    def __init__(
        self,
        *,
        repo_root: Path,
        transport_factory: TransportFactory | None = None,
        codex_binary: str = "codex",
        goal_poll_seconds: float = 15.0,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.codex_binary = codex_binary
        self.transport_factory = transport_factory
        self.goal_poll_seconds = goal_poll_seconds
        self._next_request_id = 1

    async def _open_transport(self) -> AppServerTransport:
        if self.transport_factory is not None:
            return await self.transport_factory()
        return await StdioAppServerTransport.open(
            repo_root=self.repo_root,
            codex_binary=self.codex_binary,
        )

    def _request_id(self) -> int:
        value = self._next_request_id
        self._next_request_id += 1
        return value

    @staticmethod
    def _remaining(deadline: float) -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise CodexTaskError(
                code="E_CODEX_TIMEOUT",
                message="The Codex daily task exceeded its timeout.",
                hint="Resume the same daily run; its persisted thread id is retained.",
                retryable=True,
                exit_code=5,
            )
        return remaining

    async def _handle_message(
        self,
        transport: AppServerTransport,
        message: dict[str, Any],
        state: _TaskState,
        *,
        progress: ProgressCallback | None,
    ) -> None:
        method = str(message.get("method") or "")
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        if "id" in message and method:
            if state.thread_id and state.turn_id and state.turn_in_progress:
                await transport.send(
                    {
                        "method": "turn/interrupt",
                        "id": self._request_id(),
                        "params": {
                            "threadId": state.thread_id,
                            "turnId": state.turn_id,
                        },
                    }
                )
            await transport.send(
                {
                    "id": message["id"],
                    "error": {
                        "code": -32000,
                        "message": (
                            "The FLI daily runner is non-interactive and cannot "
                            f"satisfy server request {method}."
                        ),
                    },
                }
            )
            raise CodexTaskError(
                code="E_CODEX_INTERACTION_REQUIRED",
                message=f"Codex requested unsupported interaction {method}.",
                hint="Open the persisted task in Codex Desktop or adjust the task instructions.",
                retryable=False,
                exit_code=2,
            )
        if method == "turn/started":
            turn = params.get("turn") if isinstance(params.get("turn"), dict) else {}
            state.turn_id = str(turn.get("id") or state.turn_id or "") or None
            state.turn_status = str(turn.get("status") or "inProgress")
            state.turn_in_progress = True
            state.turns_started += 1
            if progress:
                progress("codex_turn", state.turn_id or "started")
        elif method == "turn/completed":
            turn = params.get("turn") if isinstance(params.get("turn"), dict) else {}
            state.turn_id = str(turn.get("id") or state.turn_id or "") or None
            state.turn_status = str(turn.get("status") or "completed")
            state.turn_in_progress = False
            if progress:
                progress("codex_turn", state.turn_status)
        elif method == "thread/goal/updated":
            goal = params.get("goal") if isinstance(params.get("goal"), dict) else {}
            state.goal_status = str(goal.get("status") or state.goal_status or "") or None
            if progress and state.goal_status:
                progress("codex_goal", state.goal_status)
        elif method == "thread/goal/cleared":
            state.goal_status = "cleared"
        elif method == "thread/status/changed":
            status = params.get("status") if isinstance(params.get("status"), dict) else {}
            if status.get("type") == "idle":
                state.turn_in_progress = False

    @staticmethod
    def _hydrate_thread_state(state: _TaskState, thread: dict[str, Any]) -> None:
        turns = thread.get("turns") if isinstance(thread.get("turns"), list) else []
        state.turns_started = len(turns)
        if turns and isinstance(turns[-1], dict):
            latest = turns[-1]
            state.turn_id = str(latest.get("id") or "") or None
            state.turn_status = str(latest.get("status") or "") or None
        status = thread.get("status") if isinstance(thread.get("status"), dict) else {}
        state.turn_in_progress = status.get("type") == "active"

    async def _refresh_thread_state(
        self,
        transport: AppServerTransport,
        state: _TaskState,
        *,
        deadline: float,
        progress: ProgressCallback | None,
    ) -> None:
        """Replace notification-derived activity with persisted thread state."""
        result = await self._request(
            transport,
            "thread/read",
            {"threadId": state.thread_id, "includeTurns": True},
            state,
            deadline=deadline,
            progress=progress,
        )
        thread = result.get("thread") if isinstance(result.get("thread"), dict) else {}
        returned_thread_id = str(thread.get("id") or "")
        if not returned_thread_id or returned_thread_id != state.thread_id:
            raise CodexTaskError(
                code="E_CODEX_PROTOCOL",
                message="App Server did not return the expected persisted task state.",
                hint="Inspect the persisted task in Codex Desktop before retrying.",
                retryable=False,
                exit_code=4,
            )
        self._hydrate_thread_state(state, thread)

    async def _request(
        self,
        transport: AppServerTransport,
        method: str,
        params: dict[str, Any],
        state: _TaskState,
        *,
        deadline: float,
        progress: ProgressCallback | None,
    ) -> dict[str, Any]:
        request_id = self._request_id()
        await transport.send({"method": method, "id": request_id, "params": params})
        while True:
            message = await transport.receive(self._remaining(deadline))
            if message.get("id") == request_id and not message.get("method"):
                if isinstance(message.get("error"), dict):
                    error = message["error"]
                    raise CodexTaskError(
                        code="E_CODEX_RPC",
                        message=f"{method} failed: {error.get('message', 'unknown error')}",
                        hint="Inspect the installed App Server protocol and resume the same run.",
                        retryable=False,
                        exit_code=4,
                    )
                result = message.get("result")
                return result if isinstance(result, dict) else {}
            await self._handle_message(
                transport,
                message,
                state,
                progress=progress,
            )

    async def _start_turn(
        self,
        transport: AppServerTransport,
        state: _TaskState,
        *,
        prompt: str,
        skill_path: Path,
        deadline: float,
        progress: ProgressCallback | None,
    ) -> dict[str, Any]:
        result = await self._request(
            transport,
            "turn/start",
            {
                "threadId": state.thread_id,
                "input": [
                    {
                        "type": "skill",
                        "name": "fli-daily-intelligence",
                        "path": str(skill_path.resolve()),
                    },
                    {"type": "text", "text": prompt},
                ],
            },
            state,
            deadline=deadline,
            progress=progress,
        )
        turn = result.get("turn") if isinstance(result.get("turn"), dict) else {}
        state.turn_id = str(turn.get("id") or state.turn_id or "") or None
        state.turn_status = str(turn.get("status") or "inProgress")
        state.turn_in_progress = True
        if state.turns_started == 0:
            state.turns_started = 1
        return result

    async def discard_task(
        self,
        *,
        thread_id: str,
        timeout_seconds: float = 60.0,
    ) -> dict[str, Any]:
        """Clear and permanently delete one known archived, idle task."""
        if not thread_id.strip():
            raise ValueError("thread_id must not be empty")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        deadline = time.monotonic() + timeout_seconds
        state = _TaskState(thread_id=thread_id)
        transport = await self._open_transport()
        try:
            await self._request(
                transport,
                "initialize",
                {
                    "clientInfo": {
                        "name": "fli_daily_runner",
                        "title": "FLI Daily Runner",
                        "version": "1.0.0",
                    },
                    "capabilities": None,
                },
                state,
                deadline=deadline,
                progress=None,
            )
            await transport.send({"method": "initialized", "params": {}})
            await self._request(
                transport,
                "thread/unarchive",
                {"threadId": thread_id},
                state,
                deadline=deadline,
                progress=None,
            )
            goal_result = await self._request(
                transport,
                "thread/goal/get",
                {"threadId": thread_id},
                state,
                deadline=deadline,
                progress=None,
            )
            goal = goal_result.get("goal")
            goal_cleared = False
            if isinstance(goal, dict):
                clear_result = await self._request(
                    transport,
                    "thread/goal/clear",
                    {"threadId": thread_id},
                    state,
                    deadline=deadline,
                    progress=None,
                )
                if clear_result.get("cleared") is not True:
                    raise CodexTaskError(
                        code="E_CODEX_GOAL_NOT_CLEARED",
                        message="Codex did not confirm that the obsolete goal was cleared.",
                        hint="Inspect the task in Codex Desktop before deleting it.",
                        retryable=False,
                        exit_code=4,
                    )
                goal_cleared = True
            await self._request(
                transport,
                "thread/delete",
                {"threadId": thread_id},
                state,
                deadline=deadline,
                progress=None,
            )
            return {
                "thread_id": thread_id,
                "goal_cleared": goal_cleared,
                "deleted": True,
            }
        finally:
            await transport.close()

    async def run_task(
        self,
        *,
        name: str,
        objective: str,
        prompt: str,
        skill_path: Path,
        timeout_seconds: float,
        thread_id: str | None = None,
        progress: ProgressCallback | None = None,
        checkpoint: CheckpointCallback | None = None,
    ) -> dict[str, Any]:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not skill_path.is_file():
            raise FileNotFoundError(skill_path)
        deadline = time.monotonic() + timeout_seconds
        state = _TaskState(thread_id=thread_id)
        transport = await self._open_transport()
        instruction_sources: list[str] = []
        try:
            await self._request(
                transport,
                "initialize",
                {
                    "clientInfo": {
                        "name": "fli_daily_runner",
                        "title": "FLI Daily Runner",
                        "version": "1.0.0",
                    },
                    "capabilities": None,
                },
                state,
                deadline=deadline,
                progress=progress,
            )
            await transport.send({"method": "initialized", "params": {}})

            if state.thread_id:
                opened = await self._request(
                    transport,
                    "thread/resume",
                    {"threadId": state.thread_id},
                    state,
                    deadline=deadline,
                    progress=progress,
                )
            else:
                if checkpoint:
                    checkpoint(
                        {
                            "thread_id": None,
                            "turn_id": None,
                            "goal_status": None,
                            "status": "thread_starting",
                        }
                    )
                opened = await self._request(
                    transport,
                    "thread/start",
                    {
                        "cwd": str(self.repo_root),
                        "ephemeral": False,
                        "serviceName": "fli_daily_intelligence",
                        "approvalPolicy": "never",
                    },
                    state,
                    deadline=deadline,
                    progress=progress,
                )
            thread = opened.get("thread") if isinstance(opened.get("thread"), dict) else {}
            state.thread_id = str(thread.get("id") or state.thread_id or "") or None
            if not state.thread_id:
                raise CodexTaskError(
                    code="E_CODEX_PROTOCOL",
                    message="App Server did not return a thread id.",
                    hint="Inspect the installed App Server protocol and retry.",
                    retryable=False,
                    exit_code=4,
                )
            if checkpoint:
                checkpoint(
                    {
                        "thread_id": state.thread_id,
                        "turn_id": None,
                        "goal_status": None,
                        "status": "thread_resumed" if thread_id else "thread_created",
                    }
                )
            returned_cwd = Path(str(opened.get("cwd") or thread.get("cwd") or ""))
            if not returned_cwd.is_absolute() or returned_cwd.resolve() != self.repo_root:
                raise CodexTaskError(
                    code="E_CODEX_CWD_MISMATCH",
                    message="App Server created the task in a different workspace.",
                    hint="Inspect Codex configuration before retrying this daily run.",
                    retryable=False,
                    exit_code=4,
                )
            self._hydrate_thread_state(state, thread)
            raw_sources = opened.get("instructionSources")
            if isinstance(raw_sources, list):
                instruction_sources = [str(item) for item in raw_sources]
            await self._request(
                transport,
                "thread/name/set",
                {"threadId": state.thread_id, "name": name},
                state,
                deadline=deadline,
                progress=progress,
            )
            goal_result = await self._request(
                transport,
                "thread/goal/get",
                {"threadId": state.thread_id},
                state,
                deadline=deadline,
                progress=progress,
            )
            goal = (
                goal_result.get("goal")
                if isinstance(goal_result.get("goal"), dict)
                else None
            )
            if thread_id and goal is None:
                raise CodexTaskError(
                    code="E_CODEX_GOAL_MISSING",
                    message="The persisted Codex task no longer has its daily goal.",
                    hint=(
                        "Do not restart work in this task. Inspect the exact imported "
                        "editorial run or start a new date with a fresh task."
                    ),
                    retryable=False,
                    exit_code=4,
                )
            if thread_id and goal is not None:
                returned_objective = str(goal.get("objective") or "")
                if returned_objective != objective:
                    raise CodexTaskError(
                        code="E_CODEX_GOAL_MISMATCH",
                        message="The persisted Codex task now owns a different goal.",
                        hint=(
                            "Leave the reused task untouched and inspect the durable "
                            "editorial run for the original workspace."
                        ),
                        retryable=False,
                        exit_code=4,
                    )
            if goal is None and not state.turn_in_progress:
                await self._start_turn(
                    transport,
                    state,
                    prompt=f"Goal:\n{objective}\n\nExecution context:\n{prompt}",
                    skill_path=skill_path,
                    deadline=deadline,
                    progress=progress,
                )
                if checkpoint:
                    checkpoint(
                        {
                            "thread_id": state.thread_id,
                            "thread_name": name,
                            "turn_id": state.turn_id,
                            "goal_status": None,
                            "status": "turn_started",
                        }
                    )
            if goal is None:
                goal_result = await self._request(
                    transport,
                    "thread/goal/set",
                    {
                        "threadId": state.thread_id,
                        "objective": objective,
                        "status": "active",
                    },
                    state,
                    deadline=deadline,
                    progress=progress,
                )
                goal = goal_result.get("goal") if isinstance(goal_result.get("goal"), dict) else {}
            state.goal_status = str((goal or {}).get("status") or "active")
            if checkpoint:
                checkpoint(
                    {
                        "thread_id": state.thread_id,
                        "thread_name": name,
                        "goal_status": state.goal_status,
                        "turn_id": state.turn_id,
                        "status": "running",
                    }
                )
            while (
                state.goal_status not in TERMINAL_GOAL_STATUSES
                or state.turn_in_progress
            ):
                if (
                    state.goal_status in TERMINAL_GOAL_STATUSES
                    and state.turn_in_progress
                ):
                    await self._refresh_thread_state(
                        transport,
                        state,
                        deadline=deadline,
                        progress=progress,
                    )
                    if not state.turn_in_progress:
                        break
                wait_seconds = min(
                    self._remaining(deadline), self.goal_poll_seconds
                )
                try:
                    message = await transport.receive(wait_seconds)
                except TimeoutError:
                    goal_result = await self._request(
                        transport,
                        "thread/goal/get",
                        {"threadId": state.thread_id},
                        state,
                        deadline=deadline,
                        progress=progress,
                    )
                    current_goal = (
                        goal_result.get("goal")
                        if isinstance(goal_result.get("goal"), dict)
                        else {}
                    )
                    state.goal_status = str(
                        current_goal.get("status") or state.goal_status or "active"
                    )
                    if state.goal_status in TERMINAL_GOAL_STATUSES:
                        if state.turn_in_progress:
                            await self._refresh_thread_state(
                                transport,
                                state,
                                deadline=deadline,
                                progress=progress,
                            )
                        if not state.turn_in_progress:
                            break
                        continue
                    if not state.turn_in_progress:
                        raise CodexTaskError(
                            code="E_CODEX_STALLED",
                            message="The Codex goal remained active while its task was idle.",
                            hint="Open the persisted task in Desktop; do not create a replacement task.",
                            retryable=True,
                            exit_code=5,
                        )
                    continue
                await self._handle_message(
                    transport,
                    message,
                    state,
                    progress=progress,
                )
                if message.get("method") == "turn/completed":
                    goal_result = await self._request(
                        transport,
                        "thread/goal/get",
                        {"threadId": state.thread_id},
                        state,
                        deadline=deadline,
                        progress=progress,
                    )
                    current_goal = (
                        goal_result.get("goal")
                        if isinstance(goal_result.get("goal"), dict)
                        else {}
                    )
                    state.goal_status = str(
                        current_goal.get("status") or state.goal_status or "active"
                    )
                if state.turn_status == "failed" and state.goal_status not in TERMINAL_GOAL_STATUSES:
                    raise CodexTaskError(
                        code="E_CODEX_TURN_FAILED",
                        message="The Codex daily task turn failed.",
                        hint="Resume the same daily run; the persisted thread id is retained.",
                        retryable=True,
                        exit_code=4,
                    )

            result = {
                "thread_id": state.thread_id,
                "thread_name": name,
                "turn_id": state.turn_id,
                "turn_status": state.turn_status,
                "goal_status": state.goal_status,
                "turns_started": state.turns_started,
                "instruction_sources": instruction_sources,
            }
            if checkpoint:
                checkpoint({**result, "status": "finished"})
            return result
        finally:
            await transport.close()
