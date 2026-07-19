# Daily Brief delivery

Frontier Lab Intelligence can manually send any complete audience-specific
Daily Brief from the Insights page. Delivery reuses the same canonical brief
and cached PDF as the web reader. It does not create a separate report.

## Reader flow

The `Send brief` action is available only when the selected date and audience
have a complete editorial run and the chosen provider is configured.

1. The operator chooses Slack or email.
2. The panel shows the masked destination, audience, date, and content scope.
3. A separate confirmation performs the real provider action.
4. Success or provider failure remains visible in the same panel.

Slack sends every cited Insight in rank order. Each item includes its linked
title and complete interpretation. The message ends with links to the full web
brief and PDF.

Email sends up to five ranked Insights with their interpretations, next steps,
and exact Feed Event links. The complete audience PDF is attached. The body
also links to the web brief and downloadable PDF.

## Runtime boundary

`GET /api/insights/delivery` reports channel availability and masked destination
labels. It never returns provider credentials. `POST /api/insights/delivery`
accepts the audience, date, and channel after the UI confirmation.

Production browser sends require an `Origin` hostname matching the application
hostname. This blocks cross-site browser requests, but it is not user
authentication, rate limiting, or duplicate-send protection. Anyone who can
open the public application can confirm a configured send. Provider secrets
remain server-side.

There is deliberately no schedule, unattended alert loop, provider settings
page, or delivery-history store. The submission proves the cited push adapters;
automation and stronger access control are documented next steps.

The public reviewer release sets `FLI_READ_ONLY=1`. In that mode, delivery
status ignores local provider credentials and the POST route returns `403`, so
the downloadable demo cannot send a real message. The same boundary also
disables Registry intake.

## Configuration

Canonical secret values live in Azure Key Vault. Local development maps those
same values into the generated, ignored `.env` file through
`scripts/local/secrets/keyvault_env_map.env` and
`scripts/local/secrets/bootstrap_local_env_from_keyvault.sh`. Never put literal
secret values in tracked files.

Required secret-backed variables:

- `FLI_SLACK_WEBHOOK_URL` enables Slack delivery.
- `ACS_SMTP_PASS` enables authenticated email delivery when a recipient exists.

Optional non-secret settings:

- `FLI_DELIVERY_SLACK_LABEL`
- `FLI_DELIVERY_EMAIL_TO`
- `FLI_DELIVERY_EMAIL_LABEL`
- `FLI_DELIVERY_TIMEOUT_SECONDS`
- `ACS_SMTP_HOST`
- `ACS_SMTP_PORT`
- `ACS_SMTP_USER`
- `ACS_SMTP_FROM_EMAIL`
- `ACS_SMTP_FROM_NAME`
- `ACS_SMTP_REPLY_TO`

Without overrides, email targets `adi@aipodcast.ing` through the shared Azure
Communication Services SMTP defaults. The browser displays only the masked
recipient.

## Proof and validation

On 19 July 2026, Adi confirmed real Slack webhook delivery and real email
delivery with the generated PDF attached. Automated coverage in
`tests/delivery/test_daily_brief.py` verifies:

- complete Slack content across a six-Insight fixture;
- Slack section-size limits and secret redaction;
- email top-five selection and PDF attachment;
- configured and unavailable channel status;
- same-origin acceptance and cross-site rejection.

Run `scripts/check-fast.sh` for the complete repository gate. A read-only
configuration check is available at:

```text
GET /api/insights/delivery?audience=investment&date=2026-07-17
```

Do not call the POST route during validation unless a real external send is
explicitly intended.
