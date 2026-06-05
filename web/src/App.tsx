import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchCalls, fetchMetrics, type CallResult, type Metrics } from "./api";

const C = {
  ink: "#0f172a",
  muted: "#64748b",
  brand: "#4f46e5",
  pos: "#16a34a",
  neg: "#dc2626",
  warn: "#d97706",
  slate: "#64748b",
};

const OUTCOME_META: Record<string, { label: string; color: string }> = {
  booked: { label: "Booked", color: C.pos },
  no_agreement: { label: "No agreement", color: C.warn },
  not_eligible: { label: "Not eligible", color: C.neg },
  no_load_match: { label: "No load match", color: "#0ea5e9" },
  abandoned: { label: "Abandoned", color: "#94a3b8" },
};

const SENTIMENT_META: Record<string, { label: string; color: string }> = {
  positive: { label: "Positive", color: C.pos },
  neutral: { label: "Neutral", color: "#94a3b8" },
  negative: { label: "Negative", color: C.neg },
};

function Badge({ color, label }: { color: string; label: string }) {
  return (
    <span className="badge" style={{ background: `${color}1a`, color }}>
      <span className="dot" style={{ background: color }} />
      {label}
    </span>
  );
}

function Kpi({
  label,
  value,
  accent,
  hint,
}: {
  label: string;
  value: string | number;
  accent: string;
  hint?: string;
}) {
  return (
    <div className="card kpi" style={{ flex: 1, minWidth: 168, padding: "18px 20px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span className="dot" style={{ background: accent, width: 8, height: 8 }} />
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: 0.6,
            textTransform: "uppercase",
            color: C.muted,
          }}
        >
          {label}
        </span>
      </div>
      <div style={{ fontSize: 30, fontWeight: 800, color: C.ink, marginTop: 8, lineHeight: 1.1 }}>
        {value}
      </div>
      {hint && <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>{hint}</div>}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 style={{ margin: "0 0 4px", fontSize: 15, fontWeight: 700, color: C.ink }}>{children}</h3>
  );
}

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #e2e8f0",
        borderRadius: 10,
        padding: "8px 12px",
        boxShadow: "0 4px 16px rgba(15,23,42,0.12)",
        fontSize: 13,
      }}
    >
      <div style={{ color: C.muted, marginBottom: 2 }}>{label ?? payload[0].name}</div>
      <div style={{ fontWeight: 700, color: C.ink }}>{payload[0].value}</div>
    </div>
  );
}

export function App() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [calls, setCalls] = useState<CallResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([fetchMetrics(), fetchCalls()])
      .then(([m, c]) => {
        setMetrics(m);
        setCalls(c);
        setError(null);
        setUpdatedAt(new Date());
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, [load]);

  const outcomeData = metrics
    ? Object.entries(metrics.outcomes)
        .filter(([, v]) => v > 0)
        .map(([k, v]) => ({ name: OUTCOME_META[k]?.label ?? k, value: v, color: OUTCOME_META[k]?.color }))
    : [];
  const sentimentData = metrics
    ? Object.entries(metrics.sentiments)
        .filter(([, v]) => v > 0)
        .map(([k, v]) => ({ name: SENTIMENT_META[k]?.label ?? k, value: v, color: SENTIMENT_META[k]?.color }))
    : [];

  const fmt = (n: number | null | undefined, prefix = "") =>
    n != null ? `${prefix}${n.toLocaleString()}` : "—";

  return (
    <div style={{ minHeight: "100vh", background: "var(--canvas)" }}>
      {/* Branded header */}
      <header
        style={{
          background: "linear-gradient(120deg, #0b1120 0%, #1e1b4b 100%)",
          color: "#fff",
          padding: "20px 32px",
        }}
      >
        <div
          style={{
            maxWidth: 1180,
            margin: "0 auto",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            flexWrap: "wrap",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div
              style={{
                width: 42,
                height: 42,
                borderRadius: 12,
                background: "linear-gradient(135deg, #6366f1, #4f46e5)",
                display: "grid",
                placeItems: "center",
                fontSize: 22,
                boxShadow: "0 4px 14px rgba(79,70,229,0.5)",
              }}
            >
              🚛
            </div>
            <div>
              <div style={{ fontSize: 19, fontWeight: 800, letterSpacing: -0.2 }}>
                Carrier Sales · Command Center
              </div>
              <div style={{ fontSize: 13, color: "#a5b4fc" }}>
                Inbound carrier call performance — powered by a HappyRobot voice agent
              </div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 13, color: "#cbd5e1" }}>
              <span className="live-dot" />
              {updatedAt ? `Updated ${updatedAt.toLocaleTimeString()}` : "Connecting…"}
            </div>
            <button className="btn" onClick={load}>
              {loading ? "Refreshing…" : "↻ Refresh"}
            </button>
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1180, margin: "0 auto", padding: "28px 32px 48px" }}>
        {error && (
          <div
            className="card"
            style={{ padding: 18, color: C.neg, background: "#fef2f2", borderColor: "#fecaca" }}
          >
            <strong>Couldn't reach the API.</strong> {error}
            <div style={{ fontSize: 13, color: "#7f1d1d", marginTop: 6 }}>
              Check VITE_API_BASE_URL / VITE_API_KEY and that this origin is allowed (CORS).
            </div>
          </div>
        )}

        {metrics && (
          <>
            {/* Primary KPIs */}
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              <Kpi label="Total Calls" value={metrics.total_calls} accent={C.brand} />
              <Kpi label="Booked" value={metrics.booked} accent={C.pos} />
              <Kpi
                label="Booking Rate"
                value={`${(metrics.booking_rate * 100).toFixed(0)}%`}
                accent={C.brand}
              />
              <Kpi label="Avg Rounds" value={metrics.avg_negotiation_rounds} accent={C.slate} />
              <Kpi
                label="Avg Final Rate"
                value={fmt(metrics.avg_final_rate, "$")}
                accent={C.warn}
              />
            </div>

            {/* Negotiation effectiveness + transfer */}
            <div style={{ marginTop: 22 }}>
              <SectionTitle>Negotiation effectiveness</SectionTitle>
              <div style={{ fontSize: 13, color: C.muted, marginBottom: 12 }}>
                How good the booked deals were, measured against our posted rate and our hidden
                walk-away ceiling.
              </div>
              <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                <Kpi
                  label="Avg Markup vs Posted"
                  value={fmt(metrics.avg_markup_over_loadboard, "+$")}
                  accent={C.warn}
                  hint="paid above our posted rate"
                />
                <Kpi
                  label="Avg Saved vs Ceiling"
                  value={fmt(metrics.avg_savings_vs_ceiling, "$")}
                  accent={C.pos}
                  hint="kept under our walk-away max"
                />
                <Kpi
                  label="Gap Paid"
                  value={
                    metrics.avg_gap_captured_pct != null
                      ? `${(metrics.avg_gap_captured_pct * 100).toFixed(0)}%`
                      : "—"
                  }
                  accent={C.brand}
                  hint="of the negotiable margin"
                />
                <Kpi label="Transferred" value={metrics.transferred} accent={C.slate} hint="to a human rep" />
                <Kpi
                  label="Transfer Rate"
                  value={`${(metrics.transfer_rate * 100).toFixed(0)}%`}
                  accent={C.pos}
                  hint="of booked calls"
                />
              </div>
            </div>

            {/* Funnel */}
            <div className="card" style={{ padding: 22, marginTop: 22 }}>
              <SectionTitle>Conversion funnel</SectionTitle>
              <ResponsiveContainer width="100%" height={190}>
                <BarChart data={metrics.funnel} layout="vertical" margin={{ left: 16, right: 36 }}>
                  <XAxis type="number" allowDecimals={false} hide />
                  <YAxis
                    type="category"
                    dataKey="stage"
                    width={104}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 13, fill: C.ink }}
                  />
                  <Tooltip cursor={{ fill: "#f1f5f9" }} content={<ChartTooltip />} />
                  <Bar dataKey="count" radius={[0, 8, 8, 0]} barSize={26}>
                    {metrics.funnel.map((_, i) => (
                      <Cell key={i} fill={`rgba(79,70,229,${1 - i * 0.18})`} />
                    ))}
                    <LabelList dataKey="count" position="right" style={{ fill: C.ink, fontWeight: 700 }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Outcomes + sentiment */}
            <div style={{ display: "flex", gap: 16, marginTop: 22, flexWrap: "wrap" }}>
              <div className="card" style={{ flex: 2, minWidth: 320, padding: 22 }}>
                <SectionTitle>Call outcomes</SectionTitle>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={outcomeData} margin={{ top: 12 }}>
                    <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: C.muted }} />
                    <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: C.muted }} />
                    <Tooltip cursor={{ fill: "#f8fafc" }} content={<ChartTooltip />} />
                    <Bar dataKey="value" radius={[8, 8, 0, 0]} barSize={48}>
                      {outcomeData.map((d, i) => (
                        <Cell key={i} fill={d.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="card" style={{ flex: 1, minWidth: 260, padding: 22 }}>
                <SectionTitle>Sentiment</SectionTitle>
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie
                      data={sentimentData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={52}
                      outerRadius={90}
                      paddingAngle={2}
                    >
                      {sentimentData.map((d, i) => (
                        <Cell key={i} fill={d.color} />
                      ))}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ display: "flex", gap: 14, justifyContent: "center", flexWrap: "wrap" }}>
                  {sentimentData.map((d) => (
                    <span key={d.name} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: C.muted }}>
                      <span className="dot" style={{ background: d.color }} /> {d.name} · {d.value}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Recent calls */}
            <div className="card" style={{ padding: 22, marginTop: 22 }}>
              <SectionTitle>Recent calls</SectionTitle>
              {calls.length === 0 ? (
                <p style={{ color: C.muted, fontSize: 14 }}>
                  No calls logged yet. They appear here once the agent posts to{" "}
                  <code>/call_results</code>.
                </p>
              ) : (
                <div style={{ overflowX: "auto", marginTop: 8 }}>
                  <table className="calls">
                    <thead>
                      <tr>
                        <th>When</th>
                        <th>MC</th>
                        <th>Load</th>
                        <th>Outcome</th>
                        <th>Sentiment</th>
                        <th>Rounds</th>
                        <th>Final rate</th>
                        <th>Transfer</th>
                      </tr>
                    </thead>
                    <tbody>
                      {calls.map((c) => (
                        <tr key={c.id}>
                          <td style={{ color: C.muted, whiteSpace: "nowrap" }}>
                            {new Date(c.created_at).toLocaleString([], {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </td>
                          <td style={{ fontVariantNumeric: "tabular-nums" }}>{c.mc_number ?? "—"}</td>
                          <td style={{ fontWeight: 600 }}>{c.load_id ?? "—"}</td>
                          <td>
                            <Badge
                              color={OUTCOME_META[c.outcome]?.color ?? C.slate}
                              label={OUTCOME_META[c.outcome]?.label ?? c.outcome}
                            />
                          </td>
                          <td>
                            <Badge
                              color={SENTIMENT_META[c.sentiment]?.color ?? C.slate}
                              label={SENTIMENT_META[c.sentiment]?.label ?? c.sentiment}
                            />
                          </td>
                          <td style={{ fontVariantNumeric: "tabular-nums" }}>{c.negotiation_rounds}</td>
                          <td style={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>
                            {c.final_rate != null ? `$${c.final_rate.toLocaleString()}` : "—"}
                          </td>
                          <td>{c.transferred ? "✓" : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div style={{ textAlign: "center", color: C.muted, fontSize: 12, marginTop: 28 }}>
              Auto-refreshes every 15s · FastAPI on Fly.io · React on Vercel
            </div>
          </>
        )}
      </main>
    </div>
  );
}
