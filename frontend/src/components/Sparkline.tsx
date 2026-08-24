import { ResponsiveContainer, Line, LineChart, YAxis } from "recharts";

interface SparklineProps {
  /** Close prices ordered oldest → newest */
  values: number[];
  height?: number;
}

/** Tiny trend line for table rows / cards. Color follows direction. */
export default function Sparkline({ values, height = 36 }: SparklineProps) {
  if (values.length < 2) {
    return (
      <div style={{ height }} className="flex items-center text-xs text-muted">
        —
      </div>
    );
  }

  const data = values.map((v, i) => ({ i, v }));
  const positive = values[values.length - 1] >= values[0];
  const stroke = positive ? "#4ade80" : "#f87171";

  return (
    <div style={{ width: 110, height }} aria-hidden="true">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, right: 2, left: 2, bottom: 4 }}>
          <YAxis hide domain={["dataMin", "dataMax"]} />
          <Line
            type="monotone"
            dataKey="v"
            stroke={stroke}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
