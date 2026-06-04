"""FMCSA carrier eligibility lookup behind a small client interface.

MOCK mode (FMCSA_MODE=mock, the default) behaves like a small registry: only the
MC numbers explicitly listed in _MOCK_CARRIERS resolve, and every other number
returns "not_found". This keeps the demo deterministic and avoids depending on a
live FMCSA key or FMCSA uptime.

LIVE mode (FMCSA_MODE=live) calls the FMCSA QCMobile API by docket number with
a server-side webkey, mapping the response to three statuses:
  found + allowedToOperate == "Y"  -> eligible
  found + allowedToOperate != "Y"  -> not_eligible
  not found / error                -> not_found

Verified against FMCSA QCMobile docs (mobile.fmcsa.dot.gov/QCDevsite/docs):
  GET /qc/services/carriers/docket-number/{n}?webKey=...
  -> { "content": [ { "carrier": { "allowedToOperate": "Y", "legalName": ... } } ] }
"""

import httpx

from app.config import get_settings
from app.models import VerifyMcResponse

_FMCSA_BASE = "https://mobile.fmcsa.dot.gov/qc/services"

# Canned results for mock mode, keyed by MC number (digits only).
_MOCK_CARRIERS: dict[str, VerifyMcResponse] = {
    "123456": VerifyMcResponse(status="eligible", legal_name="Mock Freight Lines LLC"),
    "111111": VerifyMcResponse(status="eligible", legal_name="Acme Carriers Inc"),
    "222222": VerifyMcResponse(status="not_eligible", legal_name="Out Of Service Trucking LLC"),
    "000000": VerifyMcResponse(status="not_found"),
}


async def verify_mc(mc_number: str) -> VerifyMcResponse:
    digits = "".join(c for c in mc_number if c.isdigit())
    if get_settings().fmcsa_is_mock:
        return _mock_verify(digits)
    return await _live_verify(digits)


def _mock_verify(digits: str) -> VerifyMcResponse:
    # Mock mode acts like a registry: only explicitly known MC numbers resolve.
    # Anything else is treated as not in the system.
    return _MOCK_CARRIERS.get(digits, VerifyMcResponse(status="not_found"))


async def _live_verify(digits: str) -> VerifyMcResponse:
    if not digits:
        return VerifyMcResponse(status="not_found")
    url = f"{_FMCSA_BASE}/carriers/docket-number/{digits}"
    params = {"webKey": get_settings().fmcsa_webkey}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return VerifyMcResponse(status="not_found")

    content = data.get("content")
    if not content:
        return VerifyMcResponse(status="not_found")
    first = content[0] if isinstance(content, list) else content
    carrier = first.get("carrier", {}) if isinstance(first, dict) else {}
    if not carrier:
        return VerifyMcResponse(status="not_found")

    legal_name = carrier.get("legalName")
    if carrier.get("allowedToOperate") == "Y":
        return VerifyMcResponse(status="eligible", legal_name=legal_name)
    return VerifyMcResponse(status="not_eligible", legal_name=legal_name)
