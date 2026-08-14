import type { ReactNode } from "react";
import * as Tooltip from "@radix-ui/react-tooltip";
import { GLOSSARY, GITHUB_URL } from "../lib/site";

// Hover glossary term. Wrap any jargon: <Term k="PD">PD</Term>.
export function Term({ k, children }: { k: string; children?: ReactNode }) {
  const def = GLOSSARY[k];
  const label = children ?? k;
  if (!def) return <>{label}</>;
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>
        <span
          tabIndex={0}
          className="cursor-help underline decoration-dotted decoration-accent underline-offset-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          {label}
        </span>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          side="top"
          sideOffset={6}
          className="z-50 max-w-[320px] border border-line bg-bg px-3 py-2 text-[12px] leading-snug text-ink"
        >
          <span className="reg text-[10px] text-accent">{k}</span>
          <div className="mt-1">{def}</div>
          <Tooltip.Arrow style={{ fill: "#9caf9d" }} />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

// Guided intro shown under a section title: what it does / why / what to look at.
export function IntroBlock({ what, why, look }: { what: string; why: string; look: string }) {
  const rows: [string, string][] = [["what", what], ["why it matters", why], ["what to look at", look]];
  return (
    <div className="mb-4 border-l-2 border-accent bg-panel-2 px-4 py-3">
      <dl className="grid gap-1.5">
        {rows.map(([k, v]) => (
          <div key={k} className="grid grid-cols-[110px_1fr] gap-3">
            <dt className="reg text-[10px] text-ink-soft">{k}</dt>
            <dd className="text-[12.5px] leading-snug text-ink">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

// Caveat / disclosure callout (uses the muted "review" tone, never alarming red).
export function Callout({ label = "note", children }: { label?: string; children: ReactNode }) {
  return (
    <div className="border border-line bg-panel px-4 py-2.5" style={{ borderLeft: "3px solid #6c6440" }}>
      <span className="reg mr-2 text-[10px]" style={{ color: "#6c6440" }}>{label}</span>
      <span className="text-[12px] leading-snug text-ink">{children}</span>
    </div>
  );
}

export function GithubLink({ compact = false }: { compact?: boolean }) {
  return (
    <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer"
      className="reg inline-flex items-center gap-1.5 border border-line px-2.5 py-1 text-[10.5px] text-ink hover:border-accent hover:text-accent">
      <svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
        <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38v-1.32c-2.23.49-2.7-1.07-2.7-1.07-.36-.93-.89-1.18-.89-1.18-.73-.5.05-.49.05-.49.81.06 1.23.83 1.23.83.72 1.23 1.89.87 2.35.67.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.6 7.6 0 014 0c1.53-1.03 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48v2.2c0 .21.15.46.55.38A8 8 0 0016 8c0-4.42-3.58-8-8-8z"/>
      </svg>
      {compact ? "GitHub" : "View GitHub Repository"}
    </a>
  );
}
