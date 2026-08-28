from __future__ import annotations

from typing import Literal, Protocol, get_args, get_origin, get_type_hints
import re

try:
    from pydantic import BaseModel, Field
except ModuleNotFoundError:  # Keep the decision logic runnable in the minimal test venv.
    class _Field:
        def __init__(self, **constraints: object) -> None:
            self.constraints = constraints

    def Field(**constraints: object) -> _Field:
        return _Field(**constraints)

    class BaseModel:
        def __init__(self, **values: object) -> None:
            hints = get_type_hints(type(self))
            for name, hint in hints.items():
                if name not in values:
                    raise ValueError(f"missing field: {name}")
                value = values[name]
                if isinstance(value, dict) and isinstance(hint, type) and issubclass(hint, BaseModel):
                    value = hint.model_validate(value)
                elif get_origin(hint) is list:
                    item_type = get_args(hint)[0]
                    value = [item_type.model_validate(item) if isinstance(item, dict) else item for item in value]  # type: ignore[union-attr]
                field = getattr(type(self), name, None)
                constraints = getattr(field, "constraints", {})
                if isinstance(value, str):
                    if "min_length" in constraints and len(value) < constraints["min_length"]:
                        raise ValueError(f"{name} is too short")
                    if "max_length" in constraints and len(value) > constraints["max_length"]:
                        raise ValueError(f"{name} is too long")
                    if "pattern" in constraints and not re.search(str(constraints["pattern"]), value):
                        raise ValueError(f"{name} has invalid format")
                if isinstance(value, list) and ("min_length" in constraints or "max_length" in constraints):
                    if len(value) < constraints.get("min_length", 0) or len(value) > constraints.get("max_length", float("inf")):
                        raise ValueError(f"{name} has invalid length")
                setattr(self, name, value)

        @classmethod
        def model_validate(cls, value: object):
            if isinstance(value, cls):
                return value
            if not isinstance(value, dict):
                raise ValueError("expected an object")
            return cls(**value)

        def model_dump(self) -> dict[str, object]:
            result = {}
            for name in get_type_hints(type(self)):
                value = getattr(self, name)
                result[name] = [item.model_dump() if isinstance(item, BaseModel) else item for item in value] if isinstance(value, list) else (value.model_dump() if isinstance(value, BaseModel) else value)
            return result


class AssetDelivery(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    download_url: str = Field(pattern=r"^https://")
    processing_state: Literal["ready", "processing"]


class SubscriberUpdate(BaseModel):
    subscriber_id: str = Field(min_length=1)
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    first_name: str = Field(min_length=1, max_length=40)
    subscribed: bool


class CampaignRequest(BaseModel):
    campaign_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_-]+$")
    creator_name: str = Field(min_length=1, max_length=60)
    asset: AssetDelivery
    subscribers: list[SubscriberUpdate] = Field(min_length=1, max_length=100)


class MessageReceipt(BaseModel):
    subscriber_id: str
    message_id: str
    status: str


class CampaignResult(BaseModel):
    campaign_id: str
    sent: list[MessageReceipt]
    skipped_subscriber_ids: list[str]


class SmsGateway(Protocol):
    def send(self, *, to: str, message: str, idempotency_key: str) -> dict:
        """Send one campaign message and return its API data."""

    def status(self, message_id: str) -> dict:
        """Return the current API data for one message."""


def deliver_campaign(request: CampaignRequest, sms: SmsGateway) -> CampaignResult:
    if request.asset.processing_state != "ready":
        return CampaignResult(
            campaign_id=request.campaign_id,
            sent=[],
            skipped_subscriber_ids=[item.subscriber_id for item in request.subscribers],
        )

    sent: list[MessageReceipt] = []
    skipped: list[str] = []
    for subscriber in request.subscribers:
        if not subscriber.subscribed:
            skipped.append(subscriber.subscriber_id)
            continue

        message = (
            f"Hi {subscriber.first_name}, {request.creator_name} released "
            f"{request.asset.title}: {request.asset.download_url}"
        )
        reply = sms.send(
            to=subscriber.phone,
            message=message,
            idempotency_key=f"{request.campaign_id}:{subscriber.subscriber_id}",
        )
        message_id = str(reply["message_id"])
        delivery = sms.status(message_id)
        sent.append(
            MessageReceipt(
                subscriber_id=subscriber.subscriber_id,
                message_id=message_id,
                status=str(delivery["status"]),
            )
        )

    return CampaignResult(
        campaign_id=request.campaign_id,
        sent=sent,
        skipped_subscriber_ids=skipped,
    )
