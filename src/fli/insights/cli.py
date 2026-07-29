"""Machine-first CLI for the company-aware Investment Insight agent."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Callable
from uuid import uuid4

from openai import APIConnectionError, APITimeoutError, AuthenticationError

from fli.insights import company_context
from fli.insights import investment_agent
from fli.insights import investment_agent_runs
from fli.registry import classification as entity_kinds
from fli.routing import runs as routing_run_store


CLI_SCHEMA_VERSION = "1.0"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_json(value: Any, *, pretty: bool = False) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2 if pretty else None,
        sort_keys=True,
        separators=None if pretty else (",", ":"),
    )


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(routing_run_store.REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _meta(*, request_id: str, started: float) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "timestamp_utc": _now().isoformat(),
    }


def _success(
    command: str, data: dict[str, Any], *, request_id: str, started: float
) -> dict[str, Any]:
    return {
        "schema_version": CLI_SCHEMA_VERSION,
        "command": command,
        "status": "ok",
        "data": data,
        "error": None,
        "meta": _meta(request_id=request_id, started=started),
    }


def _error(
    command: str,
    *,
    code: str,
    message: str,
    retryable: bool,
    hint: str,
    request_id: str,
    started: float,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": CLI_SCHEMA_VERSION,
        "command": command,
        "status": "error",
        "data": data,
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "hint": hint,
        },
        "meta": _meta(request_id=request_id, started=started),
    }



class InvestmentAgentBatchIncomplete(RuntimeError):
    """A company-aware batch preserved its successes but some targets failed."""

    def __init__(self, result: dict[str, Any]):
        super().__init__("Investment agent batch completed with failed targets.")
        self.result = result


def _plain(payload: dict[str, Any]) -> str:
    if payload["status"] == "error":
        return f"{payload['error']['code']}: {payload['error']['message']}"
    data = payload["data"]
    if payload["command"] == "insights.contract":
        return _canonical_json(data, pretty=True)
    if payload["command"] in {
        "insights.summary",
        "insights.inspect",
        "insights.import-result",
        "insights.import-investment-trace",
        "insights.run-investment-agent",
    }:
        return _canonical_json(data, pretty=True)
    if payload["command"] == "insights.refresh":
        if payload["status"] == "error":
            return f"{payload['error']['code']}: {payload['error']['message']}"
        if data["dry_run"]:
            return (
                f"{data['refresh_id']} · {data['event_count']} Events · "
                f"{data['request_count']} requests · no model calls"
            )
        return (
            f"{data['refresh_id']} · {data['counts']['complete']}/"
            f"{data['counts']['requests']} complete · "
            f"{data['telemetry']['model_requests']} model requests · "
            f"${data['telemetry']['reported_cost_usd']:.6f}"
        )
    lines = [
        f"event {data['event_id']} · {data['day']} · Feed rank {data['feed_rank']}",
        f"model {data['model']} · dump {data['dump_dir']}",
    ]
    for evaluation in data["evaluations"]:
        result = evaluation["result"]
        lines.append(
            f"{evaluation['audience']}: {result['decision']} — "
            f"{result['suppression_reason'] or result['summary']}"
        )
    return "\n".join(lines)



def _add_output_flags(parser: argparse.ArgumentParser) -> None:
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true", help="Emit stable JSON (default).")
    mode.add_argument("--plain", action="store_true", help="Emit a compact inspection view.")
    parser.add_argument("--no-input", action="store_true", help="Never prompt (always honored).")




def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fli insights",
        description="Run, import, and audit company-aware Investment Insights.",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    contract = sub.add_parser(
        "contract", help="Inspect the live prompt identity and output schema."
    )
    _add_output_flags(contract)

    run = sub.add_parser(
        "run-investment-agent",
        help=(
            "Analyze the highest-ranked current Investment-routed Developments "
            "with the company-aware agent, persist full audit traces, and "
            "import successful results."
        ),
    )
    run.add_argument("--through", required=True)
    run.add_argument("--days", type=int, default=1)
    run.add_argument(
        "--top-ranked",
        type=int,
        default=investment_agent.DEFAULT_TOP_RANKED,
        help="Number of Investment-routed Developments to analyze per day.",
    )
    run.add_argument(
        "--rank",
        type=int,
        help=(
            "Run only this absolute daily rank on every requested day; the "
            "Development must have a current positive Investment route."
        ),
    )
    run.add_argument("--model", default=investment_agent.DEFAULT_MODEL)
    run.add_argument("--reasoning-effort", default=investment_agent.DEFAULT_EFFORT)
    run.add_argument("--workers", type=int, default=investment_agent.DEFAULT_WORKERS)
    run.add_argument("--api-base", default=investment_agent.DEFAULT_API_BASE)
    run.add_argument(
        "--trace-root", type=Path, default=investment_agent.DEFAULT_TRACE_ROOT
    )
    run.add_argument("--db", type=Path, default=investment_agent_runs.DEFAULT_DB)
    _add_output_flags(run)

    imported = sub.add_parser(
        "import-investment-trace",
        help="Persist one validated company-aware Investment agent trace.",
    )
    imported.add_argument("--trace", type=Path, required=True)
    imported.add_argument("--db", type=Path, default=investment_agent_runs.DEFAULT_DB)
    _add_output_flags(imported)

    summary = sub.add_parser("summary", help="Inspect aggregate durable run state.")
    summary.add_argument("--db", type=Path, default=investment_agent_runs.DEFAULT_DB)
    _add_output_flags(summary)

    company = sub.add_parser(
        "company-context",
        help="Inspect one reusable BIT company lens by name, ticker, or alias.",
    )
    company.add_argument("--company", required=True)
    _add_output_flags(company)

    universe = sub.add_parser(
        "company-universe",
        help="Inspect the complete auditable company context read model.",
    )
    _add_output_flags(universe)
    return parser


def contract_payload() -> dict[str, Any]:
    """Report the live prompt identity the production loop binds to each run."""
    return {
        "schema_version": CLI_SCHEMA_VERSION,
        "prompt_version": investment_agent.PROMPT_VERSION,
        "prompt_cache_key": investment_agent.PROMPT_CACHE_KEY,
        "prompt_path": _display_path(investment_agent.PROMPT_PATH),
        "model": investment_agent.DEFAULT_MODEL,
        "reasoning_effort": investment_agent.DEFAULT_EFFORT,
        "max_model_turns": investment_agent.MAX_MODEL_TURNS,
        "max_unique_memos": investment_agent.MAX_UNIQUE_MEMOS,
        "store_schema_version": investment_agent_runs.STORE_SCHEMA_VERSION,
        "read_schema_version": investment_agent_runs.READ_SCHEMA_VERSION,
    }


def main(
    argv: list[str] | None = None,
    *,
    client_factory: Callable[[], Any] = entity_kinds.create_litellm_client,
) -> int:
    args = _parser().parse_args(argv)
    started = time.monotonic()
    request_id = str(uuid4())
    command = f"insights.{args.action}"
    exit_code = 0
    try:
        if args.action == "contract":
            data = contract_payload()
        elif args.action == "run-investment-agent":
            data = investment_agent.run_range(
                through=args.through,
                days=args.days,
                top_ranked=args.top_ranked,
                rank=args.rank,
                model=args.model,
                effort=args.reasoning_effort,
                workers=args.workers,
                api_base=args.api_base,
                trace_root=args.trace_root,
                db_path=args.db,
                client_factory=client_factory,
            )
            if not data["complete"]:
                raise InvestmentAgentBatchIncomplete(data)
        elif args.action == "import-investment-trace":
            data = investment_agent_runs.import_trace(args.trace, db_path=args.db)
        elif args.action == "summary":
            if not args.db.is_file():
                raise FileNotFoundError(args.db)
            data = {
                "db": _display_path(args.db),
                **investment_agent_runs.summary_payload(args.db),
            }
        elif args.action == "company-context":
            data = company_context.company_context(args.company)
        else:
            data = company_context.investment_company_universe_payload()
        payload = _success(command, data, request_id=request_id, started=started)
    except InvestmentAgentBatchIncomplete as exc:
        exit_code = 1
        payload = _error(
            command,
            code="E_PARTIAL_FAILURE",
            message=str(exc),
            retryable=True,
            hint=(
                "Rerun the identical command; completed runs are reused and "
                "failed ranks retry. A day publishes only when every requested "
                "rank succeeds."
            ),
            request_id=request_id,
            started=started,
            data=exc.result,
        )
    except KeyboardInterrupt:
        exit_code = 5
        payload = _error(
            command,
            code="E_INTERRUPTED",
            message="Investment agent run was interrupted.",
            retryable=True,
            hint="Run the same command again; each run writes a new trace.",
            request_id=request_id,
            started=started,
        )
    except company_context.CompanyProfileNotFound as exc:
        exit_code = 2
        payload = _error(
            command,
            code="E_INVALID_INPUT",
            message=str(exc),
            retryable=False,
            hint="Use a canonical company name, ticker, or documented alias.",
            request_id=request_id,
            started=started,
        )
    except (FileNotFoundError, sqlite3.Error, ValueError) as exc:
        exit_code = 2
        payload = _error(
            command,
            code="E_INVALID_INPUT",
            message=str(exc),
            retryable=False,
            hint="Check the requested day, rank, database path, and routing lineage.",
            request_id=request_id,
            started=started,
        )
    except AuthenticationError as exc:
        exit_code = 3
        payload = _error(
            command,
            code="E_AUTH",
            message=str(exc),
            retryable=False,
            hint="Repair the shared LiteLLM credential file and retry.",
            request_id=request_id,
            started=started,
        )
    except (APITimeoutError, TimeoutError) as exc:
        exit_code = 5
        payload = _error(
            command,
            code="E_TIMEOUT",
            message=str(exc),
            retryable=True,
            hint="Retry the same command; the loop owns bounded transient retries.",
            request_id=request_id,
            started=started,
        )
    except APIConnectionError as exc:
        exit_code = 4
        payload = _error(
            command,
            code="E_DEPENDENCY_UNAVAILABLE",
            message=str(exc),
            retryable=True,
            hint="Check the shared LiteLLM endpoint and retry.",
            request_id=request_id,
            started=started,
        )
    except Exception as exc:
        exit_code = 1
        payload = _error(
            command,
            code="E_EXECUTION",
            message=str(exc),
            retryable=True,
            hint="Inspect the written trace and retry after the dependency is stable.",
            request_id=request_id,
            started=started,
        )
    print(_plain(payload) if getattr(args, "plain", False) else _canonical_json(payload))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
