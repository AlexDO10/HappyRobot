"""Deterministic pricing authority.

This is the ONLY place pricing decisions are made. No LLM, no randomness. The
round cap is enforced HERE — the agent is not trusted to count rounds or hold
the line. The endpoint takes nothing from the caller except load_id, the
carrier's offer, and the round number; it never accepts a "max" or "limit".
"""

from app.config import get_settings
from app.models import Decision, EvaluateOfferResponse, Load


def evaluate_offer(load: Load, carrier_offer: float, round_num: int) -> EvaluateOfferResponse:
    fractions = get_settings().concession_fractions
    max_round = max(fractions)  # 3 with the default schedule

    base = load.loadboard_rate  # our opening offer (low)
    ceiling = load.max_buy_rate  # hidden walk-away max (base < ceiling)
    gap = ceiling - base

    # Clamp the round into the schedule's range; round 3 is the final round.
    round_num = max(1, min(round_num, max_round))

    # Highest we are willing to offer this round.
    allowed = round(base + gap * fractions[round_num], 2)

    if carrier_offer <= allowed:
        # They asked for <= what we'd pay — book at THEIR number (cheaper for us).
        return EvaluateOfferResponse(decision=Decision.accept, agreed_rate=carrier_offer)

    if round_num < max_round:
        # Can't meet them yet — counter at our round-N number.
        return EvaluateOfferResponse(decision=Decision.counter, counter_offer=allowed)

    # Final round, still above what we'll pay, out of rounds.
    return EvaluateOfferResponse(decision=Decision.walk)
