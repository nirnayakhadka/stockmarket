import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import type { PricePoint } from "../types";

export default function PriceChart({ data }: { data: PricePoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a2f3a" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={20} />
        <YAxis yAxisId="price" tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
        <YAxis yAxisId="volume" orientation="right" tick={{ fontSize: 11 }} />
        <Tooltip
          contentStyle={{ background: "#1b1f27", border: "1px solid #333", fontSize: 12 }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar yAxisId="volume" dataKey="volume" fill="#3a4256" name="Volume" barSize={12} />
        <Line yAxisId="price" type="monotone" dataKey="close" stroke="#4fd1c5" strokeWidth={2} dot={false} name="Close" />
        <Line yAxisId="price" type="monotone" dataKey="vwap" stroke="#f6ad55" strokeWidth={1.5} strokeDasharray="4 3" dot={false} name="VWAP" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
