"""HTTP routes — the three tools the HappyRobot agent calls mid-conversation.

All POST JSON, all behind the shared API key. Request shapes match the agent's
tool definitions exactly.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models import (
    CallResult,
    CallResultCreate,
    EvaluateOfferRequest,
    EvaluateOfferResponse,
    GetLoadsRequest,
    GetLoadsResponse,
    Metrics,
    VerifyMcRequest,
    VerifyMcResponse,
)
from app.security import require_api_key
from app.services import fmcsa, negotiation
from app.stores import calls_store, loads_store

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


# --------------------------------------------------------------------------- #
# Call results / analytics (powers the dashboard) — outside the core brief, but
# additive: these endpoints do not affect get_loads / verify_mc / evaluate_offer.
# --------------------------------------------------------------------------- #
@router.post("/call_results", response_model=CallResult, tags=["analytics"])
def log_call_result(body: CallResultCreate) -> CallResult:
    return calls_store.add_call(body)


@router.get("/call_results", response_model=list[CallResult], tags=["analytics"])
def list_call_results(limit: int = Query(100, ge=1, le=500)) -> list[CallResult]:
    return calls_store.list_calls(limit)


@router.get("/metrics", response_model=Metrics, tags=["analytics"])
def metrics() -> Metrics:
    return calls_store.compute_metrics()
