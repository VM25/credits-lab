import type { ReactNode } from "react";
import * as RTabs from "@radix-ui/react-tabs";
import { stateColor } from "../lib/format";

// Flat, sharp, radius-0 primitives (doc 10).
// Hierarchy is carried by surface tone, scale and spacing - borders are reserved
// for tables, state and interaction, not for wrapping every element.

/* ---------------------------------------------------------------- sections */

export function Section({ id, title, lede, children, tone = "bg" }: {
  id: string; title: string; lede?: ReactNode; children: ReactNode;
  tone?: "bg" | "panel";
}) {
  return (
    <section id={id} className={`scroll-mt-14 ${tone === "panel" ? "bg-panel" : ""}`}>
      <div className={`mx-auto max-w-[1480px] px-5 ${tone === "panel" ? "py-14" : "py-14"}`}>
        <h2 className="max-w-[26ch] text-[30px] font-semibold leading-[1.12] tracking-tight text-ink">
          {title}
        </h2>
        {lede && <p className="mt-3 max-w-[78ch] text-[14.5px] leading-relaxed text-ink-soft">{lede}</p>}
        <div className="mt-8">{children}</div>
      </div>
    </section>
  );
}

// Surface container. Borderless by default; tone sets its depth.
export function Block({ children, className = "", tone = "panel" }: {
  children: ReactNode; className?: string; tone?: "panel" | "deep" | "flat" | "outline";
}) {
  const t =
    tone === "deep" ? "bg-panel-3"
    : tone === "flat" ? "bg-panel-2"
    : tone === "outline" ? "border border-line"
    : "bg-panel";
  return <div className={`${t} ${className}`}>{children}</div>;
}

// Small label above a block of content. No box, no border.
export function Label({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-2 flex items-baseline justify-between gap-4">
      <span className="text-[12px] font-medium tracking-wide text-ink-soft">{children}</span>
      {right && <span className="text-[11.5px] text-ink-faint">{right}</span>}
    </div>
  );
}

/* ------------------------------------------------------------------- stats */

// Typographic stat. Hierarchy from scale, not from a bordered tile.
export function Stat({ label, value, sub, size = "md", color }: {
  label: string; value: ReactNode; sub?: ReactNode;
  size?: "sm" | "md" | "lg" | "xl"; color?: string;
}) {
  const s = { sm: "text-[17px]", md: "text-[23px]", lg: "text-[32px]", xl: "text-[44px]" }[size];
  return (
    <div>
      <div className="text-[11.5px] leading-tight text-ink-soft">{label}</div>
      <div className={`num mt-1 ${s} font-medium leading-none text-ink`} style={color ? { color } : undefined}>
        {value}
      </div>
      {sub && <div className="mt-1.5 text-[11px] leading-snug text-ink-faint">{sub}</div>}
    </div>
  );
}

// A scope caption. Used wherever two similar metrics differ by what they cover.
export function Scope({ children }: { children: ReactNode }) {
  return <span className="text-[11px] italic leading-snug text-ink-faint">{children}</span>;
}

/* ------------------------------------------------------------------- state */

export function Chip({ label, size = "md" }: { label: string; size?: "sm" | "md" }) {
  return (
    <span
      className={`num inline-flex items-center font-medium ${size === "sm" ? "px-1.5 py-0.5 text-[10.5px]" : "px-2.5 py-1 text-[12px]"}`}
      style={{ background: stateColor(label), color: "#EAF0EA" }}
    >
      {(label || "").replace(/_/g, " ")}
    </span>
  );
}

// Verdict / status word rendered in its semantic colour, no chip.
export function StateWord({ label, size = "md" }: { label: string; size?: "sm" | "md" | "lg" }) {
  const s = { sm: "text-[12px]", md: "text-[15px]", lg: "text-[21px]" }[size];
  return (
    <span className={`${s} font-semibold tracking-tight`} style={{ color: stateColor(label) }}>
      {(label || "").replace(/_/g, " ")}
    </span>
  );
}

/* -------------------------------------------------------------------- tabs */

export function Tabs({ tabs, defaultValue, children }: {
  tabs: { value: string; label: string }[]; defaultValue?: string; children: ReactNode;
}) {
  return (
    <RTabs.Root defaultValue={defaultValue ?? tabs[0].value}>
      <RTabs.List className="mb-6 flex flex-wrap gap-x-7 gap-y-1 border-b border-line">
        {tabs.map((t) => (
          <RTabs.Trigger
            key={t.value}
            value={t.value}
            className="-mb-px border-b-2 border-transparent pb-2 text-[13.5px] text-ink-soft transition-colors hover:text-ink data-[state=active]:border-accent data-[state=active]:font-medium data-[state=active]:text-ink"
          >
            {t.label}
          </RTabs.Trigger>
        ))}
      </RTabs.List>
      {children}
    </RTabs.Root>
  );
}

export const TabPanel = RTabs.Content;

/* ------------------------------------------------------------------ tables */

// Selectable row list: borders here are structural, so they stay.
export function RowButton({ selected, onClick, cols, children }: {
  selected: boolean; onClick: () => void; cols: string; children: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`grid w-full items-center border-b border-line/60 text-left transition-colors ${
        selected ? "bg-panel-4" : "hover:bg-panel-2"
      }`}
      style={{ gridTemplateColumns: cols }}
      aria-pressed={selected}
    >
      {children}
    </button>
  );
}

export function TableHead({ cols, headers }: { cols: string; headers: string[] }) {
  return (
    <div
      className="grid border-b border-line text-[11px] text-ink-soft"
      style={{ gridTemplateColumns: cols }}
    >
      {headers.map((h) => <div key={h} className="px-3 py-2">{h}</div>)}
    </div>
  );
}

/* ------------------------------------------------------------------ detail */

// Key/value line used inside detail panels.
export function KV({ k, v, mono = true }: { k: string; v: ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5">
      <span className="text-[12px] text-ink-soft">{k}</span>
      <span className={`${mono ? "num" : ""} text-[13px] text-ink`}>{v}</span>
    </div>
  );
}

export function Note({ children, tone = "plain" }: { children: ReactNode; tone?: "plain" | "caveat" }) {
  return (
    <p
      className={`max-w-[86ch] text-[12px] leading-relaxed text-ink-soft ${tone === "caveat" ? "pl-3" : ""}`}
      style={tone === "caveat" ? { borderLeft: "2px solid #6C6440" } : undefined}
    >
      {children}
    </p>
  );
}
