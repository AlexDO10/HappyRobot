export interface FunnelStage {
  stage: string;
  count: number;
}

export interface Metrics {
  total_calls: number;
  booked: number;
  booking_rate: number;
  avg_negotiation_rounds: number;
  avg_final_rate: number | null;
  outcomes: Record<string, number>;
  sentiments: Record<string, number>;
  funnel: FunnelStage[];
  avg_markup_over_loadboard: number | null;
  avg_savings_vs_ceiling: number | null;
  avg_gap_captured_pct: number | null;
  transferred: number;
  transfer_rate: number;
}

export interface CallResult {
  id: number;
  mc_number: string | null;
  load_id: string | null;
  outcome: string;
  sentiment: string;
  final_rate: number | null;
  negotiation_rounds: number;
  transcript_summary: string | null;
  created_at: string;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "x-api-key": API_KEY },
  });
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export const fetchMetrics = () => get<Metrics>("/metrics");
export const fetchCalls = () => get<CallResult[]>("/call_results?limit=50");
