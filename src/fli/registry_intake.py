"""Authenticated operator intake for one X profile.

The web layer owns authentication. This module owns duplicate-safe profile
materialization, the normal evidence screen, direct admission, and the durable
audit row shared by API and future operator tooling.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Literal
from urllib import parse

from fli import entity_kinds, registry, registry_evaluation, sources

Mode = Literal["screen", "direct"]
DEFAULT_MIN_FOLLOWERS = entity_kinds.DEFAULT_MIN_FOLLOWERS
DEFAULT_POST_LIMIT = entity_kinds.DEFAULT_POST_LIMIT


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_x_profile(value: str) -> tuple[str, str]:
    """Return a normalized handle and canonical X URL."""
    raw = value.strip()
    if not raw:
        raise ValueError("Enter an X profile URL or handle.")
    if raw.startswith("@") or "/" not in raw:
        handle = sources.normalize_x_handle(raw)
        return handle, f"https://x.com/{handle}"

    candidate = raw if "://" in raw else f"https://{raw}"
    parsed = parse.urlparse(candidate)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    if parsed.scheme != "https" or host not in {"x.com", "twitter.com"}:
        raise ValueError("Use an HTTPS x.com profile URL or an X handle.")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 1:
        raise ValueError("Use a profile URL such as https://x.com/handle.")
    handle = sources.normalize_x_handle(parts[0])
    return handle, f"https://x.com/{handle}"


def _existing_entity(conn: sqlite3.Connection, handle: str) -> sqlite3.Row | None:
    return conn.execute(
        """SELECT e.id, e.kind,
                  CASE WHEN rejected.entity_id IS NULL THEN 'active' ELSE 'rejected' END
                    AS registry_state
           FROM entities e
           JOIN entity_channels ec ON ec.entity_id = e.id
           JOIN channels c ON c.id = ec.channel_id
           LEFT JOIN entity_registry_rejections rejected ON rejected.entity_id = e.id
           WHERE c.kind = 'x' AND lower(c.key) = ?
           LIMIT 1""",
        (handle.lower(),),
    ).fetchone()


def _start_audit(
    conn: sqlite3.Connection,
    *,
    handle: str,
    profile_url: str,
    mode: Mode,
    reason: str | None,
) -> int:
    registry.ensure_schema(conn)
    cursor = conn.execute(
        """INSERT INTO entity_registry_intake_audit
           (handle, profile_url, mode, override_reason, status, requested_at)
           VALUES (?, ?, ?, ?, 'running', ?)""",
        (handle, profile_url, mode, reason, _now()),
    )
    conn.commit()
    return int(cursor.lastrowid)


def _finish_audit(
    conn: sqlite3.Connection,
    audit_id: int,
    *,
    entity_id: int | None,
    outcome: str,
    registry_decision: str | None,
    registry_decision_reason: str | None,
    kind: str | None,
    kind_reason: str | None,
    model: str | None = None,
    reasoning_effort: str | None = None,
    prompt_version: str | None = None,
    response_id: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    reported_cost_usd: float | None = None,
) -> None:
    conn.execute(
        """UPDATE entity_registry_intake_audit
           SET entity_id = ?, status = 'completed', outcome = ?,
               registry_decision = ?, registry_decision_reason = ?,
               kind = ?, kind_reason = ?, model = ?, reasoning_effort = ?,
               prompt_version = ?, response_id = ?, input_tokens = ?,
               output_tokens = ?, reported_cost_usd = ?, completed_at = ?
           WHERE id = ?""",
        (
            entity_id,
            outcome,
            registry_decision,
            registry_decision_reason,
            kind,
            kind_reason,
            model,
            reasoning_effort,
            prompt_version,
            response_id,
            input_tokens,
            output_tokens,
            reported_cost_usd,
            _now(),
            audit_id,
        ),
    )
    conn.commit()


def _fail_audit(conn: sqlite3.Connection, audit_id: int, error: Exception) -> None:
    conn.execute(
        """UPDATE entity_registry_intake_audit
           SET status = 'failed', error_code = ?, error_message = ?, completed_at = ?
           WHERE id = ?""",
        (type(error).__name__, str(error), _now(), audit_id),
    )
    conn.commit()


def _result(
    *,
    audit_id: int,
    handle: str,
    mode: Mode,
    outcome: str,
    entity_id: int | None,
    registry_decision: str,
    decision_reason: str,
    kind: str | None,
    kind_reason: str | None,
    followers_count: int | None,
) -> dict[str, Any]:
    return {
        "audit_id": audit_id,
        "handle": handle,
        "mode": mode,
        "outcome": outcome,
        "entity_id": entity_id,
        "registry_decision": registry_decision,
        "decision_reason": decision_reason,
        "kind": kind,
        "kind_reason": kind_reason,
        "followers_count": followers_count,
    }


def _llm_client(value: Any) -> Any:
    return value() if callable(value) and not hasattr(value, "responses") else value


def _post_client(value: Any) -> Any:
    return value() if callable(value) and not hasattr(value, "fetch_user") else value


def run_intake(
    conn: sqlite3.Connection,
    *,
    profile: str,
    mode: Mode,
    reason: str | None,
    llm_client: Any,
    post_client: Any,
    min_followers: int = DEFAULT_MIN_FOLLOWERS,
    post_limit: int = DEFAULT_POST_LIMIT,
) -> dict[str, Any]:
    """Run one operator-requested profile through screen or direct admission."""
    if mode not in {"screen", "direct"}:
        raise ValueError("mode must be screen or direct")
    normalized_reason = " ".join((reason or "").split()) or None
    if mode == "direct" and (normalized_reason is None or len(normalized_reason) < 8):
        raise ValueError("Direct admission requires a specific audit reason.")
    handle, profile_url = normalize_x_profile(profile)
    audit_id = _start_audit(
        conn,
        handle=handle,
        profile_url=profile_url,
        mode=mode,
        reason=normalized_reason,
    )
    try:
        existing = _existing_entity(conn, handle)
        if existing is not None and existing["registry_state"] == "active":
            decision_reason = "This X profile already belongs to an active Registry entity."
            _finish_audit(
                conn,
                audit_id,
                entity_id=int(existing["id"]),
                outcome="existing",
                registry_decision="existing",
                registry_decision_reason=decision_reason,
                kind=str(existing["kind"]),
                kind_reason=None,
            )
            return _result(
                audit_id=audit_id,
                handle=handle,
                mode=mode,
                outcome="existing",
                entity_id=int(existing["id"]),
                registry_decision="existing",
                decision_reason=decision_reason,
                kind=str(existing["kind"]),
                kind_reason=None,
                followers_count=None,
            )

        if mode == "direct":
            lifecycle = entity_kinds.run_x_account_lifecycle(
                conn,
                handle=handle,
                client=_llm_client(llm_client),
                post_client=_post_client(post_client),
                min_followers=0,
                post_limit=post_limit,
            )
            entity_id = lifecycle.get("entity_id")
            if lifecycle.get("outcome") == "rejected":
                decision = "remove"
                outcome = "rejected"
                decision_reason = str(lifecycle.get("reason") or "Profile rejected.")
                kind = None
                kind_reason = None
            else:
                if entity_id is None:
                    raise RuntimeError("Direct admission completed without an entity ID.")
                registry.clear_rejection(conn, entity_id=int(entity_id))
                conn.commit()
                decision = "manual_keep"
                outcome = "active"
                decision_reason = normalized_reason or "Manual operator admission."
                row = conn.execute(
                    "SELECT kind FROM entities WHERE id = ?", (entity_id,)
                ).fetchone()
                kind = str(row["kind"])
                kind_reason = lifecycle.get("reason")
            _finish_audit(
                conn,
                audit_id,
                entity_id=int(entity_id) if entity_id is not None else None,
                outcome=outcome,
                registry_decision=decision,
                registry_decision_reason=decision_reason,
                kind=kind,
                kind_reason=kind_reason,
                model=(lifecycle.get("workflow") or {}).get("model"),
                reasoning_effort=(lifecycle.get("workflow") or {}).get(
                    "reasoning_effort"
                ),
                prompt_version=(lifecycle.get("workflow") or {}).get(
                    "prompt_version"
                ),
                input_tokens=int((lifecycle.get("workflow") or {}).get("input_tokens") or 0),
                output_tokens=int((lifecycle.get("workflow") or {}).get("output_tokens") or 0),
                reported_cost_usd=(lifecycle.get("workflow") or {}).get(
                    "reported_cost_usd"
                ),
            )
            return _result(
                audit_id=audit_id,
                handle=handle,
                mode=mode,
                outcome=outcome,
                entity_id=int(entity_id) if entity_id is not None else None,
                registry_decision=decision,
                decision_reason=decision_reason,
                kind=kind,
                kind_reason=kind_reason,
                followers_count=lifecycle.get("followers_count"),
            )

        resolved_post_client = _post_client(post_client)
        provider_profile = resolved_post_client.fetch_user(username=handle)
        materialized = sources.persist_x_profile(conn, profile=provider_profile)
        conn.commit()
        entity_id = int(materialized["entity_id"])
        followers_count = sources.profile_followers_count(provider_profile)
        if followers_count is None:
            raise ValueError("The provider profile did not include a follower count.")

        if sources.is_protected_profile(provider_profile):
            decision_reason = entity_kinds.PROTECTED_ACCOUNT_REASON
            registry.reject_entity(
                conn,
                entity_id=entity_id,
                reason_code=entity_kinds.PROTECTED_ACCOUNT_REASON_CODE,
                reason=decision_reason,
                source=sources.PROVIDER,
                evidence_url=profile_url,
            )
            conn.commit()
            _finish_audit(
                conn,
                audit_id,
                entity_id=entity_id,
                outcome="rejected",
                registry_decision="remove",
                registry_decision_reason=decision_reason,
                kind=str(materialized["entity_kind"]),
                kind_reason=None,
            )
            return _result(
                audit_id=audit_id,
                handle=handle,
                mode=mode,
                outcome="rejected",
                entity_id=entity_id,
                registry_decision="remove",
                decision_reason=decision_reason,
                kind=str(materialized["entity_kind"]),
                kind_reason=None,
                followers_count=followers_count,
            )

        if followers_count < min_followers:
            decision_reason = (
                f"The X account has {followers_count:,} followers, below the current "
                f"{min_followers:,}-follower intake floor."
            )
            registry.reject_entity(
                conn,
                entity_id=entity_id,
                reason_code="below_follower_floor",
                reason=decision_reason,
                source="manual_registry_intake",
                evidence_url=profile_url,
            )
            conn.commit()
            _finish_audit(
                conn,
                audit_id,
                entity_id=entity_id,
                outcome="rejected",
                registry_decision="remove",
                registry_decision_reason=decision_reason,
                kind=str(materialized["entity_kind"]),
                kind_reason=None,
            )
            return _result(
                audit_id=audit_id,
                handle=handle,
                mode=mode,
                outcome="rejected",
                entity_id=entity_id,
                registry_decision="remove",
                decision_reason=decision_reason,
                kind=str(materialized["entity_kind"]),
                kind_reason=None,
                followers_count=followers_count,
            )

        recent_posts = resolved_post_client.fetch_recent_authored_posts(
            username=handle,
            limit=post_limit,
            profile=provider_profile,
        )
        entity_input = registry_evaluation.EvaluationInput(
            entity_id=entity_id,
            handle=handle,
            display_name=str(provider_profile.get("name") or f"@{handle}"),
            bio=str(provider_profile.get("description") or "") or None,
            profile_url=profile_url,
            recent_posts=tuple(recent_posts),
        )
        evaluation = registry_evaluation.evaluate_one(
            _llm_client(llm_client),
            entity_input,
            run=f"manual-intake-{audit_id}",
        )
        decision = str(evaluation["registry_decision"])
        outcome = "active" if decision == "keep" else "rejected"
        conn.execute(
            "UPDATE entities SET kind = ?, updated_at = ? WHERE id = ?",
            (evaluation["kind"], _now(), entity_id),
        )
        if decision == "keep":
            registry.clear_rejection(conn, entity_id=entity_id)
        else:
            registry.reject_entity(
                conn,
                entity_id=entity_id,
                reason_code=f"registry_evaluation_{decision}",
                reason=evaluation["registry_decision_reason"],
                source=registry_evaluation.PROMPT_VERSION,
                evidence_url=profile_url,
            )
        conn.commit()
        _finish_audit(
            conn,
            audit_id,
            entity_id=entity_id,
            outcome=outcome,
            registry_decision=decision,
            registry_decision_reason=evaluation["registry_decision_reason"],
            kind=evaluation["kind"],
            kind_reason=evaluation["kind_reason"],
            model=evaluation["model"],
            reasoning_effort=evaluation["reasoning_effort"],
            prompt_version=evaluation["prompt_version"],
            response_id=evaluation["response_id"],
            input_tokens=evaluation["input_tokens"],
            output_tokens=evaluation["output_tokens"],
            reported_cost_usd=evaluation["reported_cost_usd"],
        )
        return _result(
            audit_id=audit_id,
            handle=handle,
            mode=mode,
            outcome=outcome,
            entity_id=entity_id,
            registry_decision=decision,
            decision_reason=evaluation["registry_decision_reason"],
            kind=evaluation["kind"],
            kind_reason=evaluation["kind_reason"],
            followers_count=followers_count,
        )
    except Exception as error:
        _fail_audit(conn, audit_id, error)
        raise
