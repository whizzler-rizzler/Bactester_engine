export interface SchemaProperty {
  type?: string | string[];
  anyOf?: { type?: string }[];
  description?: string;
  default?: unknown;
  minimum?: number;
  maximum?: number;
  enum?: string[];
  title?: string;
}

export interface StrategyDescriptor {
  name: string;
  description: string;
  defaults: Record<string, unknown>;
  schema: {
    type: string;
    properties: Record<string, SchemaProperty>;
    required?: string[];
    $defs?: Record<string, { enum?: string[]; title?: string }>;
  };
}

export interface DatasetInfo {
  name: string;
  path: string;
  symbol: string;
  interval: string;
  size_bytes: number;
}

export interface Metrics {
  total_return_pct: number;
  pnl: number;
  max_drawdown_pct: number;
  sharpe: number;
  num_trades: number;
  win_rate_pct: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number | null;
  exposure_pct: number;
}

export interface EquityPoint {
  ts: string;
  equity: number;
  price: number;
  position_qty: number;
}

export interface FillRow {
  ts: string;
  side: "buy" | "sell";
  qty: number;
  price: number;
  fee: number;
  tag: string;
}

export interface BacktestResponse {
  strategy: string;
  dataset: string;
  bars: number;
  metrics: Metrics;
  equity_curve: EquityPoint[];
  fills: FillRow[];
  closed_trades: number[];
  params: Record<string, unknown>;
}
