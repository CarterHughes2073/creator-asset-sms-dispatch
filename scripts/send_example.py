from creator_asset_sms.campaign_delivery import (
    AssetDelivery,
    CampaignRequest,
    SubscriberUpdate,
    deliver_campaign,
)
from creator_asset_sms.infrai_sms import InfraiSms


request = CampaignRequest(
    campaign_id="studio-drop-2026-08",
    creator_name="Mira Studio",
    asset=AssetDelivery(
        title="Agent Prompt Pack",
        download_url="https://downloads.example.com/prompt-pack",
        processing_state="ready",
    ),
    subscribers=[
        SubscriberUpdate(
            subscriber_id="sub-1042",
            phone="+15551234567",
            first_name="Ada",
            subscribed=True,
        )
    ],
)

with InfraiSms() as infrai:
    result = deliver_campaign(request, infrai)

print(result.model_dump_json(indent=2))
