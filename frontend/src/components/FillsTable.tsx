import type { FillRow } from "../types";

interface Props {
  fills: FillRow[];
  max?: number;
}

export function FillsTable({ fills, max = 40 }: Props) {
  const head = fills.slice(0, max);
  if (!head.length) return null;
  return (
    <table className="fills-table">
      <thead>
        <tr>
          <th>Time</th>
          <th>Side</th>
          <th>Qty</th>
          <th>Price</th>
          <th>Tag</th>
        </tr>
      </thead>
      <tbody>
        {head.map((f, i) => (
          <tr key={i}>
            <td>{f.ts.slice(5, 16).replace("T", " ")}</td>
            <td className={f.side === "buy" ? "tag-buy" : "tag-sell"}>{f.side}</td>
            <td>{f.qty.toFixed(6)}</td>
            <td>{f.price.toFixed(2)}</td>
            <td>{f.tag}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
