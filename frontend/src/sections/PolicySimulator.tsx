import { useMemo, useState } from "react";
import type { Bundle } from "../lib/load";
import { Section, Panel, PanelHead, MetricRow } from "../components/ui";
import { StepSlider } from "../components/StepSlider";
import { pct, money, num } from "../lib/format";

const near = (a: number, b: number) => Math.abs(a - b) < 1e-6;

export function PolicySimulator({ b }: { b: Bundle }) {
  const inp = b.simulatorInputs;
  const scenarios: any[] = b.simulatorResults.scenarios ?? [];

  const stressOpts: string[] = inp.stress.options;
  const approveOpts: number[] = inp.credit.approve_pd_cutoff.options;
  const fraudOpts: number[] = inp.fraud.review_threshold.options;
  const stableOpts: number[] = inp.stablecoin.high_risk_threshold.options;

  const [sI, setSI] = useState(stressOpts.indexOf(inp.defaults.stress));
  const [aI, setAI] = useState(Math.max(0, approveOpts.indexOf(inp.defaults.approve)));
  const [fI, setFI] = useState(Math.max(0, fraudOpts.indexOf(inp.defaults.fraud_review)));
  const [kI, setKI] = useState(Math.max(0, stableOpts.indexOf(inp.defaults.stablecoin_high_risk)));

  const scen = useMemo(() => scenarios.find((s) =>
    s.stress_scenario === stressOpts[sI] &&
    near(s.credit_pd_cutoff, approveOpts[aI]) &&
    near(s.fraud_threshold, fraudOpts[fI]) &&
    near(s.stablecoin_threshold, stableOpts[kI])
  ), [sI, aI, fI, kI, scenarios, stressOpts, approveOpts, fraudOpts, stableOpts]);

  return (
    <Section id="policy-simulator" label="Policy simulator" title="Threshold changes → growth vs loss tradeoff"
      note={`Controls snap to a precomputed scenario grid (${scenarios.length} scenarios). The interface looks up real backend results; it does not recompute risk client-side.`}>
      <div className="grid gap-2 lg:grid-cols-[320px_1fr]">
        <Panel>
          <PanelHead left="Policy controls" />
          <div className="space-y-4 px-4 py-4">
            <StepSlider label="approve PD cutoff" options={approveOpts} index={aI} onChange={setAI}
              format={(v) => `${pct(Number(v))}${near(Number(v), inp.credit.approve_pd_cutoff.doc_reference) ? " (doc ref)" : ""}`} />
            <StepSlider label="fraud review threshold" options={fraudOpts} index={fI} onChange={setFI} format={(v) => num(Number(v), 2)} />
            <StepSlider label="stablecoin high-risk threshold" options={stableOpts} index={kI} onChange={setKI} format={(v) => num(Number(v), 2)} />
            <StepSlider label="stress scenario" options={stressOpts} index={sI} onChange={setSI} format={(v) => String(v)} />
            <div className="num text-[10px] text-ink-soft">decline cutoff = approve + review band ({num(inp.credit.review_band.value, 2)})</div>
          </div>
        </Panel>

        <div>
          {scen ? (
            <>
              <MetricRow items={[
                { label: "approval rate", value: pct(scen.approval_rate) },
                { label: "review rate", value: pct(scen.review_rate) },
                { label: "decline rate", value: pct(scen.decline_rate) },
                { label: "manual review", value: num(scen.manual_review_volume, 0) },
              ]} />
              <div className="mt-2">
                <MetricRow items={[
                  { label: "expected credit loss", value: money(scen.expected_credit_loss) },
                  { label: "residual fraud loss", value: money(scen.expected_fraud_loss) },
                  { label: "stablecoin exposure", value: money(scen.stablecoin_risk_exposure) },
                  { label: "total expected loss", value: money(scen.total_expected_loss) },
                ]} />
              </div>
              <Panel className="mt-2">
                <PanelHead left="Model-risk warnings" right={`${(scen.model_risk_warnings || []).length} active`} />
                <div className="divide-y divide-line">
                  {(scen.model_risk_warnings || []).length === 0 && (
                    <div className="px-4 py-3 text-[12px] text-ink-soft">No warnings at this configuration.</div>
                  )}
                  {(scen.model_risk_warnings || []).map((w: string, i: number) => (
                    <div key={i} className="px-4 py-2 text-[12px] text-ink" style={{ borderLeft: "3px solid #6c6440" }}>{w}</div>
                  ))}
                </div>
              </Panel>
            </>
          ) : (
            <Panel><div className="px-4 py-6 text-[13px] text-ink-soft">No scenario for this combination.</div></Panel>
          )}
        </div>
      </div>
    </Section>
  );
}
