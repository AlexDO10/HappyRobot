"""SQLite-backed store for call results + aggregated metrics.

This powers the analytics dashboard. The HappyRobot agent POSTs one record per
call to /call_results; the dashboard reads /metrics and /call_results.

On Fly the DB file lives on a mounted volume (see fly.toml) so data survives
restarts and redeploys. For consistent metrics the app runs as a single machine
(SQLite is local to its volume; multiple machines would each keep separate data).
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.models import CallOutcome, CallResult, CallResultCreate, FunnelStage, Metrics, Sentiment
from app.stores import loads_store

_SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    mc_number           TEXT,
    load_id             TEXT,
    outcome             TEXT NOT NULL,
    sentiment           TEXT NOT NULL,
    final_rate          REAL,
    negotiation_rounds  INTEGER NOT NULL DEFAULT 0,
    transcript_summary  TEXT,
    transferred         INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    db_path = Path(get_settings().calls_db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Idempotent: guarantees the table exists even if init_db() wasn't called
    # (e.g. under TestClient without lifespan).
    conn.executescript(_SCHEMA)
    # Lightweight migration: add `transferred` to pre-existing tables.
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(calls)").fetchall()}
    if "transferred" not in cols:
        conn.execute("ALTER TABLE calls ADD COLUMN transferred INTEGER NOT NULL DEFAULT 0")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)


def add_call(record: CallResultCreate) -> CallResult:
    created_at = datetime.now(timezone.utc)
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO calls
                (mc_number, load_id, outcome, sentiment, final_rate,
                 negotiation_rounds, transcript_summary, transferred, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.mc_number,
                record.load_id,
                record.outcome.value,
                record.sentiment.value,
                record.final_rate,
                record.negotiation_rounds,
                record.transcript_summary,
                int(record.transferred),
                created_at.isoformat(),
            ),
        )
        new_id = cur.lastrowid
    return CallResult(id=new_id, created_at=created_at, **record.model_dump())


def list_calls(limit: int = 100) -> list[CallResult]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM calls ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_record(r) for r in rows]


def compute_metrics() -> Metrics:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM calls").fetchall()

    total = len(rows)
    outcomes = {o.value: 0 for o in CallOutcome}
    sentiments = {s.value: 0 for s in Sentiment}
    rounds_sum = 0
    rate_sum = 0.0
    rate_count = 0

    # Negotiation effectiveness accumulators (booked loads only).
    markup_sum = 0.0
    savings_sum = 0.0
    gap_pct_sum = 0.0
    effectiveness_count = 0
    transferred = 0

    for r in rows:
        outcomes[r["outcome"]] = outcomes.get(r["outcome"], 0) + 1
        sentiments[r["sentiment"]] = sentiments.get(r["sentiment"], 0) + 1
        rounds_sum += r["negotiation_rounds"] or 0
        # Treat final_rate=0 as missing — the agent sometimes sends 0 as a
        # default when nothing was booked, which would corrupt the averages.
        valid_rate = r["final_rate"] if (r["final_rate"] is not None and r["final_rate"] > 0) else None
        if valid_rate is not None:
            rate_sum += valid_rate
            rate_count += 1

        is_booked = r["outcome"] == CallOutcome.booked.value
        if is_booked and r["transferred"]:
            transferred += 1

        # Join booked calls with their load to measure how good the deal was.
        # Only count rows with a real positive rate to avoid corrupting averages.
        if is_booked and valid_rate is not None and r["load_id"]:
            load = loads_store.get_load(r["load_id"])
            if load:
                final = valid_rate
                markup_sum += final - load.loadboard_rate
                savings_sum += load.max_buy_rate - final
                gap = load.max_buy_rate - load.loadboard_rate
                if gap > 0:
                    gap_pct_sum += (final - load.loadboard_rate) / gap
                effectiveness_count += 1

    booked = outcomes.get(CallOutcome.booked.value, 0)
    not_eligible = outcomes.get(CallOutcome.not_eligible.value, 0)
    no_match = outcomes.get(CallOutcome.no_load_match.value, 0)
    eligible = total - not_eligible
    matched = eligible - no_match

    funnel = [
        FunnelStage(stage="Total calls", count=total),
        FunnelStage(stage="Eligible", count=eligible),
        FunnelStage(stage="Load matched", count=matched),
        FunnelStage(stage="Booked", count=booked),
    ]

    n = effectiveness_count
    return Metrics(
        total_calls=total,
        booked=booked,
        booking_rate=round(booked / total, 3) if total else 0.0,
        avg_negotiation_rounds=round(rounds_sum / total, 2) if total else 0.0,
        avg_final_rate=round(rate_sum / rate_count, 2) if rate_count else None,
        outcomes=outcomes,
        sentiments=sentiments,
        funnel=funnel,
        avg_markup_over_loadboard=round(markup_sum / n, 2) if n else None,
        avg_savings_vs_ceiling=round(savings_sum / n, 2) if n else None,
        avg_gap_captured_pct=round(gap_pct_sum / n, 3) if n else None,
        transferred=transferred,
        transfer_rate=round(transferred / booked, 3) if booked else 0.0,
    )


def _row_to_record(r: sqlite3.Row) -> CallResult:
    return CallResult(
        id=r["id"],
        mc_number=r["mc_number"],
        load_id=r["load_id"],
        outcome=CallOutcome(r["outcome"]),
        sentiment=Sentiment(r["sentiment"]),
        final_rate=r["final_rate"],
        negotiation_rounds=r["negotiation_rounds"],
        transcript_summary=r["transcript_summary"],
        transferred=bool(r["transferred"]),
        created_at=datetime.fromisoformat(r["created_at"]),
    )
