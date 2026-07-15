"""Primary-author evidence boundaries for Feed envelopes."""

from __future__ import annotations

import sqlite3
from typing import Any


def frozen_primary_post_ids(envelope: dict[str, Any]) -> set[str]:
    """Return the root and explicitly frozen same-author reply continuations."""

    root_id = str((envelope.get("root") or {}).get("post_id") or "")
    if not root_id:
        raise ValueError("envelope root is missing post_id")
    post_ids = {root_id}
    for raw in envelope.get("related_posts") or []:
        item = dict(raw)
        if (
            item.get("same_author_as_root") is True
            and str(item.get("relation") or "") == "reply"
            and item.get("post_id")
        ):
            post_ids.add(str(item["post_id"]))
    return post_ids


def verified_primary_post_ids(
    feed: sqlite3.Connection,
    *,
    feed_run_id: str,
    envelope: dict[str, Any],
) -> set[str]:
    """Verify a root author's reply chain using stable account and parent IDs."""

    frozen_ids = frozen_primary_post_ids(envelope)
    root_id = str(envelope["root"]["post_id"])
    placeholders = ",".join("?" for _ in frozen_ids)
    rows = feed.execute(
        f"""SELECT post_id, author_x_id, post_type, in_reply_to_post_id
            FROM feed_post
            WHERE run_id = ? AND provider = 'twitterapi_io'
              AND post_id IN ({placeholders})""",
        (feed_run_id, *sorted(frozen_ids)),
    ).fetchall()
    by_id = {str(row["post_id"]): row for row in rows}
    root = by_id.get(root_id)
    if root is None:
        return {root_id}
    root_author_x_id = str(root["author_x_id"] or "")
    if not root_author_x_id:
        return {root_id}

    allowed = {root_id}
    pending = frozen_ids - allowed
    while pending:
        newly_allowed = {
            post_id
            for post_id in pending
            if (
                (post := by_id.get(post_id)) is not None
                and str(post["author_x_id"] or "") == root_author_x_id
                and str(post["post_type"] or "") == "reply"
                and str(post["in_reply_to_post_id"] or "") in allowed
            )
        }
        if not newly_allowed:
            break
        allowed.update(newly_allowed)
        pending.difference_update(newly_allowed)
    return allowed
