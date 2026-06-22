import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { Bundle } from "../lib/load";
import { Section, Panel, PanelHead, Chip } from "../components/ui";
import { BarFlat } from "../components/charts";
import { pct, money, num, TOK, stateColor } from "../lib/format";

const toArr = (o: Record<string, number>) => Object.entries(o || {}).map(([name, value]) => ({ name, value }));

export function Underwriting({ b }: { b: Bundle }) {
  const p = b.underwritingPolicy;
  const rows: any[] = b.underwritingDecisions.rows ?? [];
  const [sel, setSel] = useState<number | null>(null);
  const view = rows.slice(0, 40);

  const pdHist = (p.champion_vs_challenger?.champion?.pd_distribution ?? []).map((d: any) => ({
    bin: d.bin_left?.toFixed ? d.bin_left.toFixed(2) : d.bin_left, count: d.count,
  }));
  const grades = toArr(p.risk_grade_distribution).sort((a, b) => a.name.localeCompare(b.name));
  const mix = toArr(p.approval_mix);
  const elGrade = toArr(p.expected_loss_by_risk_grade).sort((a, b) => a.name.localeCompare(b.name));
  const reasons = toArr(p.top_decline_reasons).sort((a, b) => b.value - a.value).slice(0, 7);

  return (
    <Section id="underwriting" label="Underwriting decision engine" title="Applicant data → credit decision"
      note={`Champion logistic scorecard (calibrated PD). Showing ${view.length} of ${num(b.underwritingDecisions.row_count_total, 0)} accepted applicants (a labeled display sample); aggregates below are over the full book.`}>

      <div className="grid gap-2 lg:grid-cols-2">
        <Panel>
          <PanelHead left="PD distribution (calibrated)" />
          <div className="px-3 py-3"><BarFlat data={pdHist} x="bin" y="count" /></div>
        </Panel>
        <Panel>
          <PanelHead left="Expected loss by risk grade" />
          <div className="px-3 py-3"><BarFlat data={elGrade} x="name" y="value" money /></div>
        </Panel>
      </div>

      <div className="mt-2 grid gap-2 lg:grid-cols-3">
        <Panel>
          <PanelHead left="Risk grade mix" />
          <div className="px-3 py-3"><BarFlat data={grades} x="name" y="value" height={180} /></div>
        </Panel>
        <Panel>
          <PanelHead left="Approve / review / decline" />
          <div className="px-3 py-3"><BarFlat data={mix} x="name" y="value" height={180} colorFor={(r) => stateColor(r.name)} /></div>
        </Panel>
        <Panel>
          <PanelHead left="Top decline reasons" />
          <div className="px-3 py-3"><BarFlat data={reasons} x="name" y="value" height={180} colorFor={() => TOK.fail} /></div>
        </Panel>
      </div>

      <Panel className="mt-2">
        <PanelHead left="Applicant decisions" right="select a row for reason codes" />
        <div className="grid grid-cols-[1.1fr_0.7fr_0.6fr_0.9fr_0.9fr_0.9fr] reg border-b border-line bg-panel-2 text-[10px] text-ink-soft">
          {["applicant", "PD", "grade", "decision", "limit", "expected loss"].map((h) => (
            <div key={h} className="px-3 py-2">{h}</div>
          ))}
        </div>
        <div className="max-h-[420px] overflow-auto">
          {view.map((r, i) => (
            <div key={r.applicant_id}>
              <button
                onClick={() => setSel(sel === i ? null : i)}
                className="grid w-full grid-cols-[1.1fr_0.7fr_0.6fr_0.9fr_0.9fr_0.9fr] items-center border-b border-line text-left hover:bg-panel-2"
                style={sel === i ? { background: "#bcc9bb" } : undefined}
              >
                <div className="num px-3 py-2 text-[12px] text-ink">{r.applicant_id}</div>
                <div className="num px-3 py-2 text-[12px] text-ink">{pct(r.PD)}</div>
                <div className="num px-3 py-2 text-[12px] text-ink">{r.risk_grade}</div>
                <div className="px-3 py-2"><Chip label={r.decision} /></div>
                <div className="num px-3 py-2 text-[12px] text-ink">{money(r.recommended_credit_limit)}</div>
                <div className="num px-3 py-2 text-[12px] text-ink">{money(r.expected_loss)}</div>
              </button>
              <AnimatePresence>
                {sel === i && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.18 }} className="overflow-hidden border-b border-line bg-bg">
                    <div className="px-4 py-3">
                      <div className="reg text-[10px] text-ink-soft">reason codes · model: {r.model_used}</div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {[r.top_reason_1, r.top_reason_2, r.top_reason_3].filter(Boolean).map((rc: string, k: number) => (
                          <span key={k} className="num border border-line px-2 py-1 text-[11px] text-ink">{rc.replace(/_/g, " ")}</span>
                        ))}
                      </div>
                      <div className="mt-2 num text-[11px] text-ink-soft">
                        LGD {num(r.LGD, 2)} · EAD {money(r.EAD)} · EL rate {pct(r.expected_loss_rate)}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>
      </Panel>
    </Section>
  );
}
