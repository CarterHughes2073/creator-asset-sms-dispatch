from creator_asset_sms.campaign_delivery import CampaignRequest, deliver_campaign


class RecordingSms:
    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def send(self, *, to: str, message: str, idempotency_key: str) -> dict:
        self.sent.append(
            {"to": to, "message": message, "idempotency_key": idempotency_key}
        )
        return {"message_id": "msg_42"}

    def status(self, message_id: str) -> dict:
        assert message_id == "msg_42"
        return {"status": "queued"}


def test_sends_ready_asset_only_to_subscribed_recipients() -> None:
    gateway = RecordingSms()
    request = CampaignRequest.model_validate(
        {
            "campaign_id": "creator-drop-7",
            "creator_name": "Mira Studio",
            "asset": {
                "title": "Agent Prompt Pack",
                "download_url": "https://downloads.example.com/prompt-pack",
                "processing_state": "ready",
            },
            "subscribers": [
                {
                    "subscriber_id": "active-1",
                    "phone": "+15551234567",
                    "first_name": "Ada",
                    "subscribed": True,
                },
                {
                    "subscriber_id": "paused-2",
                    "phone": "+15557654321",
                    "first_name": "Lin",
                    "subscribed": False,
                },
            ],
        }
    )

    result = deliver_campaign(request, gateway)

    assert result.sent[0].model_dump() == {
        "subscriber_id": "active-1",
        "message_id": "msg_42",
        "status": "queued",
    }
    assert result.skipped_subscriber_ids == ["paused-2"]
    assert gateway.sent == [
        {
            "to": "+15551234567",
            "message": (
                "Hi Ada, Mira Studio released Agent Prompt Pack: "
                "https://downloads.example.com/prompt-pack"
            ),
            "idempotency_key": "creator-drop-7:active-1",
        }
    ]
