export interface Metrics {
  total_calls: number;
  booked: number;
  booking_rate: number;
  avg_negotiation_rounds: number;
  avg_final_rate: number | null;
  outcomes: Record<string, number>;
  sentiments: Record<string, number>;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

export async function fetchMetrics(): Promise<Metrics> {
  const res = await fetch(`${API_BASE}/metrics`, {
    headers: { "x-api-key": API_KEY },
  });
  if (!res.ok) {
    throw new Error(`Metrics request failed: ${res.status}`);
  }
  return res.json();
}
