import type { Bundle } from "../lib/load";
import { Section, Block, Stat, Scope, Label, Tabs, TabPanel, Note, StateWord } from "../components/ui";
import { ARCH } from "../lib/site";
import { num } from "../lib/format";

const readable = (s: string) => (s || "").replace(/_/g, " ");

// Definition list for a flat record of facts. No boxes, no borders per row.
function Facts({ obj }: { obj: Record<string, any> }) {
  return (
    <dl className="divide-y divide-line/50">
      {Object.entries(obj || {}).map(([k, val]) => (
        <div key={k} className="grid gap-1 py-2.5 md:grid-cols-[210px_1fr] md:gap-6">
          <dt className="text-[12px] text-ink-soft">{readable(k)}</dt>
          <dd className="max-w-[80ch] text-[12.5px] leading-relaxed text-ink">
            {Array.isArray(val)
              ? <ul className="space-y-1">{val.map((x, i) => <li key={i}>{String(x)}</li>)}</ul>
              : typeof val === "object" && val !== null
                ? <ul className="space-y-1">{Object.entries(val).map(([kk, vv]) => (
                    <li key={kk}><span className="text-ink-soft">{readable(kk)}: </span><span className="num">{String(vv)}</span></li>
                  ))}</ul>
                : String(val)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function Evidence({ b }: { b: Bundle }) {
  const m = b.methodology;
  const dq: any[] = b.dataQuality ?? [];
  const limits: string[] = Array.isArray(m.known_limitations) ? m.known_limitations : [];

  return (
    <Section
      id="evidence"
      title="The receipts."
      lede="Everything the results rest on: where the data came from, what is synthetic, which assumptions were imposed, how the models were validated, and what this project does not support. Nothing here is hidden behind a summary."
    >
      <Tabs
        tabs={[
          { value: "data", label: "Data" },
          { value: "models", label: "Models" },
          { value: "assumptions", label: "Assumptions" },
          { value: "limits", label: "Limitations" },
          { value: "quality", label: "Data quality" },
          { value: "arch", label: "Architecture" },
        ]}
      >
        <TabPanel value="data">
          <div className="grid gap-12 lg:grid-cols-2">
            <div>
              <Label>Sources</Label>
              <Facts obj={m.data_sources} />
            </div>
            <div>
              <Label>What is synthetic</Label>
              <Facts obj={m.synthetic_data_disclosure} />
              <div className="mt-8">
                <Label>Default flag definition</Label>
                <p className="max-w-[80ch] text-[12.5px] leading-relaxed text-ink">{m.default_flag_definition}</p>
                <div className="mt-3"><Scope>Labeled throughout as a default / severe-delinquency proxy, not pure charge-off default.</Scope></div>
              </div>
            </div>
          </div>
        </TabPanel>

        <TabPanel value="models">
          <div className="grid gap-12 lg:grid-cols-2">
            <div>
              <Label>Models</Label>
              <Facts obj={m.model_list} />
            </div>
            <div>
              <Label>How they were split and validated</Label>
              <Facts obj={{ split_method: m.split_method, ...(m.validation_methods || {}) }} />
              <div className="mt-8">
                <Label>Operating point</Label>
                <Facts obj={m.operating_point} />
              </div>
            </div>
          </div>
        </TabPanel>

        <TabPanel value="assumptions">
          <div className="grid gap-12 lg:grid-cols-2">
            <div>
              <Label>Loss assumptions</Label>
              <Facts obj={m.loss_assumptions} />
            </div>
            <div>
              <Label>Stress assumptions</Label>
              <Facts obj={m.stress_assumptions} />
            </div>
          </div>
          <div className="mt-8 max-w-[86ch]">
            <Note tone="caveat">
              Every dollar figure on this site inherits these assumptions. They are imposed
              parameters, not estimates recovered from recovery or collections data.
            </Note>
          </div>
        </TabPanel>

        <TabPanel value="limits">
          <ul className="max-w-[90ch] space-y-3">
            {limits.map((l, i) => (
              <li key={i} className="pl-4 text-[13px] leading-relaxed text-ink" style={{ borderLeft: "2px solid #6C6440" }}>
                {l}
              </li>
            ))}
          </ul>
          <div className="mt-8 max-w-[86ch]">
            <Note>
              This is a research project on public and synthetic data. It makes no lending
              decisions, touches no customer records, and supports no regulatory-compliance claim.
            </Note>
          </div>
        </TabPanel>

        <TabPanel value="quality">
          <Label right="every gate must pass before an output is written">Leakage and schema gates</Label>
          <Block tone="flat" className="overflow-x-auto">
            <div className="min-w-[820px]">
              <div className="grid grid-cols-[1.6fr_0.7fr_0.6fr_0.7fr_0.7fr_0.8fr_0.8fr] border-b border-line text-[11px] text-ink-soft">
                {["dataset", "rows", "cols", "missing", "target rate", "leakage", "schema"].map((h) => (
                  <div key={h} className="px-3 py-2">{h}</div>
                ))}
              </div>
              {dq.map((r: any, i: number) => (
                <div key={i} className="grid grid-cols-[1.6fr_0.7fr_0.6fr_0.7fr_0.7fr_0.8fr_0.8fr] border-b border-line/50 text-[12px]">
                  <div className="px-3 py-2 text-ink">{readable(r.dataset_name)}</div>
                  <div className="num px-3 py-2 text-ink">{num(r.row_count, 0)}</div>
                  <div className="num px-3 py-2 text-ink">{num(r.column_count, 0)}</div>
                  <div className="num px-3 py-2 text-ink">{num(r.missing_value_count, 0)}</div>
                  <div className="num px-3 py-2 text-ink">{r.target_rate == null || r.target_rate === "" ? "-" : num(Number(r.target_rate), 3)}</div>
                  <div className="px-3 py-2"><StateWord label={String(r.leakage_check_status)} size="sm" /></div>
                  <div className="px-3 py-2"><StateWord label={String(r.schema_check_status)} size="sm" /></div>
                </div>
              ))}
            </div>
          </Block>
          <div className="mt-3">
            <Scope>
              Leakage is guarded structurally: only application-time credit fields are read, and the
              fraud label and chargeback amount are excluded from fraud model features by an
              explicit exclusion set.
            </Scope>
          </div>
        </TabPanel>

        <TabPanel value="arch">
          <div className="grid gap-12 lg:grid-cols-[1.2fr_1fr]">
            <div>
              <Label>Build pipeline</Label>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                {ARCH.layers.map((l, i) => (
                  <span key={l} className="flex items-center gap-3">
                    <span className="text-[12.5px] text-ink">{l}</span>
                    {i < ARCH.layers.length - 1 && <span className="text-accent" aria-hidden="true">→</span>}
                  </span>
                ))}
              </div>
              <p className="mt-6 max-w-[70ch] text-[12.5px] leading-relaxed text-ink-soft">
                One orchestrator runs fourteen fail-fast phases in order and writes every output
                deterministically. The interface is a thin reader over those files, which is why no
                figure on this site can drift from the pipeline that produced it.
              </p>
              <div className="mt-8 flex flex-wrap gap-x-12 gap-y-6">
                <Stat size="md" label="python source files" value={ARCH.pythonFiles} />
                <Stat size="md" label="test files" value={ARCH.testFiles} />
                <Stat size="md" label="test functions" value={ARCH.testFunctions} />
              </div>
            </div>
            <div>
              <Label>Backend</Label>
              <p className="text-[12.5px] leading-relaxed text-ink">{ARCH.backend.join(" · ")}</p>
              <div className="mt-7">
                <Label>Frontend</Label>
                <p className="text-[12.5px] leading-relaxed text-ink">{ARCH.frontend.join(" · ")}</p>
              </div>
              <div className="mt-7">
                <Label>Reproduce it</Label>
                <p className="num max-w-[46ch] text-[12px] leading-relaxed text-ink-soft">
                  python -m src.run_pipeline<br />python -m pytest
                </p>
              </div>
            </div>
          </div>
        </TabPanel>
      </Tabs>
    </Section>
  );
}
