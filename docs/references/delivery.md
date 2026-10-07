# Daily Brief delivery

Frontier Lab Intelligence can manually send any complete Investment or AI
Engineering brief to Slack from the Insights page. Delivery reuses the same
canonical brief as the web reader and does not create or link a PDF.

## Reader flow

The `Send brief` action is available only when the selected date has a complete
published cohort and the Slack webhook is configured.

1. The operator chooses Slack.
2. The panel shows the destination label, audience, date, and content scope.
3. A separate confirmation performs the real provider action.
4. Success or provider failure remains visible in the same panel.

Slack sends every surfaced Insight in brief order. The visible list is numbered
from one, independent of Feed rank. Each item includes its headline, complete
`What changed` text, and the memo-owned upside or downside direction for every
connected company. The message ends with one link to the full web brief; Slack
does not generate or link a PDF.

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

Canonical secret values live in the local `shared` scope. Local development maps those
same values into the generated, ignored `.env` file through
`scripts/local/secrets/secret_env_map.env` and
`scripts/local/secrets/bootstrap_local_env.sh`. Never put literal
secret values in tracked files.

Required secret-backed variable:

- `FLI_SLACK_WEBHOOK_URL` enables Slack delivery.

Optional non-secret settings:

- `FLI_DELIVERY_SLACK_LABEL`
- `FLI_DELIVERY_TIMEOUT_SECONDS`

Email delivery is not part of the current runtime. The API accepts only
`channel: "slack"`.

## Proof and validation

On 19 July 2026, Adi confirmed real Slack webhook delivery. Automated coverage
in `tests/delivery/test_daily_brief.py` verifies:

- complete Slack content across a six-Insight fixture;
- Slack section-size limits and secret redaction;
- Slack-only channel status and rejection of the retired email channel;
- same-origin acceptance and cross-site rejection.

Run `scripts/check-fast.sh` for the complete repository gate. A read-only
configuration check is available at:

```text
GET /api/insights/delivery?audience=investment&date=2026-07-17
```

Do not call the POST route during validation unless a real external send is
explicitly intended.
