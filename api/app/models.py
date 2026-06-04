"""Pydantic schemas for the inbound carrier sales API.

Request/response shapes match the HappyRobot agent's tool definitions exactly.

CRITICAL INVARIANT: `max_buy_rate` is the broker's hidden walk-away ceiling.
It lives on the internal `Load` model only. `LoadPublic` — the only load shape
that ever leaves the server — does NOT contain it. If `max_buy_rate` appears in
any response body, the design is broken.
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Loads
# --------------------------------------------------------------------------- #
class Load(BaseModel):
    """Internal load record. Includes the hidden ceiling — never serialized out."""

    load_id: str
    origin: str
    destination: str
    pickup_datetime: datetime
    delivery_datetime: datetime
    equipment_type: str
    loadboard_rate: float
    max_buy_rate: float  # hidden walk-away ceiling — server-side only
    notes: str = ""
    weight: float | None = None
    commodity_type: str | None = None
    num_of_pieces: int | None = None
    miles: float | None = None
    dimensions: str | None = None

    def public(self) -> "LoadPublic":
        data = self.model_dump()
        data.pop("max_buy_rate", None)
        return LoadPublic(**data)


class LoadPublic(BaseModel):
    """The only load shape returned to callers — `max_buy_rate` is absent."""

    load_id: str
    origin: str
    destination: str
    pickup_datetime: datetime
    delivery_datetime: datetime
    equipment_type: str
    loadboard_rate: float
    notes: str = ""
    weight: float | None = None
    commodity_type: str | None = None
    num_of_pieces: int | None = None
    miles: float | None = None
    dimensions: str | None = None


class GetLoadsRequest(BaseModel):
    origin: str | None = None
    destination: str | None = None
    equipment_type: str | None = None


class GetLoadsResponse(BaseModel):
    loads: list[LoadPublic]


# --------------------------------------------------------------------------- #
# Carrier verification (FMCSA)
# --------------------------------------------------------------------------- #
class VerifyMcRequest(BaseModel):
    mc_number: str = Field(..., description="Carrier MC docket number, digits only.")


class VerifyMcResponse(BaseModel):
    status: Literal["eligible", "not_eligible", "not_found"]
    legal_name: str | None = None


# --------------------------------------------------------------------------- #
# Offer evaluation (the only pricing authority)
# --------------------------------------------------------------------------- #
class EvaluateOfferRequest(BaseModel):
    load_id: str
    carrier_offer: float
    round: int


class Decision(str, Enum):
    accept = "accept"
    counter = "counter"
    walk = "walk"


class EvaluateOfferResponse(BaseModel):
    """Exactly one decision. Unused fields are omitted on serialization."""

    decision: Decision
    agreed_rate: float | None = None
    counter_offer: float | None = None
