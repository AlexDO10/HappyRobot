import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { fetchMetrics, type Metrics } from "./api";

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div
      style={{
        background: "#fff",
        borderRadius: 12,
        padding: "20px 24px",
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
        flex: 1,
        minWidth: 160,
      }}
    >
      <div style={{ fontSize: 13, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5 }}>
        {label}
      </div>
      <div style={{ fontSize: 32, fontWeight: 700, color: "#0f172a", marginTop: 6 }}>{value}</div>
    </div>
  );
}

export function App() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMetrics().then(setMetrics).catch((e) => setError(String(e)));
  }, []);

  const outcomeData = metrics
    ? Object.entries(metrics.outcomes).map(([name, value]) => ({ name, value }))
    : [];

  return (
    <div
      style={{
        fontFamily: "system-ui, sans-serif",
        background: "#f1f5f9",
        minHeight: "100vh",
        padding: 32,
      }}
    >
      <h1 style={{ margin: 0, color: "#0f172a" }}>Inbound Carrier Sales</h1>
      <p style={{ color: "#64748b", marginTop: 4 }}>Live call performance metrics</p>

      {error && <div style={{ color: "#b91c1c", marginTop: 16 }}>Error: {error}</div>}

      {metrics && (
        <>
          <div style={{ display: "flex", gap: 16, marginTop: 24, flexWrap: "wrap" }}>
            <StatCard label="Total Calls" value={metrics.total_calls} />
            <StatCard label="Booked" value={metrics.booked} />
            <StatCard label="Booking Rate" value={`${(metrics.booking_rate * 100).toFixed(0)}%`} />
            <StatCard label="Avg Rounds" value={metrics.avg_negotiation_rounds} />
            <StatCard
              label="Avg Final Rate"
              value={metrics.avg_final_rate ? `$${metrics.avg_final_rate}` : "—"}
            />
          </div>

          <div
            style={{
              background: "#fff",
              borderRadius: 12,
              padding: 24,
              marginTop: 24,
              boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
            }}
          >
            <h3 style={{ marginTop: 0, color: "#0f172a" }}>Outcomes</h3>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={outcomeData}>
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="value" fill="#2563eb" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}
