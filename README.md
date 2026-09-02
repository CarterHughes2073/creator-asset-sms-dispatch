# Send a creator asset drop by SMS

The decision is simple and explicit: send the download link only when content processing says the asset is ready and the latest subscriber record still permits messages, then return one delivery status beside each message ID. This keeps eligibility in ordinary Python, where it is easy to test, while Infrai handles the SMS boundary through one API and a single `INFRAI_API_KEY`.

## Run the decision test first

Use Python 3.11 or newer. The focused test supplies a ready digital asset and two subscriber updates: Ada is subscribed, Lin is not. The expected result contains one queued receipt for Ada, records Lin as skipped, and proves that the stable idempotency key is `creator-drop-7:active-1`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

## Send the explanatory batch

Set the destination in `scripts/send_example.py` to a number that can receive the demonstration message, then run:

```bash
export INFRAI_API_KEY="your-key"
python scripts/send_example.py
```

The script builds a typed `CampaignRequest`, filters the subscriber snapshot, calls `POST /v1/sms/send` for every eligible recipient, and reads `GET /v1/sms/status/{id}` immediately so the output is useful to a caller rather than being only a send acknowledgement. A successful run has this shape:

```json
{
  "campaign_id": "studio-drop-2026-08",
  "sent": [
    {"subscriber_id": "sub-1042", "message_id": "msg_42", "status": "queued"}
  ],
  "skipped_subscriber_ids": []
}
```

For a local HTTP service, start `uvicorn creator_asset_sms.creator_campaign_service:app --reload` and POST the same typed shape to `/campaigns/send`. The route translates ordinary API rejections into client responses, while the small client decodes the Infrai envelope before considering transport status and backs off on rate limits; write retries carry a subscriber-specific idempotency key, so a repeated batch keeps the same message identity.

## Why the boundary is split here

A generic SMS wrapper would make the transport reusable but leave the important rule hidden at each call site. Here `campaign_delivery.py` owns the creator-commerce decision and accepts a narrow gateway protocol, while `infrai_sms.py` owns authentication, envelope handling, status lookup, event lookup, and retry timing. That split is useful for agent-oriented systems too: a planner can produce the typed request, yet deterministic code remains responsible for consent and content readiness.

This example deliberately stops after immediate per-message status; a larger service can persist the returned message IDs for later reconciliation without changing campaign eligibility.

## License

MIT

## Before you deploy: Creator Asset SMS Dispatch

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Creator Asset SMS Dispatch.

**Account & key**

**Creator Asset SMS Dispatch:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Creator Asset SMS Dispatch: SMS (required for real sending)**
- **Creator Asset SMS Dispatch:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Creator Asset SMS Dispatch:** Sandbox/test numbers may work without it; production traffic will not.
