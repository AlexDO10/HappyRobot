import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchCalls, fetchMetrics, type CallResult, type Metrics } from "./api";

const SENTIMENT_COLORS: Record<string, string> = {
  positive: "#16a34a",
  neutral: "#94a3b8",
  negative: "#dc2626",
};

const OUTCOME_LABELS: Record<string, string> = {
  booked: "Booked",
  no_agreement: "No agreement",
  not_eligible: "Not eligible",
  no_load_match: "No load match",
  abandoned: "Abandoned",
};

const card: React.CSSProperties = {
  background: "#fff",
  borderRadius: 14,
  padding: 24,
  boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
};

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{ ...card, flex: 1, minWidth: 150 }}>
      <div style={{ fontSize: 12, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.6 }}>
        {label}
      </div>
      <div style={{ fontSize: 30, fontWeight: 700, color: "#0f172a", marginTop: 6 }}>{value}</div>
    </div>
  );
}

export function App() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [calls, setCalls] = useState<CallResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([fetchMetrics(), fetchCalls()])
      .then(([m, c]) => {
        setMetrics(m);
        setCalls(c);
        setError(null);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 15000); // auto-refresh every 15s
    return () => clearInterval(id);
  }, [load]);

  const outcomeData = metrics
    ? Object.entries(metrics.outcomes).map(([k, v]) => ({ name: OUTCOME_LABELS[k] ?? k, value: v }))
    : [];
  const sentimentData = metrics
    ? Object.entries(metrics.sentiments)
        .filter(([, v]) => v > 0)
        .map(([k, v]) => ({ name: k, value: v }))
    : [];

  return (
    <div
      style={{
        fontFamily: "system-ui, -apple-system, sans-serif",
        background: "#f1f5f9",
        minHeight: "100vh",
        padding: 32,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ margin: 0, color: "#0f172a" }}>Inbound Carrier Sales</h1>
          <p style={{ color: "#64748b", marginTop: 4 }}>Live call performance · auto-refreshes every 15s</p>
        </div>
        <button
          onClick={load}
          style={{
            background: "#2563eb",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "10px 18px",
            fontSize: 14,
            cursor: "pointer",
          }}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && (
        <div style={{ ...card, marginTop: 16, color: "#b91c1c", background: "#fef2f2" }}>
          Error: {error}
          <div style={{ fontSize: 13, color: "#7f1d1d", marginTop: 6 }}>
            Check VITE_API_BASE_URL and VITE_API_KEY, and that the API allows this origin (CORS).
          </div>
        </div>
      )}

      {metrics && (
        <>
          <div style={{ display: "flex", gap: 16, marginTop: 24, flexWrap: "wrap" }}>
            <StatCard label="Total Calls" value={metrics.total_calls} />
            <StatCard label="Booked" value={metrics.booked} />
            <StatCard label="Booking Rate" value={`${(metrics.booking_rate * 100).toFixed(0)}%`} />
            <StatCard label="Avg Rounds" value={metrics.avg_negotiation_rounds} />
            <StatCard
              label="Avg Final Rate"
              value={metrics.avg_final_rate != null ? `$${metrics.avg_final_rate.toLocaleString()}` : "—"}
            />
          </div>

          <div style={{ display: "flex", gap: 16, marginTop: 24, flexWrap: "wrap" }}>
            <div style={{ ...card, flex: 2, minWidth: 320 }}>
              <h3 style={{ marginTop: 0, color: "#0f172a" }}>Call outcomes</h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={outcomeData}>
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#2563eb" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div style={{ ...card, flex: 1, minWidth: 260 }}>
              <h3 style={{ marginTop: 0, color: "#0f172a" }}>Sentiment</h3>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={sentimentData} dataKey="value" nameKey="name" outerRadius={90} label>
                    {sentimentData.map((d) => (
                      <Cell key={d.name} fill={SENTIMENT_COLORS[d.name] ?? "#94a3b8"} />
                    ))}
                  </Pie>
                  <Legend />
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div style={{ ...card, marginTop: 24 }}>
            <h3 style={{ marginTop: 0, color: "#0f172a" }}>Recent calls</h3>
            {calls.length === 0 ? (
              <p style={{ color: "#64748b" }}>
                No calls logged yet. They appear here once the agent POSTs to <code>/call_results</code>.
              </p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                  <thead>
                    <tr style={{ textAlign: "left", color: "#64748b", borderBottom: "1px solid #e2e8f0" }}>
                      <th style={{ padding: 8 }}>When</th>
                      <th style={{ padding: 8 }}>MC</th>
                      <th style={{ padding: 8 }}>Load</th>
                      <th style={{ padding: 8 }}>Outcome</th>
                      <th style={{ padding: 8 }}>Sentiment</th>
                      <th style={{ padding: 8 }}>Rounds</th>
                      <th style={{ padding: 8 }}>Final rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {calls.map((c) => (
                      <tr key={c.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                        <td style={{ padding: 8, color: "#64748b" }}>
                          {new Date(c.created_at).toLocaleString()}
                        </td>
                        <td style={{ padding: 8 }}>{c.mc_number ?? "—"}</td>
                        <td style={{ padding: 8 }}>{c.load_id ?? "—"}</td>
                        <td style={{ padding: 8 }}>{OUTCOME_LABELS[c.outcome] ?? c.outcome}</td>
                        <td style={{ padding: 8, color: SENTIMENT_COLORS[c.sentiment] }}>{c.sentiment}</td>
                        <td style={{ padding: 8 }}>{c.negotiation_rounds}</td>
                        <td style={{ padding: 8 }}>
                          {c.final_rate != null ? `$${c.final_rate.toLocaleString()}` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
