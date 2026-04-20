import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { EquityPoint } from "../types";

interface Props {
  data: EquityPoint[];
}

export function EquityChart({ data }: Props) {
  const plot = data.map((d) => ({
    ts: d.ts.slice(5, 16).replace("T", " "),
    equity: d.equity,
    price: d.price,
  }));
  return (
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={plot} margin={{ top: 8, right: 20, bottom: 8, left: 0 }}>
          <CartesianGrid stroke="#2a3142" strokeDasharray="3 3" />
          <XAxis dataKey="ts" stroke="#8b93a7" fontSize={11} minTickGap={60} />
          <YAxis
            yAxisId="eq"
            stroke="#5b8cff"
            fontSize={11}
            tickFormatter={(v: number) => v.toFixed(0)}
          />
          <YAxis
            yAxisId="px"
            orientation="right"
            stroke="#2dd4bf"
            fontSize={11}
            tickFormatter={(v: number) => v.toFixed(0)}
          />
          <Tooltip
            contentStyle={{ background: "#1d2330", border: "1px solid #2a3142" }}
            labelStyle={{ color: "#e7ecf3" }}
            formatter={(v: number) => v.toFixed(2)}
          />
          <Legend />
          <Line
            yAxisId="eq"
            type="monotone"
            dataKey="equity"
            name="Equity"
            stroke="#5b8cff"
            dot={false}
            strokeWidth={1.5}
          />
          <Line
            yAxisId="px"
            type="monotone"
            dataKey="price"
            name="Price"
            stroke="#2dd4bf"
            dot={false}
            strokeWidth={1.2}
            opacity={0.7}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
