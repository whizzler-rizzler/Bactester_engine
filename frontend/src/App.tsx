import { useEffect, useMemo, useState } from "react";
import { getDatasets, getStrategies, runBacktest } from "./api";
import type { BacktestResponse, DatasetInfo, StrategyDescriptor } from "./types";
import { StrategyForm } from "./components/StrategyForm";
import { MetricsView } from "./components/MetricsView";
import { EquityChart } from "./components/EquityChart";
import { FillsTable } from "./components/FillsTable";

export function App() {
  const [strategies, setStrategies] = useState<StrategyDescriptor[]>([]);
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<string>("");
  const [selectedDataset, setSelectedDataset] = useState<string>("");
  const [params, setParams] = useState<Record<string, unknown>>({});
  const [execCfg, setExecCfg] = useState({
    starting_cash: 10000,
    fee_rate: 0.001,
    slippage_rate: 0.0002,
    limit_bars: 10000,
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getStrategies()
      .then((s) => {
        setStrategies(s);
        if (s.length && !selectedStrategy) {
          setSelectedStrategy(s[0].name);
          setParams({ ...s[0].defaults });
        }
      })
      .catch((e) => setError(String(e)));
    getDatasets()
      .then((d) => {
        setDatasets(d);
        if (d.length && !selectedDataset) setSelectedDataset(d[0].name);
      })
      .catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const currentStrategy = useMemo(
    () => strategies.find((s) => s.name === selectedStrategy),
    [strategies, selectedStrategy],
  );

  const onStrategyChange = (name: string) => {
    setSelectedStrategy(name);
    const s = strategies.find((x) => x.name === name);
    if (s) setParams({ ...s.defaults });
  };

  const resetToDefaults = () => {
    if (currentStrategy) setParams({ ...currentStrategy.defaults });
  };

  const submit = async () => {
    if (!selectedStrategy || !selectedDataset) return;
    setLoading(true);
    setError(null);
    try {
      const res = await runBacktest({
        strategy: selectedStrategy,
        params,
        dataset: selectedDataset,
        starting_cash: execCfg.starting_cash,
        fee_rate: execCfg.fee_rate,
        slippage_rate: execCfg.slippage_rate,
        limit_bars: execCfg.limit_bars || null,
      });
      setResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>Bactester Engine</h1>
          <div className="brand-tag">Binance 1m candle backtester · strategy panel</div>
        </div>
        <div className="brand-tag">
          {datasets.length} dataset{datasets.length === 1 ? "" : "s"} ·{" "}
          {strategies.length} strateg{strategies.length === 1 ? "y" : "ies"}
        </div>
      </header>

      <main className="layout">
        <section className="panel">
          <h2>Setup</h2>
          <div className="field">
            <label>
              Strategy
              <span className="hint">
                {currentStrategy?.description ?? ""}
              </span>
            </label>
            <select
              value={selectedStrategy}
              onChange={(e) => onStrategyChange(e.target.value)}
            >
              {strategies.map((s) => (
                <option key={s.name} value={s.name}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>
              Dataset
              <span className="hint">Select candle history</span>
            </label>
            <select
              value={selectedDataset}
              onChange={(e) => setSelectedDataset(e.target.value)}
            >
              {datasets.map((d) => (
                <option key={d.name} value={d.name}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <div className="section-divider" />
          <h2>Execution</h2>
          <div className="field">
            <label>Starting cash<span className="hint">Quote currency</span></label>
            <input
              type="number"
              value={execCfg.starting_cash}
              onChange={(e) => setExecCfg({ ...execCfg, starting_cash: Number(e.target.value) })}
            />
          </div>
          <div className="field">
            <label>Fee rate<span className="hint">Per fill, e.g. 0.001 = 10 bps</span></label>
            <input
              type="number"
              step="0.0001"
              value={execCfg.fee_rate}
              onChange={(e) => setExecCfg({ ...execCfg, fee_rate: Number(e.target.value) })}
            />
          </div>
          <div className="field">
            <label>Slippage rate<span className="hint">Market-order slippage</span></label>
            <input
              type="number"
              step="0.0001"
              value={execCfg.slippage_rate}
              onChange={(e) => setExecCfg({ ...execCfg, slippage_rate: Number(e.target.value) })}
            />
          </div>
          <div className="field">
            <label>Bar cap<span className="hint">0 = no cap</span></label>
            <input
              type="number"
              value={execCfg.limit_bars}
              onChange={(e) => setExecCfg({ ...execCfg, limit_bars: Number(e.target.value) })}
            />
          </div>

          {currentStrategy && (
            <>
              <div className="section-divider" />
              <h2>{currentStrategy.name} params</h2>
              <StrategyForm
                strategy={currentStrategy}
                values={params}
                onChange={setParams}
              />
              <button className="primary" onClick={resetToDefaults} style={{ background: "#2a3142" }}>
                Reset defaults
              </button>
            </>
          )}

          <button className="primary" onClick={submit} disabled={loading || !selectedDataset}>
            {loading ? "Running…" : "Run backtest"}
          </button>
          {error && <div className="error">{error}</div>}
        </section>

        <section className="results-panel">
          {!result ? (
            <div className="panel">
              <div className="placeholder">
                Configure a strategy and hit <b>Run backtest</b> to see results here.
              </div>
            </div>
          ) : (
            <>
              <div className="panel">
                <h2>Metrics</h2>
                <MetricsView metrics={result.metrics} bars={result.bars} />
              </div>
              <div className="panel">
                <h2>Equity vs price</h2>
                <EquityChart data={result.equity_curve} />
              </div>
              <div className="panel">
                <h2>Fills (first 40 of {result.fills.length})</h2>
                <FillsTable fills={result.fills} />
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
