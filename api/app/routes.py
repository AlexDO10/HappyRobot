"""HTTP routes — the three tools the HappyRobot agent calls mid-conversation.

All POST JSON, all behind the shared API key. Request shapes match the agent's
tool definitions exactly.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.models import (
    EvaluateOfferRequest,
    EvaluateOfferResponse,
    GetLoadsRequest,
    GetLoadsResponse,
    VerifyMcRequest,
    VerifyMcResponse,
)
from app.security import require_api_key
from app.services import fmcsa, negotiation
from app.stores import loads_store

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/get_loads", response_model=GetLoadsResponse, tags=["loads"])
def get_loads(body: GetLoadsRequest) -> GetLoadsResponse:
    loads = loads_store.search_loads(body.origin, body.destination, body.equipment_type)
    return GetLoadsResponse(loads=loads)


@router.post("/verify_mc", response_model=VerifyMcResponse, tags=["carriers"])
async def verify_mc(body: VerifyMcRequest) -> VerifyMcResponse:
    return await fmcsa.verify_mc(body.mc_number)


@router.post(
    "/evaluate_offer",
    response_model=EvaluateOfferResponse,
    response_model_exclude_none=True,
    tags=["negotiation"],
)
def evaluate_offer(body: EvaluateOfferRequest) -> EvaluateOfferResponse:
    load = loads_store.get_load(body.load_id)
    if not load:
        raise HTTPException(status_code=404, detail="Load not found.")
    return negotiation.evaluate_offer(load, body.carrier_offer, body.round)
