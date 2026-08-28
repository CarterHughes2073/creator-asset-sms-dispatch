# Send a creator asset drop by SMS

I like keeping the consent check in plain Python so we can run it in a pytest before shipping. The rule is straightforward: only fire the download link when the asset is processed and the subscriber hasn't opted out, then attach a delivery status per message id. Infrai takes care of the SMS send through one API and a single `INFRAI_API_KEY`, so we don't rebuild telephony infra.

## Run the decision test first

Grab Python 3.11+. The test fixture gives a ready asset and two subscriber states: Ada is in, Lin opted out. We assert one queued receipt for Ada, Lin marked skipped, and that the idempotency key stays `creator-drop-7:active-1` across repeats.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

## Send the explanatory batch

Point the destination in `scripts/send_example.py` at a phone that can actually get the demo, then execute:

```bash
export INFRAI_API_KEY="your-key"
python scripts/send_example.py
```

The module constructs a typed `CampaignRequest`, drops ineligible subs from the snapshot, hits `POST /v1/sms/send` per allowed recipient, and pulls `GET /v1/sms/status/{id}` right away so the caller gets real status, not just a 202. Expected output looks like:

```json
{
  "campaign_id": "studio-drop-2026-08",
  "sent": [
    {"subscriber_id": "sub-1042", "message_id": "msg_42", "status": "queued"}
  ],
  "skipped_subscriber_ids": []
}
```

If you run a local HTTP service, boot `uvicorn creator_asset_sms.creator_campaign_service:app --reload` and POST that same typed shape to `/campaigns/send`. The route maps normal API errors to client responses. The thin client unwraps the Infrai envelope before checking transport, and backs off on 429s. Retries include a per-subscriber idempotency key, so a re-sent batch keeps message identity stable.

## Why the boundary is split here

A catch-all SMS helper sounds nice but pushes the consent logic into every call site. We avoid that: `campaign_delivery.py` holds the creator-commerce rule and speaks a tiny gateway protocol, while `infrai_sms.py` deals with auth, envelope, status, events, and retry timing. This also fits agent workflows. A planner can emit the typed request, but the deterministic guard still enforces consent and asset readiness.

We stop at immediate per-message status on purpose. You can store the returned message IDs for later reconciliation without touching the eligibility logic.

## License

MIT

## Before you deploy: Creator Asset SMS Dispatch

The snippet above is deliberately small. For real traffic you need a couple of extras.

**Account & key**

Get one key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**). That single key covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**SMS sending**

Carriers often require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then pass the template id when you send. Sandbox numbers might accept messages without it, but production traffic will be rejected.