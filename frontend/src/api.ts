import type { BacktestResponse, DatasetInfo, StrategyDescriptor } from "./types";

const BASE = "/api";

export async function getStrategies(): Promise<StrategyDescriptor[]> {
  const r = await fetch(`${BASE}/strategies`);
  if (!r.ok) throw new Error(`strategies ${r.status}`);
  return r.json();
}

export async function getDatasets(): Promise<DatasetInfo[]> {
  const r = await fetch(`${BASE}/datasets`);
  if (!r.ok) throw new Error(`datasets ${r.status}`);
  return r.json();
}

export interface RunBacktestReq {
  strategy: string;
  params: Record<string, unknown>;
  dataset: string;
  starting_cash: number;
  fee_rate: number;
  slippage_rate: number;
  limit_bars?: number | null;
}

export async function runBacktest(req: RunBacktestReq): Promise<BacktestResponse> {
  const r = await fetch(`${BASE}/backtest`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!r.ok) {
    const body = await r.text();
    throw new Error(`backtest ${r.status}: ${body}`);
  }
  return r.json();
}
