import type { Bundle } from "../lib/load";
import { Section, Panel, PanelHead, Chip } from "../components/ui";

function KV({ obj }: { obj: Record<string, any> }) {
  return (
    <div className="divide-y divide-line">
      {Object.entries(obj || {}).map(([k, val]) => (
        <div key={k} className="grid grid-cols-[160px_1fr] gap-3 px-4 py-2">
          <span className="reg text-[10px] text-ink-soft">{k.replace(/_/g, " ")}</span>
          <span className="text-[12px] text-ink">{typeof val === "object" ? JSON.stringify(val) : String(val)}</span>
        </div>
      ))}
    </div>
  );
}

export function Methodology({ b }: { b: Bundle }) {
  const m = b.methodology;
  const dq: any[] = b.dataQuality ?? [];

  return (
    <Section id="methodology" label="Evidence & methodology" title="Data, assumptions, validation, limitations"
      note="Full disclosure. Real data labeled real; synthetic data and engineered features labeled synthetic.">
      <div className="grid gap-2 lg:grid-cols-2">
        <Panel><PanelHead left="Data sources" /><KV obj={m.data_sources} /></Panel>
        <Panel><PanelHead left="Synthetic data disclosure" /><KV obj={m.synthetic_data_disclosure} /></Panel>
      </div>

      <Panel className="mt-2">
        <PanelHead left="Default flag definition" />
        <p className="px-4 py-3 text-[12px] text-ink">{m.default_flag_definition}</p>
      </Panel>

      <div className="mt-2 grid gap-2 lg:grid-cols-2">
        <Panel><PanelHead left="Model list" /><KV obj={m.model_list} /></Panel>
        <Panel><PanelHead left="Loss & stress assumptions" /><KV obj={m.loss_assumptions} /></Panel>
      </div>

      <Panel className="mt-2">
        <PanelHead left="Known limitations" />
        <ul className="divide-y divide-line">
          {(m.known_limitations ?? []).map((l: string, i: number) => (
            <li key={i} className="px-4 py-2 text-[12px] text-ink" style={{ borderLeft: "3px solid #6c6440" }}>{l}</li>
          ))}
        </ul>
      </Panel>

      <Panel className="mt-2">
        <PanelHead left="Data quality report" right="leakage + schema gates" />
        <div className="overflow-auto">
          <div className="grid grid-cols-[1.6fr_0.7fr_0.8fr_0.8fr_0.9fr_0.9fr] reg border-b border-line bg-panel-2 text-[10px] text-ink-soft">
            {["dataset", "rows", "missing", "target rate", "leakage", "schema"].map((h) => <div key={h} className="px-3 py-2">{h}</div>)}
          </div>
          {dq.map((r) => (
            <div key={r.dataset_name} className="grid grid-cols-[1.6fr_0.7fr_0.8fr_0.8fr_0.9fr_0.9fr] items-center border-b border-line">
              <div className="num px-3 py-1.5 text-[11px] text-ink">{r.dataset_name}</div>
              <div className="num px-3 py-1.5 text-[11px] text-ink">{Number(r.row_count).toLocaleString()}</div>
              <div className="num px-3 py-1.5 text-[11px] text-ink">{r.missing_value_count}</div>
              <div className="num px-3 py-1.5 text-[11px] text-ink">{r.target_rate === "" || r.target_rate == null ? "—" : Number(r.target_rate).toFixed(3)}</div>
              <div className="px-3 py-1.5"><Chip label={r.leakage_check_status === "pass" ? "pass" : "fail"} /></div>
              <div className="px-3 py-1.5"><Chip label={r.schema_check_status === "pass" ? "pass" : "fail"} /></div>
            </div>
          ))}
        </div>
      </Panel>
    </Section>
  );
}
