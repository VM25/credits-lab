import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Cell, ReferenceLine,
} from "recharts";
import { TOK } from "../lib/format";

// Flat, restrained chart wrappers. Thin strokes, low-contrast gridlines,
// no gradients, no entrance animation (functional only).

const axis = { stroke: TOK.line, tick: { fill: TOK.inkSoft, fontSize: 11, fontFamily: "Fira Code" } };
const tip = {
  contentStyle: {
    background: TOK.bg, border: `1px solid ${TOK.line}`, borderRadius: 0,
    fontFamily: "Fira Code", fontSize: 12, color: TOK.ink,
  },
  cursor: { fill: "rgba(24,36,30,0.06)" },
};

export function BarFlat({ data, x, y, height = 220, colorFor, money }: {
  data: any[]; x: string; y: string; height?: number;
  colorFor?: (row: any) => string; money?: boolean;
}) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid stroke={TOK.line} strokeOpacity={0.4} vertical={false} />
          <XAxis dataKey={x} {...axis} tickLine={false} />
          <YAxis {...axis} tickLine={false} width={money ? 52 : 40}
            tickFormatter={(v) => (money ? `${(v / 1e6).toFixed(0)}M` : String(v))} />
          <Tooltip {...tip} />
          <Bar dataKey={y} isAnimationActive={false}>
            {data.map((row, i) => (
              <Cell key={i} fill={colorFor ? colorFor(row) : TOK.accent} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LineFlat({ data, x, lines, height = 220, refLine }: {
  data: any[]; x: string; lines: { key: string; color: string }[]; height?: number;
  refLine?: { y: number; label: string };
}) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid stroke={TOK.line} strokeOpacity={0.4} vertical={false} />
          <XAxis dataKey={x} {...axis} tickLine={false} />
          <YAxis {...axis} tickLine={false} width={44} />
          <Tooltip {...tip} />
          {refLine && <ReferenceLine y={refLine.y} stroke={TOK.inkSoft} strokeDasharray="3 3" />}
          {lines.map((l) => (
            <Line key={l.key} type="monotone" dataKey={l.key} stroke={l.color}
              strokeWidth={1.6} dot={false} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
