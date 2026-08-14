import { Section, Panel, PanelHead } from "../components/ui";
import { ARCH, GITHUB_URL } from "../lib/site";

export function Architecture() {
  return (
    <Section id="architecture" label="Technical architecture" title="A Python risk engine behind the terminal"
      note="The interface is a thin layer over a reproducible backend. Every number on this site is produced by the pipeline, written to static JSON/CSV, and read by the frontend.">

      <Panel>
        <PanelHead left="Build pipeline" />
        <div className="flex flex-wrap items-center gap-1 px-3 py-4">
          {ARCH.layers.map((l, i) => (
            <div key={l} className="flex items-center">
              <div className="border border-line bg-panel-2 px-3 py-2 text-[12px] text-ink">{l}</div>
              {i < ARCH.layers.length - 1 && <span className="mx-1 text-accent" aria-hidden="true">→</span>}
            </div>
          ))}
        </div>
      </Panel>

      <div className="mt-2 grid gap-2 lg:grid-cols-3">
        <Panel>
          <PanelHead left="Backend" />
          <div className="flex flex-wrap gap-1.5 px-4 py-3">
            {ARCH.backend.map((t) => <span key={t} className="num border border-line px-2 py-0.5 text-[11px] text-ink">{t}</span>)}
          </div>
        </Panel>
        <Panel>
          <PanelHead left="Frontend" />
          <div className="flex flex-wrap gap-1.5 px-4 py-3">
            {ARCH.frontend.map((t) => <span key={t} className="num border border-line px-2 py-0.5 text-[11px] text-ink">{t}</span>)}
          </div>
        </Panel>
        <Panel>
          <PanelHead left="Code evidence" />
          <div className="grid grid-cols-3 divide-x divide-line">
            {[["python files", ARCH.pythonFiles], ["test files", ARCH.testFiles], ["test fns", ARCH.testFunctions]].map(([k, v]) => (
              <div key={k as string} className="px-3 py-3">
                <div className="num text-[20px] font-medium text-ink">{v as number}</div>
                <div className="reg text-[9px] text-ink-soft">{k as string}</div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="mt-2 text-[12px] text-ink-soft">
        Reproduce end to end: <span className="num">python -m src.run_pipeline</span> regenerates all outputs (14 fail-fast phases, deterministic), <span className="num">python -m pytest</span> runs the tests, and the frontend reads the synced outputs.{" "}
        <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="text-accent underline decoration-dotted underline-offset-2">Browse the source on GitHub.</a>
      </div>
    </Section>
  );
}
