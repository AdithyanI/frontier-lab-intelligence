"""Digg seed-graph extraction.

Digg's Tech rankings expose ranked X accounts and per-profile "top followers"
in rendered HTML. This module keeps the extraction intentionally shallow:
produce reviewable candidate nodes and edges, not a final registry.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

USER_AGENT = "fli/0.1 (research prototype; contact: local)"
DIGG_BASE = "https://digg.com"
RANKINGS_URL = f"{DIGG_BASE}/tech/x/rankings"
FOLLOWERS_PAGE_SIZE = 50


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def _get_json(url: str) -> Any:
    return json.loads(_get(url))


def _normalize(raw_html: str) -> str:
    text = html.unescape(raw_html)
    text = text.replace('\\"', '"')
    text = text.replace("\\u0026", "&")
    text = text.replace("\\n", " ")
    return text


def _react_stream_payload(raw_html: str) -> str:
    """Decode Next/React flight stream chunks embedded in script tags."""
    chunks: list[str] = []
    for match in re.finditer(
        r"self\.__next_f\.push\((\[.*?\])\)</script>",
        raw_html,
        flags=re.S,
    ):
        try:
            payload = json.loads(html.unescape(match.group(1)))
        except json.JSONDecodeError:
            continue
        if len(payload) > 1 and isinstance(payload[1], str):
            chunks.append(payload[1])
    return "".join(chunks)


def _json_array_after(text: str, key: str) -> list[dict[str, Any]]:
    start = text.find(key)
    if start < 0:
        return []
    start += len(key) - 1
    level = 0
    end = None
    in_string = False
    escaped = False
    for index, char in enumerate(text[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "[":
            level += 1
        elif char == "]":
            level -= 1
            if level == 0:
                end = index + 1
                break
    if end is None:
        return []
    return json.loads(text[start:end])


def _clean(fragment: str) -> str:
    fragment = re.sub(r"<!--.*?-->", "", fragment, flags=re.S)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    fragment = html.unescape(fragment)
    return " ".join(fragment.split())


def _first(pattern: str, text: str, default: str | None = None) -> str | None:
    match = re.search(pattern, text, flags=re.S)
    return match.group(1) if match else default


def _to_int(value: str | None) -> int | None:
    if not value:
        return None
    return int(value.replace(",", ""))


def _to_float(value: str | None) -> float | None:
    if not value:
        return None
    return float(value.replace(",", ""))


def _x_id(segment: str) -> str | None:
    return _first(r"/authors/(\d+)/avatar-", segment)


def _split_ranking_cards(text: str) -> list[str]:
    marker = '<div class="group relative"><a aria-label="Open '
    parts = text.split(marker)
    return [marker + part for part in parts[1:]]


def parse_rankings(raw_html: str) -> list[dict[str, Any]]:
    """Parse the initial Digg Tech ranking rows from rendered HTML."""
    stream_entries = _json_array_after(_react_stream_payload(raw_html), '"entries":[')
    if stream_entries:
        top_score = stream_entries[0].get("score") or 1
        return [_ranking_from_entry(entry, top_score=top_score) for entry in stream_entries]

    text = _normalize(raw_html)
    rows: list[dict[str, Any]] = []
    for segment in _split_ranking_cards(text):
        profile_username = _first(r'href="/u/x/([^"]+)"', segment)
        x_username = _first(r'href="https://x\.com/([^"]+)"', segment)
        rank = _to_int(
            _first(r'data-slot="ranked-avatar-rank"[^>]*>([0-9,]+)</span>', segment)
        )
        display_name = _first(r"<h2[^>]*>(.*?)</h2>", segment)
        bio = _first(r"<p[^>]*line-clamp-2[^>]*>(.*?)</p>", segment)
        role = _first(r'title="View ([^"]+) rankings"', segment)
        cohort = _first(r'title="#\d+ in the ([^"]+) cohort"', segment)
        ranked_followers = _to_int(
            _first(
                r'<span class="font-semibold text-foreground">([0-9,]+)</span>'
                r'<span class="text-muted-foreground">(?:\s|<!--.*?-->)*'
                r"Tech ranked followers</span>",
                segment,
            )
        )
        gravity = _to_float(
            _first(
                r'<span class="font-semibold text-foreground">([0-9.]+)</span>'
                r'<span class="text-muted-foreground">\s*gravity</span>',
                segment,
            )
        )
        if not profile_username or not rank or not display_name:
            continue
        rows.append(
            {
                "rank": rank,
                "username": x_username or profile_username,
                "digg_profile_username": profile_username,
                "display_name": _clean(display_name),
                "role": role,
                "cohort": cohort,
                "tech_ranked_followers": ranked_followers,
                "gravity": gravity,
                "bio": _clean(bio or ""),
                "x_id": _x_id(segment),
                "digg_url": f"{DIGG_BASE}/u/x/{profile_username}",
                "x_url": f"https://x.com/{x_username or profile_username}",
            }
        )
    return rows


def _ranking_from_entry(entry: dict[str, Any], *, top_score: int | float) -> dict[str, Any]:
    username = entry["username"]
    score = entry.get("score")
    gravity = round((score / top_score) * 10, 3) if score and top_score else None
    return {
        "rank": entry.get("rank"),
        "username": username,
        "digg_profile_username": username.lower(),
        "display_name": entry.get("display_name"),
        "role": entry.get("category"),
        "cohort": entry.get("cohort"),
        "tech_ranked_followers": entry.get("followed_by_count"),
        "gravity": gravity,
        "score": score,
        "followers_count": entry.get("followers_count"),
        "bio": entry.get("bio") or "",
        "x_id": entry.get("target_x_id"),
        "github_url": entry.get("githubUrl"),
        "previous_rank": entry.get("previousRank"),
        "rank_change": entry.get("rankChange"),
        "category_rank": entry.get("categoryRank"),
        "category_confidence": entry.get("categoryConfidence"),
        "vibe_distribution": entry.get("vibeDistribution"),
        "vibe_tweet_count": entry.get("vibeTweetCount"),
        "is_new_entrant": entry.get("isNewEntrant"),
        "is_emerging_startup": entry.get("isEmergingStartup"),
        "emerging_reasoning": entry.get("emergingReasoning"),
        "classification_tldr": entry.get("classificationTldr"),
        "cohort_rank": entry.get("cohortRank"),
        "digg_url": f"{DIGG_BASE}/u/x/{username.lower()}",
        "x_url": f"https://x.com/{username}",
    }


def _split_follower_cards(text: str) -> list[str]:
    top_followers_at = text.find("Top followers")
    if top_followers_at >= 0:
        text = text[top_followers_at:]
    marker = '<a aria-label="Open '
    parts = text.split(marker)
    return [
        marker + part
        for part in parts[1:]
        if 'href="/u/x/' in part and "active:scale" in part
    ]


def parse_top_followers(raw_html: str, target_username: str) -> dict[str, Any]:
    """Parse the initial top-follower rows from a Digg profile page."""
    text = _normalize(raw_html)
    payload = _react_stream_payload(raw_html)
    count_match = re.search(
        rf'"username":"{re.escape(target_username)}".*?'
        r'"initialCount":([0-9,]+).*?"totalCount":([0-9,]+)',
        payload or text,
        flags=re.S | re.I,
    )
    followers: list[dict[str, Any]] = []
    for segment in _split_follower_cards(text):
        profile_username = _first(r'href="/u/x/([^"]+)"', segment)
        rank = _to_int(_first(r">#([0-9,]+)</span>", segment))
        ps = re.findall(r"<p[^>]*>(.*?)</p>", segment, flags=re.S)
        if not profile_username or len(ps) < 2:
            continue
        handle = _clean(ps[1]).removeprefix("@")
        followers.append(
            {
                "rank": rank,
                "username": handle or profile_username,
                "digg_profile_username": profile_username,
                "display_name": _clean(ps[0]),
                "bio": _clean(ps[2]) if len(ps) > 2 else "",
                "x_id": _x_id(segment),
                "digg_url": f"{DIGG_BASE}/u/x/{profile_username}",
                "x_url": f"https://x.com/{handle or profile_username}",
            }
        )
    return {
        "initial_count": _to_int(count_match.group(1)) if count_match else len(followers),
        "total_count": _to_int(count_match.group(2)) if count_match else None,
        "vibe_topics": _parse_vibe_topics(payload),
        "followers": followers,
    }


def parse_api_followers(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    """Parse a Digg follower API page."""
    followers = []
    for item in payload.get("items", []):
        username = item.get("username")
        if not username:
            continue
        followers.append(
            {
                "rank": item.get("rank"),
                "username": username,
                "digg_profile_username": username.lower(),
                "display_name": item.get("display_name") or username,
                "bio": item.get("bio") or "",
                "x_id": item.get("x_id"),
                "role": item.get("category"),
                "followers_count": item.get("followers_count"),
                "profile_image_url": item.get("profile_image_url"),
                "digg_url": f"{DIGG_BASE}/u/x/{username.lower()}",
                "x_url": f"https://x.com/{username}",
            }
        )
    return followers, bool(payload.get("hasMore"))


def _parse_vibe_topics(payload: str) -> dict[str, Any] | None:
    marker = '"vibeTopics":'
    start = payload.find(marker)
    if start < 0:
        return None
    start += len(marker)
    level = 0
    end = None
    in_string = False
    escaped = False
    for index, char in enumerate(payload[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            level += 1
        elif char == "}":
            level -= 1
            if level == 0:
                end = index + 1
                break
    if end is None:
        return None
    return json.loads(payload[start:end])


def scrape(
    *,
    out_dir: Path,
    profile_limit: int,
    include_companies: bool = False,
    workers: int = 6,
    full_followers: bool = False,
    page_sleep: float = 0.05,
) -> dict[str, Any]:
    rankings_html = _get(RANKINGS_URL)
    rankings = parse_rankings(rankings_html)
    selected = [
        row
        for row in rankings
        if include_companies or (row.get("role") or "").lower() != "company"
    ][:profile_limit]

    profiles, edges = _scrape_profiles(
        selected,
        workers=workers,
        full_followers=full_followers,
        page_sleep=page_sleep,
    )

    graph = {
        "generated_at": _now(),
        "source": {
            "name": "Digg Tech rankings",
            "url": RANKINGS_URL,
            "methodology": (
                "Digg says the rankings are built from the X social graph, "
                "using roughly 9 million follow relationships."
            ),
        },
        "rankings": rankings,
        "profiles": profiles,
        "edges": edges,
        "followers_mode": "full_paginated" if full_followers else "initial_profile_slice",
        "limitations": [
            "Rankings page currently exposes 1,000 structured ranking entries.",
            "Digg exposes top followers within its ranked tech graph; this is not the full X follower graph.",
            "Bios are self-authored/profile-derived and need primary-source validation before registry promotion.",
        ],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "seed_graph.json").write_text(json.dumps(graph, indent=2), encoding="utf-8")
    _write_csv(out_dir / "rankings.csv", rankings)
    _write_csv(out_dir / "top_follower_edges.csv", edges)
    return graph


def _scrape_profiles(
    selected: list[dict[str, Any]], *, workers: int, full_followers: bool, page_sleep: float
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not selected:
        return [], []
    workers = max(1, workers)
    profiles_by_rank: dict[int, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                _scrape_one_profile,
                target,
                full_followers=full_followers,
                page_sleep=page_sleep,
            ): target
            for target in selected
        }
        completed = 0
        for future in as_completed(futures):
            target = futures[future]
            try:
                profile, profile_edges = future.result()
            except Exception as exc:
                profile = {
                    "target": target,
                    "error": str(exc),
                    "initial_count": 0,
                    "total_count": None,
                    "vibe_topics": None,
                    "top_followers": [],
                }
                profile_edges = []
            profiles_by_rank[target["rank"]] = profile
            edges.extend(profile_edges)
            completed += 1
            if completed == len(selected) or completed % 50 == 0:
                print(
                    "Digg profile scrape progress: "
                    f"{completed}/{len(selected)} profiles, {len(edges)} edges",
                    file=sys.stderr,
                    flush=True,
                )

    profiles = [profiles_by_rank[target["rank"]] for target in selected]
    edges.sort(key=lambda edge: (edge["to_digg_rank"], edge["from_digg_rank"] or 10**9))
    return profiles, edges


def _scrape_one_profile(
    target: dict[str, Any], *, full_followers: bool, page_sleep: float
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    username = target["digg_profile_username"]
    profile_url = f"{DIGG_BASE}/u/x/{username}"
    parsed = parse_top_followers(_get(profile_url), username)
    follower_fetch_error = None
    if full_followers:
        try:
            followers = _fetch_all_top_followers(
                username,
                page_sleep=page_sleep,
                fallback_followers=parsed["followers"],
            )
        except Exception as exc:
            follower_fetch_error = str(exc)
            followers = parsed["followers"]
    else:
        followers = parsed["followers"]

    profile = {
        "target": target,
        "initial_count": parsed["initial_count"],
        "total_count": parsed["total_count"],
        "fetched_count": len(followers),
        "vibe_topics": parsed["vibe_topics"],
        "top_followers": followers,
        "followers_mode": "full_paginated" if full_followers else "initial_profile_slice",
        "follower_fetch_error": follower_fetch_error,
    }
    edges = [
        {
            "source": "digg_top_followers",
            "from_username": follower["username"],
            "from_display_name": follower["display_name"],
            "from_digg_rank": follower["rank"],
            "from_role": follower.get("role"),
            "from_followers_count": follower.get("followers_count"),
            "from_x_id": follower.get("x_id"),
            "from_digg_url": follower["digg_url"],
            "from_x_url": follower["x_url"],
            "to_username": target["username"],
            "to_display_name": target["display_name"],
            "to_digg_rank": target["rank"],
            "to_role": target.get("role"),
            "to_x_id": target.get("x_id"),
            "to_digg_url": target["digg_url"],
            "to_x_url": target["x_url"],
            "to_github_url": target.get("github_url"),
            "evidence_url": (
                f"{DIGG_BASE}/api/profile/{urllib.parse.quote(username)}/followers"
                if full_followers
                else profile_url
            ),
            "evidence_type": (
                "digg_api_paginated_top_follower"
                if full_followers
                else "digg_profile_top_follower"
            ),
        }
        for follower in followers
    ]
    return profile, edges


def _fetch_all_top_followers(
    username: str,
    *,
    page_sleep: float,
    fallback_followers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    followers: list[dict[str, Any]] = []
    seen: set[str] = set()
    offset = 0
    while True:
        query = urllib.parse.urlencode({"offset": offset, "limit": FOLLOWERS_PAGE_SIZE})
        url = f"{DIGG_BASE}/api/profile/{urllib.parse.quote(username)}/followers?{query}"
        page_followers, has_more = parse_api_followers(_get_json(url))
        for follower in page_followers:
            key = follower.get("x_id") or follower["username"].lower()
            if key in seen:
                continue
            seen.add(key)
            followers.append(follower)
        if not has_more or not page_followers:
            break
        offset += FOLLOWERS_PAGE_SIZE
        if page_sleep > 0:
            time.sleep(page_sleep)
    return followers or fallback_followers


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scrape Digg seed graph.")
    parser.add_argument("--out", default="data/digg", help="Output directory.")
    parser.add_argument(
        "--profiles",
        type=int,
        default=20,
        help="Number of ranked people profiles to fetch for top-follower edges.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=6,
        help="Concurrent profile fetches for top-follower edge extraction.",
    )
    parser.add_argument(
        "--include-companies",
        action="store_true",
        help="Fetch profile edges for company/org ranking rows too.",
    )
    parser.add_argument(
        "--full-followers",
        action="store_true",
        help="Page through Digg's follower API instead of only using the first rendered slice.",
    )
    parser.add_argument(
        "--page-sleep",
        type=float,
        default=0.05,
        help="Seconds to sleep between paginated follower API requests per worker.",
    )
    args = parser.parse_args(argv)
    graph = scrape(
        out_dir=Path(args.out),
        profile_limit=args.profiles,
        include_companies=args.include_companies,
        workers=args.workers,
        full_followers=args.full_followers,
        page_sleep=args.page_sleep,
    )
    print(
        "Digg scrape wrote "
        f"{len(graph['rankings'])} rankings, "
        f"{len(graph['profiles'])} profiles, "
        f"{len(graph['edges'])} edges to {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
