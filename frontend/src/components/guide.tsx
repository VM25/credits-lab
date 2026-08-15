import { useState, type ReactNode } from "react";
import * as Tooltip from "@radix-ui/react-tooltip";
import { GLOSSARY, GITHUB_URL } from "../lib/site";

// Hover reference for a risk term. Wrap any jargon: <Term k="PD">PD</Term>.
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
          className="z-50 max-w-[340px] bg-ink px-3 py-2 text-[12px] leading-snug text-bg"
        >
          <span className="num text-[11px] opacity-70">{k}</span>
          <div className="mt-1">{def}</div>
          <Tooltip.Arrow style={{ fill: "#18241E" }} />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

// Collapsed by default: supporting reference, not a chapter of the page.
export function ReferenceDrawer() {
  const [open, setOpen] = useState(false);
  return (
    <div className="mx-auto max-w-[1480px] px-5">
      <div className="border-t border-line py-4">
        <button
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="flex items-center gap-2 text-[12.5px] text-ink-soft transition-colors hover:text-ink"
        >
          <span className="text-accent" aria-hidden="true">{open ? "−" : "+"}</span>
          Key risk terms
        </button>
        {open && (
          <dl className="mt-5 grid gap-x-12 gap-y-4 pb-3 md:grid-cols-2 xl:grid-cols-3">
            {Object.entries(GLOSSARY).map(([k, v]) => (
              <div key={k}>
                <dt className="num text-[12px] text-ink">{k}</dt>
                <dd className="mt-0.5 max-w-[46ch] text-[12px] leading-relaxed text-ink-soft">{v}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </div>
  );
}

export function GithubLink() {
  return (
    <a
      href={GITHUB_URL}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 text-[12.5px] text-ink-soft transition-colors hover:text-accent"
    >
      <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
        <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38v-1.32c-2.23.49-2.7-1.07-2.7-1.07-.36-.93-.89-1.18-.89-1.18-.73-.5.05-.49.05-.49.81.06 1.23.83 1.23.83.72 1.23 1.89.87 2.35.67.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.6 7.6 0 014 0c1.53-1.03 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48v2.2c0 .21.15.46.55.38A8 8 0 0016 8c0-4.42-3.58-8-8-8z" />
      </svg>
      GitHub
    </a>
  );
}
