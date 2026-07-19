"""Manual Slack and email delivery for one canonical Daily Intelligence Brief."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date as calendar_date
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
import hashlib
import hmac
import html
import ipaddress
import os
from pathlib import Path
import smtplib
import ssl
from typing import Any, Literal
from urllib.parse import urlencode

import httpx

from fli.insights import pdf_report


SCHEMA_VERSION = "daily-brief-delivery-v1"
TOP_INSIGHT_LIMIT = 5
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENV_PATH = REPO_ROOT / ".env"

DeliveryChannel = Literal["slack", "email"]


class DeliveryNotConfigured(ValueError):
    """The selected delivery channel is not ready for use."""


class DeliveryAuthorizationError(PermissionError):
    """A public delivery request did not supply the operator credential."""


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


def _mask_email(value: str) -> str:
    local, separator, domain = value.partition("@")
    if not separator:
        return "Configured recipient"
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}{'*' * max(2, len(local) - len(visible))}@{domain}"


@dataclass(frozen=True)
class DeliverySettings:
    slack_webhook_url: str | None
    slack_destination_label: str
    email_recipients: tuple[str, ...]
    email_destination_label: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str | None
    smtp_from_email: str
    smtp_from_name: str
    smtp_reply_to: str | None
    operator_token: str | None
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

        recipients = tuple(
            recipient.strip()
            for recipient in value("FLI_DELIVERY_EMAIL_TO", "adi@aipodcast.ing").split(",")
            if recipient.strip()
        )
        email_label = value("FLI_DELIVERY_EMAIL_LABEL")
        if not email_label and recipients:
            email_label = ", ".join(_mask_email(recipient) for recipient in recipients)
        return cls(
            slack_webhook_url=value("FLI_SLACK_WEBHOOK_URL") or None,
            slack_destination_label=value(
                "FLI_DELIVERY_SLACK_LABEL",
                "Frontier Lab Intelligence channel",
            ),
            email_recipients=recipients,
            email_destination_label=email_label or "Configured recipient",
            smtp_host=value("ACS_SMTP_HOST", "smtp.azurecomm.net"),
            smtp_port=int(value("ACS_SMTP_PORT", "587")),
            smtp_username=value("ACS_SMTP_USER", "ghostsmtp"),
            smtp_password=value("ACS_SMTP_PASS") or None,
            smtp_from_email=value(
                "ACS_SMTP_FROM_EMAIL",
                "notifications@mail.aipodcast.ing",
            ),
            smtp_from_name=value("ACS_SMTP_FROM_NAME", "Frontier Lab Intelligence"),
            smtp_reply_to=value("ACS_SMTP_REPLY_TO", "adi@aipodcast.ing") or None,
            operator_token=value("FLI_DELIVERY_OPERATOR_TOKEN") or None,
            timeout_seconds=float(value("FLI_DELIVERY_TIMEOUT_SECONDS", "15")),
        )

    def channel_configured(self, channel: DeliveryChannel) -> bool:
        if channel == "slack":
            return bool(self.slack_webhook_url)
        return bool(self.email_recipients and self.smtp_password)

    def destination_label(self, channel: DeliveryChannel) -> str:
        if channel == "slack":
            return self.slack_destination_label
        return self.email_destination_label


def _is_loopback(host: str | None) -> bool:
    if not host:
        return False
    normalized = host.strip("[]").split("%", 1)[0]
    if normalized.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _public_access_ready(settings: DeliverySettings, remote_host: str | None) -> bool:
    return _is_loopback(remote_host) or bool(settings.operator_token)


def _authorize(
    settings: DeliverySettings,
    *,
    remote_host: str | None,
    authorization: str | None,
) -> None:
    if _is_loopback(remote_host):
        return
    if not settings.operator_token:
        raise DeliveryAuthorizationError(
            "Public brief delivery is not configured with an operator access key."
        )
    prefix = "Bearer "
    supplied = (
        authorization[len(prefix) :].strip()
        if authorization and authorization.startswith(prefix)
        else ""
    )
    if not supplied or not hmac.compare_digest(supplied, settings.operator_token):
        raise DeliveryAuthorizationError("The delivery access key is missing or incorrect.")


def _plain(value: Any) -> str:
    return " ".join(html.unescape(str(value or "")).split())


def _display_day(day: str) -> str:
    try:
        parsed = calendar_date.fromisoformat(day)
    except ValueError:
        return day
    return f"{parsed.day} {parsed.strftime('%B %Y')}"


def _audience_label(audience: str) -> str:
    return "Investment" if audience == "investment" else "AI Engineering"


def _top_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        list(payload.get("items") or []),
        key=lambda item: int(item.get("rank") or 0),
    )[:TOP_INSIGHT_LIMIT]


def _urls(payload: dict[str, Any]) -> tuple[str, str]:
    day = str(payload.get("date") or payload.get("requested_date") or "")
    audience = str(payload.get("audience") or "investment")
    query = urlencode({"date": day, "audience": audience, "status": "kept"})
    report_query = urlencode({"audience": audience, "date": day})
    return (
        f"{pdf_report.PUBLIC_APP_URL}/insights?{query}",
        f"{pdf_report.PUBLIC_APP_URL}/api/insights/report.pdf?{report_query}",
    )


def _event_url(item: dict[str, Any], day: str) -> str:
    events = list(item.get("events") or [])
    primary_event = next(
        (event for event in events if event.get("role") == "primary"),
        events[0] if events else {},
    )
    event_id = str(primary_event.get("event_id") or "")
    if not event_id:
        return f"{pdf_report.PUBLIC_APP_URL}/insights"
    return (
        f"{pdf_report.PUBLIC_APP_URL}/evidence/feed?"
        f"{urlencode({'date': day, 'event_id': event_id})}"
    )


def _slack_escape(value: Any) -> str:
    return _plain(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _trim(value: Any, limit: int) -> str:
    text = _plain(value)
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


def _slack_payload(payload: dict[str, Any]) -> dict[str, Any]:
    items = _top_items(payload)
    day = str(payload.get("date") or payload.get("requested_date") or "")
    audience = _audience_label(str(payload.get("audience") or "investment"))
    brief_url, report_url = _urls(payload)
    fallback_lines = [
        f"Frontier Lab Intelligence - {audience} Daily Brief - {_display_day(day)}",
    ]
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{audience} Daily Intelligence", "emoji": False},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*{_display_day(day)}* · Top {len(items)} cited Insights",
                }
            ],
        },
        {"type": "divider"},
    ]
    for item in items:
        rank = int(item.get("rank") or 0)
        title = _slack_escape(item.get("title"))
        interpretation = _slack_escape(_trim(item.get("interpretation"), 240))
        event_url = _event_url(item, day)
        fallback_lines.append(f"{rank}. {_plain(item.get('title'))} - {_trim(item.get('interpretation'), 180)}")
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*<{event_url}|{rank}. {title}>*\n{interpretation}",
                },
            }
        )
    blocks.extend(
        [
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Open brief", "emoji": False},
                        "url": brief_url,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Download PDF", "emoji": False},
                        "url": report_url,
                    },
                ],
            },
        ]
    )
    fallback_lines.extend([f"Open brief: {brief_url}", f"Download PDF: {report_url}"])
    return {"text": "\n".join(fallback_lines), "blocks": blocks}


def _email_content(payload: dict[str, Any]) -> tuple[str, str, str]:
    items = _top_items(payload)
    day = str(payload.get("date") or payload.get("requested_date") or "")
    audience = _audience_label(str(payload.get("audience") or "investment"))
    brief_url, report_url = _urls(payload)
    subject = f"{audience} Daily Intelligence - {_display_day(day)}"
    plain_lines = [
        subject,
        "",
        f"The top {len(items)} cited Insights are below. The complete brief is attached as a PDF.",
        "",
    ]
    html_items: list[str] = []
    for item in items:
        rank = int(item.get("rank") or 0)
        title = _plain(item.get("title"))
        interpretation = _plain(item.get("interpretation"))
        next_step = _plain(item.get("next_step"))
        event_url = _event_url(item, day)
        plain_lines.extend(
            [
                f"{rank}. {title}",
                interpretation,
                f"Next: {next_step}",
                f"Evidence: {event_url}",
                "",
            ]
        )
        html_items.append(
            "".join(
                [
                    '<li style="margin:0 0 24px;padding:0 0 20px;border-bottom:1px solid #e4e4e2">',
                    f'<h2 style="margin:0 0 8px;font-size:18px;line-height:1.3"><a href="{html.escape(event_url)}" style="color:#235165;text-decoration:none">{rank}. {html.escape(title)}</a></h2>',
                    f'<p style="margin:0 0 8px;color:#434343;line-height:1.55">{html.escape(interpretation)}</p>',
                    f'<p style="margin:0;color:#151515;line-height:1.55"><strong>Next:</strong> {html.escape(next_step)}</p>',
                    "</li>",
                ]
            )
        )
    plain_lines.extend([f"Open brief: {brief_url}", f"Download PDF: {report_url}"])
    html_body = "".join(
        [
            '<!doctype html><html><body style="margin:0;background:#f7f7f6;color:#151515;font-family:Arial,sans-serif">',
            '<div style="max-width:680px;margin:0 auto;padding:36px 28px;background:#ffffff">',
            '<div style="width:12px;height:12px;background:#5bc5f2;margin-bottom:24px"></div>',
            f'<p style="margin:0 0 6px;color:#6b6b68;font-size:12px;letter-spacing:.04em;text-transform:uppercase">Frontier Lab Intelligence · {html.escape(_display_day(day))}</p>',
            f'<h1 style="margin:0 0 12px;font-size:30px;line-height:1.15">{html.escape(audience)} Daily Intelligence</h1>',
            f'<p style="margin:0 0 28px;color:#434343;line-height:1.55">The top {len(items)} cited Insights are below. The complete brief is attached as a PDF.</p>',
            f'<ol style="margin:0;padding:0;list-style:none">{"".join(html_items)}</ol>',
            '<p style="margin:28px 0 0">',
            f'<a href="{html.escape(brief_url)}" style="display:inline-block;margin-right:10px;padding:11px 15px;background:#151515;color:#ffffff;text-decoration:none">Open brief</a>',
            f'<a href="{html.escape(report_url)}" style="display:inline-block;padding:10px 14px;border:1px solid #151515;color:#151515;text-decoration:none">Download PDF</a>',
            "</p></div></body></html>",
        ]
    )
    return subject, "\n".join(plain_lines), html_body


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


def _send_email(
    settings: DeliverySettings,
    payload: dict[str, Any],
    artifact: pdf_report.ReportArtifact,
    *,
    smtp_factory: Callable[..., Any] = smtplib.SMTP,
) -> str:
    if not settings.email_recipients or not settings.smtp_password:
        raise DeliveryNotConfigured("Email delivery is not configured.")
    subject, plain_body, html_body = _email_content(payload)
    message_id = make_msgid()
    message = EmailMessage()
    message["Message-ID"] = message_id
    message["Date"] = formatdate(localtime=True)
    message["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_email))
    message["To"] = ", ".join(settings.email_recipients)
    message["Subject"] = subject
    if settings.smtp_reply_to:
        message["Reply-To"] = settings.smtp_reply_to
    message.set_content(plain_body)
    message.add_alternative(html_body, subtype="html")
    message.add_attachment(
        artifact.path.read_bytes(),
        maintype="application",
        subtype="pdf",
        filename=artifact.filename,
    )
    try:
        with smtp_factory(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.timeout_seconds,
        ) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(
                message,
                from_addr=settings.smtp_from_email,
                to_addrs=list(settings.email_recipients),
            )
    except (OSError, smtplib.SMTPException) as exc:
        raise DeliveryFailed("The email provider could not send the Daily Brief.") from exc
    return message_id.strip("<>")


def delivery_status_payload(
    payload: dict[str, Any],
    *,
    settings: DeliverySettings | None = None,
    remote_host: str | None = None,
) -> dict[str, Any]:
    resolved = settings or DeliverySettings.from_environment()
    available = bool(payload.get("content_kind") == "daily_editorial" and payload.get("available"))
    access_ready = _public_access_ready(resolved, remote_host)
    channels = []
    for channel, label, pdf_delivery in (
        ("slack", "Slack", "link"),
        ("email", "Email", "attachment"),
    ):
        configured = resolved.channel_configured(channel)
        channels.append(
            {
                "channel": channel,
                "label": label,
                "configured": configured,
                "available": bool(available and configured and access_ready),
                "destination": resolved.destination_label(channel) if configured else "Not configured",
                "pdf_delivery": pdf_delivery,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "available": available,
        "reason": None if available else str(payload.get("reason") or "No complete Daily Brief is available."),
        "audience": payload.get("audience"),
        "date": payload.get("date") or payload.get("requested_date"),
        "top_insight_count": len(_top_items(payload)) if available else 0,
        "access": {
            "required": not _is_loopback(remote_host),
            "configured": access_ready,
        },
        "channels": channels,
    }


def deliver_daily_brief(
    payload: dict[str, Any],
    *,
    channel: DeliveryChannel,
    authorization: str | None,
    remote_host: str | None,
    settings: DeliverySettings | None = None,
    cache_root: Path = pdf_report.DEFAULT_CACHE_ROOT,
    slack_transport: httpx.BaseTransport | None = None,
    smtp_factory: Callable[..., Any] = smtplib.SMTP,
) -> dict[str, Any]:
    resolved = settings or DeliverySettings.from_environment()
    _authorize(resolved, remote_host=remote_host, authorization=authorization)
    if payload.get("content_kind") != "daily_editorial" or not payload.get("available"):
        raise DeliveryNotConfigured(
            str(payload.get("reason") or "No complete Daily Brief is available for delivery.")
        )
    if not resolved.channel_configured(channel):
        raise DeliveryNotConfigured(f"{channel.title()} delivery is not configured.")

    artifact = pdf_report.get_or_create_report(payload, cache_root=cache_root)
    if channel == "slack":
        provider_id = _send_slack(resolved, payload, transport=slack_transport)
        pdf_delivery = "link"
    else:
        provider_id = _send_email(
            resolved,
            payload,
            artifact,
            smtp_factory=smtp_factory,
        )
        pdf_delivery = "attachment"

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
        "insight_count": len(_top_items(payload)),
        "pdf_delivery": pdf_delivery,
        "pdf_filename": artifact.filename,
        "report_version": artifact.report_version,
        "delivery_id": delivery_identity,
        "provider_id": provider_id,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
