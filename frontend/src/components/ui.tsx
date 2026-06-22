import type { ReactNode } from "react";
import { stateColor } from "../lib/format";

// Flat, sharp, hairline primitives. No rounded cards, no shadows (doc 10).

export function Section({ id, label, title, children, note }: {
  id: string; label: string; title: string; children: ReactNode; note?: string;
}) {
  return (
    <section id={id} className="scroll-mt-16 border-t border-line py-10">
      <div className="reg text-[11px] text-accent">{label}</div>
      <h2 className="mt-1 text-[20px] font-semibold tracking-tight text-ink">{title}</h2>
      {note && <p className="mt-1 max-w-[80ch] text-[13px] text-ink-soft">{note}</p>}
      <div className="mt-5">{children}</div>
    </section>
  );
}

export function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`border border-line bg-panel ${className}`}>{children}</div>;
}

export function PanelHead({ left, right }: { left: string; right?: string }) {
  return (
    <div className="flex items-baseline justify-between border-b border-line px-4 py-2.5">
      <span className="reg text-[11px] text-accent">{left}</span>
      {right && <span className="reg text-[10.5px] text-ink-soft">{right}</span>}
    </div>
  );
}

// Metric readouts share a panel and are separated by hairlines, not individual cards.
export function MetricRow({ items }: { items: { label: string; value: string; sub?: string }[] }) {
  return (
    <Panel>
      <div className="grid" style={{ gridTemplateColumns: `repeat(${Math.min(items.length, 4)}, minmax(0,1fr))` }}>
        {items.map((m, i) => (
          <div key={m.label} className={`px-4 py-3 ${i % Math.min(items.length, 4) !== 0 ? "border-l border-line" : ""} ${i >= Math.min(items.length, 4) ? "border-t border-line" : ""}`}>
            <div className="reg text-[10px] text-ink-soft">{m.label}</div>
            <div className="num mt-1 text-[22px] font-medium text-ink">{m.value}</div>
            {m.sub && <div className="mt-0.5 text-[11px] text-ink-soft">{m.sub}</div>}
          </div>
        ))}
      </div>
    </Panel>
  );
}

export function Chip({ label }: { label: string }) {
  return (
    <span
      className="num inline-flex items-center px-2 py-0.5 text-[11px] font-medium"
      style={{ background: stateColor(label), color: "#eaf0ea" }}
    >
      {(label || "").replace(/_/g, " ")}
    </span>
  );
}

export function Bare({ children }: { children: ReactNode }) {
  return <div className="border border-line bg-panel-2 px-4 py-3">{children}</div>;
}
