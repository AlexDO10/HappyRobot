"""Test matrix for the manipulation-proof pricing core.

Uses a fixed load: base (loadboard_rate) = 1000, ceiling (max_buy_rate) = 2000,
so gap = 1000 and the allowed-per-round numbers are clean:
    round 1 -> 1000 + 1000*0.50 = 1500
    round 2 -> 1000 + 1000*0.80 = 1800
    round 3 -> 1000 + 1000*1.00 = 2000  (== ceiling)
"""

from app.models import Decision, Load
from app.services.negotiation import evaluate_offer

BASE = 1000.0
CEILING = 2000.0


def _load() -> Load:
    return Load(
        load_id="LD-TEST",
        origin="A",
        destination="B",
        pickup_datetime="2026-06-10T08:00:00",
        delivery_datetime="2026-06-11T08:00:00",
        equipment_type="Dry Van",
        loadboard_rate=BASE,
        max_buy_rate=CEILING,
    )


def test_offer_below_allowed_accepts_at_offer():
    # round 1 allowed = 1500; carrier asks 1300 -> accept at THEIR number.
    res = evaluate_offer(_load(), carrier_offer=1300, round_num=1)
    assert res.decision == Decision.accept
    assert res.agreed_rate == 1300
    assert res.counter_offer is None


def test_offer_at_allowed_accepts():
    res = evaluate_offer(_load(), carrier_offer=1500, round_num=1)
    assert res.decision == Decision.accept
    assert res.agreed_rate == 1500


def test_round1_above_allowed_below_ceiling_counters_at_allowed():
    # 1700 > 1500 allowed, below ceiling -> counter at 1500.
    res = evaluate_offer(_load(), carrier_offer=1700, round_num=1)
    assert res.decision == Decision.counter
    assert res.counter_offer == 1500
    assert res.agreed_rate is None


def test_round2_above_allowed_below_ceiling_counters_at_allowed():
    # 1900 > 1800 allowed, below ceiling -> counter at 1800.
    res = evaluate_offer(_load(), carrier_offer=1900, round_num=2)
    assert res.decision == Decision.counter
    assert res.counter_offer == 1800


def test_round3_above_ceiling_walks():
    # round 3, 2100 > ceiling 2000, out of rounds -> walk.
    res = evaluate_offer(_load(), carrier_offer=2100, round_num=3)
    assert res.decision == Decision.walk
    assert res.agreed_rate is None
    assert res.counter_offer is None


def test_round3_exactly_at_ceiling_accepts():
    # round 3 allowed == ceiling == 2000; offer exactly 2000 -> accept.
    res = evaluate_offer(_load(), carrier_offer=2000, round_num=3)
    assert res.decision == Decision.accept
    assert res.agreed_rate == 2000


def test_round3_never_counters():
    # Even just above allowed, the final round can only accept or walk.
    res = evaluate_offer(_load(), carrier_offer=2000.01, round_num=3)
    assert res.decision == Decision.walk


def test_decreasing_step_values_per_round():
    # The allowed ceiling per round follows 50% / 80% / 100% of the gap.
    # Probe by offering 1 cent above each round's allowed and reading the counter
    # (rounds 1-2) or confirming accept at the exact allowed (round 3).
    assert evaluate_offer(_load(), 1500.01, 1).counter_offer == 1500
    assert evaluate_offer(_load(), 1800.01, 2).counter_offer == 1800
    assert evaluate_offer(_load(), 2000.00, 3).agreed_rate == 2000


def test_round_is_clamped():
    # round 0 clamps to 1, round 99 clamps to the final round.
    assert evaluate_offer(_load(), 1500, 0).decision == Decision.accept  # allowed=1500
    res = evaluate_offer(_load(), 2100, 99)
    assert res.decision == Decision.walk  # treated as final round


def test_request_carries_no_ceiling():
    # Sanity: the function signature takes only the load, offer, and round —
    # no caller-supplied max/limit can influence the ceiling.
    import inspect

    params = set(inspect.signature(evaluate_offer).parameters)
    assert params == {"load", "carrier_offer", "round_num"}
