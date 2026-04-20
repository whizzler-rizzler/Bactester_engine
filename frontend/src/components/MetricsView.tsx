import type { Metrics } from "../types";

interface Props {
  metrics: Metrics;
  bars: number;
}

export function MetricsView({ metrics, bars }: Props) {
  const cells: { lbl: string; val: string; tone?: "pos" | "neg" }[] = [
    {
      lbl: "Total return",
      val: `${metrics.total_return_pct.toFixed(2)} %`,
      tone: metrics.total_return_pct >= 0 ? "pos" : "neg",
    },
    {
      lbl: "PnL",
      val: `${metrics.pnl.toFixed(2)}`,
      tone: metrics.pnl >= 0 ? "pos" : "neg",
    },
    {
      lbl: "Max drawdown",
      val: `${metrics.max_drawdown_pct.toFixed(2)} %`,
      tone: "neg",
    },
    { lbl: "Sharpe (ann.)", val: metrics.sharpe.toFixed(2) },
    { lbl: "Trades", val: String(metrics.num_trades) },
    {
      lbl: "Win rate",
      val: `${metrics.win_rate_pct.toFixed(1)} %`,
    },
    { lbl: "Avg win", val: metrics.avg_win.toFixed(2), tone: "pos" },
    { lbl: "Avg loss", val: metrics.avg_loss.toFixed(2), tone: "neg" },
    {
      lbl: "Profit factor",
      val:
        metrics.profit_factor === null || metrics.profit_factor === undefined
          ? "∞"
          : metrics.profit_factor.toFixed(2),
    },
    { lbl: "Exposure", val: `${metrics.exposure_pct.toFixed(1)} %` },
    { lbl: "Bars", val: String(bars) },
  ];
  return (
    <div className="metrics">
      {cells.map((c) => (
        <div className={`metric ${c.tone ?? ""}`} key={c.lbl}>
          <div className="lbl">{c.lbl}</div>
          <div className="val">{c.val}</div>
        </div>
      ))}
    </div>
  );
}
