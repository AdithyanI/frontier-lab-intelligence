"""Conference speaker sources for reversible Registry seed expansion.

Conference curation is candidate provenance, not a ranking weight. Only records
with an X handle become monitorable people. Organizations and listed roles are
preserved independently so later evaluation can keep, reject, or tier the
cohort without losing the source evidence that introduced it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from fli import channels

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "data" / "registry" / "conference-sources.json"
DEFAULT_RAW_ROOT = REPO_ROOT / "data" / "raw" / "conference-sources"
DEFAULT_DB = REPO_ROOT / "data" / "fli.db"
USER_AGENT = "FrontierLabIntelligence/0.1 conference-source"
X_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:x|twitter)\.com/([A-Za-z0-9_]{1,15})",
    re.IGNORECASE,
)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)[^)]*\)")
NON_ORGANIZATIONS = frozenset(
    {
        "",
        "independent",
        "self employed",
        "self-employed",
        "stealth",
        "stealth startup",
        "n/a",
        "na",
        "none",
        "tbd",
    }
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class ConferenceSource:
    source_id: str
    name: str
    conference_url: str
    data_url: str
    format: str
    observed_at: str


@dataclass(frozen=True)
class SpeakerRecord:
    source_id: str
    conference_name: str
    conference_url: str
    observed_at: str
    name: str
    x_handle: str | None
    role: str | None
    company: str | None
    bio: str | None
    website: str | None
    blog: str | None
    session_titles: tuple[str, ...]
    company_website: str | None = None
    company_x_candidate: str | None = None


class _NextDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._capture = False
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and dict(attrs).get("id") == "__NEXT_DATA__":
            self._capture = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._capture:
            self._capture = False

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._chunks.append(data)

    def payload(self) -> dict[str, Any]:
        if not self._chunks:
            raise ValueError("conference page has no __NEXT_DATA__ payload")
        return json.loads("".join(self._chunks))


def load_manifest(path: Path | str = DEFAULT_MANIFEST) -> list[ConferenceSource]:
    raw = json.loads(Path(path).read_text())
    if not isinstance(raw, list) or not raw:
        raise ValueError("conference source manifest must be a non-empty list")
    sources: list[ConferenceSource] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"conference source {index} must be an object")
        source = ConferenceSource(**item)
        if source.source_id in seen:
            raise ValueError(f"duplicate conference source_id: {source.source_id}")
        if source.format not in {
            "speakers-json-v1",
            "next-data-worldsfair-2024",
            "next-data-summit-2023",
        }:
            raise ValueError(f"unsupported conference format: {source.format}")
        if not source.data_url.startswith("https://"):
            raise ValueError(f"conference source {source.source_id} needs HTTPS data_url")
        seen.add(source.source_id)
        sources.append(source)
    return sources


def select_sources(
    sources: Iterable[ConferenceSource], source_ids: Iterable[str] | None
) -> list[ConferenceSource]:
    sources = list(sources)
    if not source_ids:
        return sources
    requested = list(dict.fromkeys(source_ids))
    by_id = {source.source_id: source for source in sources}
    unknown = [source_id for source_id in requested if source_id not in by_id]
    if unknown:
        raise ValueError("unknown conference source_id: " + ", ".join(unknown))
    return [by_id[source_id] for source_id in requested]


def snapshot_sources(
    sources: Iterable[ConferenceSource],
    *,
    raw_root: Path | str = DEFAULT_RAW_ROOT,
) -> list[dict[str, Any]]:
    root = Path(raw_root)
    root.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for source in sources:
        request = Request(source.data_url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=60) as response:
            payload = response.read()
        suffix = ".json" if source.format == "speakers-json-v1" else ".html"
        destination = root / f"{source.source_id}{suffix}"
        destination.write_bytes(payload)
        snapshots.append(
            {
                "source_id": source.source_id,
                "path": str(destination),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "data_url": source.data_url,
            }
        )
    return snapshots


def _snapshot_path(source: ConferenceSource, raw_root: Path | str) -> Path:
    suffix = ".json" if source.format == "speakers-json-v1" else ".html"
    return Path(raw_root) / f"{source.source_id}{suffix}"


def _clean(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _x_handle(value: str | None) -> str | None:
    if not value:
        return None
    match = X_URL_RE.search(value)
    return match.group(1).lower() if match else None


def _markdown_link(value: str | None, label: str) -> str | None:
    if not value:
        return None
    for link_label, url in MARKDOWN_LINK_RE.findall(value):
        if link_label.strip().casefold() == label.casefold():
            return url.strip()
    return None


def _company(value: Any) -> str | None:
    cleaned = _clean(value)
    if not cleaned or cleaned.casefold() in NON_ORGANIZATIONS:
        return None
    return cleaned


def _session_titles(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    values = {
        title
        for item in raw
        if isinstance(item, dict) and (title := _clean(item.get("title")))
    }
    return tuple(sorted(values, key=str.casefold))


def _parse_speakers_json(
    source: ConferenceSource, payload: bytes
) -> list[SpeakerRecord]:
    data = json.loads(payload)
    speakers = data.get("speakers")
    if not isinstance(speakers, list):
        raise ValueError(f"{source.source_id} has no speakers array")
    records = []
    for item in speakers:
        if not isinstance(item, dict) or not _clean(item.get("name")):
            continue
        records.append(
            SpeakerRecord(
                source_id=source.source_id,
                conference_name=source.name,
                conference_url=source.conference_url,
                observed_at=source.observed_at,
                name=_clean(item["name"]) or "",
                x_handle=_x_handle(_clean(item.get("twitter"))),
                role=_clean(item.get("role")),
                company=_company(item.get("company")),
                bio=_clean(item.get("bio")),
                website=_clean(item.get("website")),
                blog=_clean(item.get("blog")),
                session_titles=_session_titles(item.get("sessions")),
            )
        )
    return records


def _next_page_props(payload: bytes) -> dict[str, Any]:
    parser = _NextDataParser()
    parser.feed(payload.decode("utf-8"))
    return parser.payload().get("props", {}).get("pageProps", {})


def _company_attributes(presenter: dict[str, Any]) -> dict[str, Any]:
    company = presenter.get("company") or {}
    data = company.get("data") if isinstance(company, dict) else None
    if not isinstance(data, dict):
        return {}
    attributes = data.get("attributes")
    return attributes if isinstance(attributes, dict) else {}


def _parse_worldsfair_2024(
    source: ConferenceSource, payload: bytes
) -> list[SpeakerRecord]:
    page_props = _next_page_props(payload)
    presenters = page_props.get("presenters")
    if not isinstance(presenters, list):
        raise ValueError(f"{source.source_id} has no presenters payload")
    records_by_name: dict[str, SpeakerRecord] = {}
    for item in presenters:
        if not isinstance(item, dict):
            continue
        presenter = item.get("attributes", item)
        if not isinstance(presenter, dict) or not _clean(presenter.get("name")):
            continue
        name = _clean(presenter["name"]) or ""
        company = _company_attributes(presenter)
        social = "\n".join(
            part
            for part in (
                _clean(presenter.get("socialLinks")),
                _clean(presenter.get("about")),
            )
            if part
        )
        company_social = _clean(company.get("socialLinks"))
        records_by_name[name.casefold()] = SpeakerRecord(
            source_id=source.source_id,
            conference_name=source.name,
            conference_url=source.conference_url,
            observed_at=source.observed_at,
            name=name,
            x_handle=_x_handle(social),
            role=_clean(presenter.get("tagline")),
            company=_company(company.get("name")),
            bio=_clean(presenter.get("about")),
            website=_markdown_link(social, "Website"),
            blog=None,
            session_titles=(),
            company_website=_clean(company.get("link")),
            company_x_candidate=_x_handle(company_social),
        )
    return list(records_by_name.values())


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _split_legacy_tagline(value: str | None) -> tuple[str | None, str | None]:
    if not value or "," not in value:
        return value, None
    role, company = value.rsplit(",", 1)
    return _clean(role), _company(company)


def _parse_summit_2023(
    source: ConferenceSource, payload: bytes
) -> list[SpeakerRecord]:
    page_props = _next_page_props(payload)
    records_by_name: dict[str, SpeakerRecord] = {}
    for presenter in _walk(page_props):
        if not {"name", "tagline", "about"}.issubset(presenter):
            continue
        name = _clean(presenter.get("name"))
        if not name:
            continue
        about = _clean(presenter.get("about"))
        role, company = _split_legacy_tagline(_clean(presenter.get("tagline")))
        records_by_name[name.casefold()] = SpeakerRecord(
            source_id=source.source_id,
            conference_name=source.name,
            conference_url=source.conference_url,
            observed_at=source.observed_at,
            name=name,
            x_handle=_x_handle(about),
            role=role,
            company=company,
            bio=about,
            website=_markdown_link(about, "Website"),
            blog=None,
            session_titles=(),
        )
    return list(records_by_name.values())


def parse_source(source: ConferenceSource, payload: bytes) -> list[SpeakerRecord]:
    if source.format == "speakers-json-v1":
        return _parse_speakers_json(source, payload)
    if source.format == "next-data-worldsfair-2024":
        return _parse_worldsfair_2024(source, payload)
    if source.format == "next-data-summit-2023":
        return _parse_summit_2023(source, payload)
    raise ValueError(f"unsupported conference format: {source.format}")


def load_snapshots(
    sources: Iterable[ConferenceSource],
    *,
    raw_root: Path | str = DEFAULT_RAW_ROOT,
) -> tuple[list[SpeakerRecord], list[dict[str, Any]]]:
    records: list[SpeakerRecord] = []
    snapshots = []
    for source in sources:
        path = _snapshot_path(source, raw_root)
        payload = path.read_bytes()
        parsed = parse_source(source, payload)
        records.extend(parsed)
        snapshots.append(
            {
                "source_id": source.source_id,
                "path": str(path),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "records": len(parsed),
                "x_records": sum(record.x_handle is not None for record in parsed),
            }
        )
    return records, snapshots


def _normalize_organization(value: str) -> str:
    value = value.casefold().replace("&", " and ")
    value = re.sub(
        r"\b(incorporated|inc|limited|ltd|llc|corporation|corp|company|co)\b",
        " ",
        value,
    )
    return re.sub(r"[^a-z0-9]+", "", value)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")[:72]
    return slug or hashlib.sha256(value.encode()).hexdigest()[:12]


def _available_slug(conn: sqlite3.Connection, base: str) -> str:
    if not conn.execute("SELECT 1 FROM entities WHERE slug = ?", (base,)).fetchone():
        return base
    digest = hashlib.sha256(base.encode()).hexdigest()[:10]
    return f"{base[:69]}-{digest}"


def audit_records(conn: sqlite3.Connection, records: Iterable[SpeakerRecord]) -> dict:
    records = list(records)
    handles = {record.x_handle for record in records if record.x_handle}
    existing = {
        row["key"].casefold(): row
        for row in conn.execute(
            """SELECT c.key, e.id, e.kind,
                      CASE WHEN rejected.entity_id IS NULL
                           THEN 'active' ELSE 'rejected' END AS registry_state
               FROM channels c
               JOIN entity_channels ec ON ec.channel_id = c.id
               JOIN entities e ON e.id = ec.entity_id
               LEFT JOIN entity_registry_rejections rejected
                 ON rejected.entity_id = e.id
               WHERE c.kind = 'x'"""
        ).fetchall()
    }
    matched = {handle: existing[handle] for handle in handles if handle in existing}
    companies = {
        _normalize_organization(record.company)
        for record in records
        if record.company
    }
    source_counts = {}
    for source_id in sorted({record.source_id for record in records}):
        source_records = [record for record in records if record.source_id == source_id]
        source_counts[source_id] = {
            "records": len(source_records),
            "x_records": sum(record.x_handle is not None for record in source_records),
            "companies": len(
                {
                    _normalize_organization(record.company)
                    for record in source_records
                    if record.company
                }
            ),
        }
    return {
        "records": len(records),
        "unique_names": len({record.name.casefold() for record in records}),
        "unique_x_handles": len(handles),
        "x_handles_already_in_registry": len(matched),
        "new_x_handles": len(handles) - len(matched),
        "matched_active": sum(
            row["registry_state"] == "active" for row in matched.values()
        ),
        "matched_rejected": sum(
            row["registry_state"] == "rejected" for row in matched.values()
        ),
        "unique_company_labels": len(companies),
        "source_counts": source_counts,
    }


def _organization_index(conn: sqlite3.Connection) -> dict[str, int]:
    index: dict[str, int] = {}
    for row in conn.execute(
        "SELECT id, name FROM entities WHERE kind = 'organization'"
    ).fetchall():
        index.setdefault(_normalize_organization(row["name"]), row["id"])
    return index


def _website_key(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value if "://" in value else f"https://{value}")
    host = (parsed.hostname or "").casefold().removeprefix("www.")
    return host or None


def _organization_website_index(conn: sqlite3.Connection) -> dict[str, int]:
    index: dict[str, int] = {}
    rows = conn.execute(
        """SELECT c.key, ec.entity_id
           FROM channels c
           JOIN entity_channels ec ON ec.channel_id = c.id
           JOIN entities e ON e.id = ec.entity_id
           WHERE c.kind = 'website' AND e.kind = 'organization'"""
    ).fetchall()
    for row in rows:
        if key := _website_key(row["key"]):
            index.setdefault(key, row["entity_id"])
    return index


def _ensure_account(
    conn: sqlite3.Connection, record: SpeakerRecord
) -> tuple[int, bool]:
    assert record.x_handle is not None
    row = conn.execute(
        "SELECT * FROM accounts WHERE platform = 'x' AND handle = ?",
        (record.x_handle,),
    ).fetchone()
    if row is None:
        cursor = conn.execute(
            """INSERT INTO accounts
               (platform, handle, display_name, first_seen_at, last_seen_at)
               VALUES ('x', ?, ?, ?, ?)""",
            (record.x_handle, record.name, record.observed_at, record.observed_at),
        )
        account_id = cursor.lastrowid
        created = True
    else:
        account_id = row["id"]
        created = False
        conn.execute(
            """UPDATE accounts
               SET display_name = COALESCE(display_name, ?),
                   first_seen_at = min(first_seen_at, ?),
                   last_seen_at = max(last_seen_at, ?)
               WHERE id = ?""",
            (record.name, record.observed_at, record.observed_at, account_id),
        )
    conn.execute(
        """INSERT INTO account_source_facts
           (account_id, source, fact, value, observed_at, evidence_url)
           VALUES (?, ?, 'conference_speaker', ?, ?, ?)
           ON CONFLICT (account_id, source, fact) DO UPDATE SET
               value = excluded.value,
               observed_at = excluded.observed_at,
               evidence_url = excluded.evidence_url""",
        (
            account_id,
            record.source_id,
            record.conference_name,
            record.observed_at,
            record.conference_url,
        ),
    )
    return account_id, created


def _ensure_person(conn: sqlite3.Connection, record: SpeakerRecord) -> tuple[int, bool]:
    assert record.x_handle is not None
    channel_id = channels.upsert_channel(
        conn,
        kind="x",
        key=record.x_handle,
        label=record.name,
        observed_at=record.observed_at,
    )
    owner = conn.execute(
        """SELECT e.id, e.kind
           FROM entity_channels ec
           JOIN entities e ON e.id = ec.entity_id
           WHERE ec.channel_id = ?""",
        (channel_id,),
    ).fetchone()
    created = False
    if owner is None:
        entity_id = channels.upsert_entity(
            conn,
            kind="person",
            slug=_available_slug(conn, f"x-{record.x_handle}"),
            name=record.name,
            observed_at=record.observed_at,
        )
        channels.link_entity_channel(
            conn,
            entity_id=entity_id,
            channel_id=channel_id,
            relationship="identity",
            confidence=1.0,
            evidence_url=record.conference_url,
            notes=f"Speaker listed by {record.conference_name}.",
            observed_at=record.observed_at,
        )
        created = True
    else:
        entity_id = owner["id"]
        if owner["kind"] == "organization":
            raise ValueError(
                f"speaker @{record.x_handle} belongs to organization entity {entity_id}"
            )
        if owner["kind"] in {"unknown", "unsure"}:
            conn.execute(
                """UPDATE entities
                   SET kind = 'person', updated_at = ?
                   WHERE id = ?""",
                (record.observed_at, entity_id),
            )
    return entity_id, created


def _ensure_organization(
    conn: sqlite3.Connection,
    record: SpeakerRecord,
    index: dict[str, int],
    website_index: dict[str, int],
) -> tuple[int | None, bool]:
    if not record.company:
        return None, False
    key = _normalize_organization(record.company)
    website_key = _website_key(record.company_website)
    entity_id = index.get(key)
    if entity_id is None and website_key:
        entity_id = website_index.get(website_key)
    created = False
    if entity_id is None:
        entity_id = channels.upsert_entity(
            conn,
            kind="organization",
            slug=_available_slug(conn, f"organization-{_slug(record.company)}"),
            name=record.company,
            observed_at=record.observed_at,
        )
        index[key] = entity_id
        created = True
    else:
        index.setdefault(key, entity_id)
    if record.company_website:
        website_channel_id = channels.upsert_channel(
            conn,
            kind="website",
            key=record.company_website,
            label=f"{record.company} website",
            observed_at=record.observed_at,
        )
        owner = conn.execute(
            "SELECT entity_id FROM entity_channels WHERE channel_id = ?",
            (website_channel_id,),
        ).fetchone()
        if owner is None or owner["entity_id"] == entity_id:
            channels.link_entity_channel(
                conn,
                entity_id=entity_id,
                channel_id=website_channel_id,
                relationship="official",
                confidence=0.95,
                evidence_url=record.conference_url,
                notes=f"Official company link in {record.conference_name} speaker data.",
                observed_at=record.observed_at,
            )
            if website_key:
                website_index.setdefault(website_key, entity_id)
    return entity_id, created


def _record_person_facts(
    conn: sqlite3.Connection, entity_id: int, record: SpeakerRecord
) -> None:
    facts: dict[str, Any] = {
        "conference_speaker": record.conference_name,
        "speaker_role": record.role,
        "speaker_company": record.company,
        "speaker_bio": record.bio,
    }
    for fact, value in facts.items():
        channels.record_entity_fact(
            conn,
            entity_id=entity_id,
            source=record.source_id,
            fact=fact,
            value=value,
            observed_at=record.observed_at,
            evidence_url=record.conference_url,
        )


def select_monitorable_records(
    records: Iterable[SpeakerRecord], *, limit: int | None = None
) -> list[SpeakerRecord]:
    """Return a stable, de-duplicated cohort of speakers with X identities."""
    selected: list[SpeakerRecord] = []
    seen_handles: set[str] = set()
    for record in records:
        if not record.x_handle or record.x_handle in seen_handles:
            continue
        seen_handles.add(record.x_handle)
        selected.append(record)
        if limit is not None and len(selected) >= limit:
            break
    return selected


def import_records(conn: sqlite3.Connection, records: Iterable[SpeakerRecord]) -> dict:
    channels.ensure_schema(conn)
    records = list(records)
    organizations = _organization_index(conn)
    organization_websites = _organization_website_index(conn)
    created_people = 0
    matched_people: set[int] = set()
    created_organizations = 0
    affiliations = 0
    accounts_created = 0
    non_x_records = 0
    for record in records:
        if not record.x_handle:
            non_x_records += 1
            continue
        _, account_created = _ensure_account(conn, record)
        accounts_created += account_created
        person_id, person_created = _ensure_person(conn, record)
        created_people += person_created
        matched_people.add(person_id)
        _record_person_facts(conn, person_id, record)
        organization_id, organization_created = _ensure_organization(
            conn, record, organizations, organization_websites
        )
        created_organizations += organization_created
        if organization_id is not None:
            channels.record_entity_fact(
                conn,
                entity_id=organization_id,
                source=record.source_id,
                fact="conference_company",
                value=record.company,
                observed_at=record.observed_at,
                evidence_url=record.conference_url,
            )
            if record.company_x_candidate:
                channels.record_entity_fact(
                    conn,
                    entity_id=organization_id,
                    source=record.source_id,
                    fact="company_x_candidate",
                    value=record.company_x_candidate,
                    observed_at=record.observed_at,
                    evidence_url=record.conference_url,
                )
            channels.record_affiliation(
                conn,
                person_entity_id=person_id,
                organization_entity_id=organization_id,
                relationship="listed_affiliation",
                role_title=record.role,
                source=record.source_id,
                observed_at=record.observed_at,
                evidence_url=record.conference_url,
            )
            affiliations += 1
    return {
        "records": len(records),
        "non_x_records_preserved_raw_only": non_x_records,
        "unique_monitorable_people": len(matched_people),
        "people_created": created_people,
        "accounts_created": accounts_created,
        "organizations_created": created_organizations,
        "affiliations_written": affiliations,
    }


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fli conference-sources")
    parser.add_argument("action", choices=["snapshot", "audit", "import"])
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--source",
        dest="source_ids",
        action="append",
        help="Restrict the action to one manifest source ID; repeatable.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Import at most this many unique speakers with X identities.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        sources = select_sources(load_manifest(args.manifest), args.source_ids)
    except ValueError as exc:
        parser.error(str(exc))
    if args.action == "snapshot":
        _print({"status": "ok", "snapshots": snapshot_sources(sources, raw_root=args.raw_root)})
        return 0
    records, snapshots = load_snapshots(sources, raw_root=args.raw_root)
    conn = channels.connect(args.db)
    if args.action == "audit":
        _print(
            {
                "status": "ok",
                "snapshots": snapshots,
                "coverage": audit_records(conn, records),
            }
        )
        return 0
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    import_cohort = select_monitorable_records(records, limit=args.limit)
    conn.execute("BEGIN IMMEDIATE")
    try:
        result = import_records(conn, import_cohort)
        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    _print(
        {
            "status": "ok",
            "dry_run": args.dry_run,
            "available_monitorable_records": len(
                select_monitorable_records(records)
            ),
            "selected_monitorable_records": len(import_cohort),
            "snapshots": snapshots,
            "result": result,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
