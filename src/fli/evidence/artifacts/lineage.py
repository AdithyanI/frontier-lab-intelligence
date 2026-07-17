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
    """Return root-account posts in the root conversation, never reactions."""

    root_id = str(envelope["root"]["post_id"])
    root = feed.execute(
        """SELECT post_id, author_x_id, conversation_id
           FROM feed_post
           WHERE run_id = ? AND provider = 'twitterapi_io' AND post_id = ?""",
        (feed_run_id, root_id),
    ).fetchone()
    if root is None:
        return {root_id}
    root_author_x_id = str(root["author_x_id"] or "")
    if not root_author_x_id:
        return {root_id}

    conversation_id = str(root["conversation_id"] or root_id)
    rows = feed.execute(
        """SELECT post_id
           FROM feed_post
           WHERE run_id = ? AND provider = 'twitterapi_io'
             AND author_x_id = ? AND post_type = 'reply'
             AND conversation_id = ?""",
        (feed_run_id, root_author_x_id, conversation_id),
    ).fetchall()
    return {root_id, *(str(row["post_id"]) for row in rows)}
