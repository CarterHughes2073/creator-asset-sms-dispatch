from fastapi import FastAPI, HTTPException

from .campaign_delivery import CampaignRequest, CampaignResult, deliver_campaign
from .infrai_sms import InfraiError, InfraiSms

app = FastAPI(title="Creator asset SMS dispatch")


@app.post("/campaigns/send", response_model=CampaignResult)
def send_campaign(request: CampaignRequest) -> CampaignResult:
    try:
        with InfraiSms() as sms:
            return deliver_campaign(request, sms)
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
