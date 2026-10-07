"""Manual Slack delivery for one canonical audience brief."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date as calendar_date
from datetime import datetime, timezone
import hashlib
import html
import os
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlencode

import httpx

from fli.insights import company_context, pdf_report


SCHEMA_VERSION = "daily-brief-delivery-v3"
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENV_PATH = REPO_ROOT / ".env"

DeliveryChannel = Literal["slack"]


class DeliveryNotConfigured(ValueError):
    """The selected delivery channel is not ready for use."""


class DeliveryFailed(RuntimeError):
    """A configured delivery provider rejected or failed the send."""


def _env_file_values(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


@dataclass(frozen=True)
class DeliverySettings:
    slack_webhook_url: str | None
    slack_destination_label: str
    timeout_seconds: float = 15.0

    @classmethod
    def from_environment(
        cls,
        *,
        environ: Mapping[str, str] | None = None,
        env_path: Path = DEFAULT_ENV_PATH,
    ) -> DeliverySettings:
        runtime = os.environ if environ is None else environ
        file_values = _env_file_values(env_path)

        def value(name: str, default: str = "") -> str:
            return str(runtime.get(name) or file_values.get(name) or default).strip()

        return cls(
            slack_webhook_url=value("FLI_SLACK_WEBHOOK_URL") or None,
            slack_destination_label=value(
                "FLI_DELIVERY_SLACK_LABEL",
                "Frontier Lab Intelligence channel",
            ),
            timeout_seconds=float(value("FLI_DELIVERY_TIMEOUT_SECONDS", "15")),
        )

    def channel_configured(self, channel: DeliveryChannel) -> bool:
        return channel == "slack" and bool(self.slack_webhook_url)

    def destination_label(self, channel: DeliveryChannel) -> str:
        if channel != "slack":
            raise DeliveryNotConfigured("Only Slack delivery is supported.")
        return self.slack_destination_label


def _plain(value: Any) -> str:
    return " ".join(html.unescape(str(value or "")).split())


def _display_day(day: str) -> str:
    try:
        parsed = calendar_date.fromisoformat(day)
    except ValueError:
        return day
    return f"{parsed.day} {parsed.strftime('%B %Y')}"


def _rank(item: dict[str, Any]) -> int:
    return int(item.get("daily_rank") or 0)


def _title(item: dict[str, Any]) -> str:
    return str(item.get("headline") or "")


def _summary(item: dict[str, Any]) -> str:
    return str(item.get("what_changed") or "")


def _audience_label(audience: str) -> str:
    return "Investment" if audience == "investment" else "AI Engineering"


def _brief_url(payload: dict[str, Any]) -> str:
    day = str(payload.get("date") or payload.get("requested_date") or "")
    audience = str(payload.get("audience") or "investment")
    query = urlencode({"date": day, "audience": audience, "status": "kept"})
    return f"{pdf_report.PUBLIC_APP_URL}/insights?{query}"


def _slack_escape(value: Any) -> str:
    return _plain(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _slack_text_chunks(value: Any, *, limit: int = 2700) -> list[str]:
    """Split complete prose across Slack sections without ellipsizing it."""
    words = _plain(value).split()
    chunks: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(_slack_escape(candidate)) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(_slack_escape(current))
            current = ""
        while word and len(_slack_escape(word)) > limit:
            low, high = 1, len(word)
            while low < high:
                midpoint = (low + high + 1) // 2
                if len(_slack_escape(word[:midpoint])) <= limit:
                    low = midpoint
                else:
                    high = midpoint - 1
            chunks.append(_slack_escape(word[:low]))
            word = word[low:]
        current = word
    if current:
        chunks.append(_slack_escape(current))
    return chunks


def _slack_prose_blocks(value: Any) -> list[dict[str, Any]]:
    chunks = _slack_text_chunks(value)
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": chunk,
            },
        }
        for chunk in chunks
    ]


def _slack_company_lines(
    item: dict[str, Any],
    bets: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    company_names = item.get("company_names") or {}
    seen: set[tuple[str, str]] = set()
    lines: list[str] = []
    for connection in item.get("connections") or []:
        for company in connection.get("companies") or []:
            ticker = str(company.get("ticker") or "").strip()
            bet_id = str(company.get("bet_id") or "").strip()
            identity = (ticker, bet_id)
            if not ticker or identity in seen:
                continue
            seen.add(identity)
            direction = str((bets.get(bet_id) or {}).get("direction") or "").strip()
            if direction not in {"upside", "downside"}:
                continue
            name = _plain(company_names.get(ticker) or ticker)
            arrow = "↑" if direction == "upside" else "↓"
            label = f"{name} ({ticker})" if name != ticker else ticker
            lines.append(
                f"• *{_slack_escape(label)}* · {arrow} {direction.title()}"
            )
    return lines


def _slack_engineering_lines(item: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for landing in item.get("lands") or []:
        surface_id = _plain(landing.get("surface_id"))
        surface_name = _plain(landing.get("surface_name"))
        label = surface_name or surface_id
        if not label or label in seen:
            continue
        seen.add(label)
        suffix = f" ({surface_id})" if surface_id and surface_id != label else ""
        lines.append(f"• *{_slack_escape(label + suffix)}*")
    return lines


def _slack_payload(payload: dict[str, Any]) -> dict[str, Any]:
    items = sorted(
        list(payload.get("items") or []),
        key=_rank,
    )
    day = str(payload.get("date") or payload.get("requested_date") or "")
    audience = _audience_label(str(payload.get("audience") or "investment"))
    brief_url = _brief_url(payload)
    is_investment = payload.get("content_kind") == "investment_agent"
    bets = company_context.investment_bet_index() if is_investment else {}
    fallback_lines = [
        f"Frontier Lab Intelligence | {audience} brief | {_display_day(day)}",
    ]
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{audience} brief",
                "emoji": False,
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*{_display_day(day)}* · {len(items)} Insights",
                }
            ],
        },
        {"type": "divider"},
    ]
    for index, item in enumerate(items):
        if index:
            blocks.append({"type": "divider"})
        brief_position = index + 1
        title = _slack_escape(_title(item))
        summary = _summary(item)
        landing_lines = (
            _slack_company_lines(item, bets)
            if is_investment
            else _slack_engineering_lines(item)
        )
        landing_label = (
            "How this reaches companies"
            if is_investment
            else "Engineering surfaces"
        )
        fallback_lines.extend(
            [
                "",
                f"{brief_position}. {_plain(_title(item))}",
                "What changed",
                _plain(summary),
            ]
        )
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{brief_position}. {title}*",
                },
            }
        )
        if summary:
            prose_blocks = _slack_prose_blocks(summary)
            if prose_blocks:
                prose_blocks[0]["text"]["text"] = (
                    f"*What changed*\n{prose_blocks[0]['text']['text']}"
                )
            blocks.extend(prose_blocks)
        if landing_lines:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*{landing_label}*\n"
                            + "\n".join(landing_lines)
                        ),
                    },
                }
            )
            fallback_lines.extend([landing_label, *landing_lines])
    blocks.extend(
        [
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Read full brief",
                            "emoji": False,
                        },
                        "url": brief_url,
                    },
                ],
            },
        ]
    )
    fallback_lines.append(f"Read full brief: {brief_url}")
    return {"text": "\n".join(fallback_lines), "blocks": blocks}


def _send_slack(
    settings: DeliverySettings,
    payload: dict[str, Any],
    *,
    transport: httpx.BaseTransport | None = None,
) -> str:
    if not settings.slack_webhook_url:
        raise DeliveryNotConfigured("Slack delivery is not configured.")
    try:
        with httpx.Client(
            transport=transport,
            timeout=httpx.Timeout(settings.timeout_seconds, connect=5.0),
        ) as client:
            response = client.post(settings.slack_webhook_url, json=_slack_payload(payload))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DeliveryFailed("Slack did not accept the Daily Brief notification.") from exc
    if response.text.strip().lower() != "ok":
        raise DeliveryFailed("Slack returned an unexpected response to the notification.")
    return "slack-webhook"


def delivery_status_payload(
    payload: dict[str, Any],
    *,
    settings: DeliverySettings | None = None,
) -> dict[str, Any]:
    resolved = settings or DeliverySettings.from_environment()
    available = bool(
        payload.get("content_kind") in {"investment_agent", "engineering_agent"}
        and payload.get("available")
    )
    total_insight_count = len(list(payload.get("items") or [])) if available else 0
    configured = resolved.channel_configured("slack")
    channels = [
        {
            "channel": "slack",
            "label": "Slack",
            "configured": configured,
            "available": bool(available and configured),
            "destination": resolved.destination_label("slack") if configured else "Not configured",
        }
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "available": available,
        "reason": None if available else str(payload.get("reason") or "No complete Daily Brief is available."),
        "audience": payload.get("audience"),
        "date": payload.get("date") or payload.get("requested_date"),
        "total_insight_count": total_insight_count,
        "channels": channels,
    }


def deliver_daily_brief(
    payload: dict[str, Any],
    *,
    channel: DeliveryChannel,
    settings: DeliverySettings | None = None,
    slack_transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    resolved = settings or DeliverySettings.from_environment()
    if channel != "slack":
        raise DeliveryNotConfigured("Only Slack delivery is supported.")
    content_kind = payload.get("content_kind")
    if content_kind not in {"investment_agent", "engineering_agent"} or not payload.get("available"):
        raise DeliveryNotConfigured(
            str(payload.get("reason") or "No complete Daily Brief is available for delivery.")
        )
    if not resolved.channel_configured(channel):
        raise DeliveryNotConfigured(f"{channel.title()} delivery is not configured.")

    provider_id = _send_slack(resolved, payload, transport=slack_transport)

    day = str(payload.get("date") or payload.get("requested_date") or "")
    audience = str(payload.get("audience") or "investment")
    run = payload.get("run") or {}
    delivery_identity = hashlib.sha256(
        f"{channel}:{audience}:{day}:{run.get('result_sha256', '')}".encode()
    ).hexdigest()
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "sent",
        "channel": channel,
        "destination": resolved.destination_label(channel),
        "audience": audience,
        "date": day,
        "insight_count": len(list(payload.get("items") or [])),
        "delivery_id": delivery_identity,
        "provider_id": provider_id,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
