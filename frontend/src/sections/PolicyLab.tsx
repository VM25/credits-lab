import { useMemo, useState } from "react";
import type { Bundle } from "../lib/load";
import { Section, Block, Stat, Scope, Label, Tabs, TabPanel, Note } from "../components/ui";
import { StepSlider } from "../components/StepSlider";
import { BarFlat } from "../components/charts";
import { pct, money, num, TOK } from "../lib/format";

const near = (a: number, b: number) => Math.abs(a - b) < 1e-6;

// One consequence line: baseline value -> current value, with a signed delta.
function Delta({ label, base, cur, kind, better = "down" }: {
  label: string; base: number; cur: number;
  kind: "pct" | "money" | "int"; better?: "down" | "up" | "none";
}) {
  const fmt = (v: number) => (kind === "pct" ? pct(v) : kind === "money" ? money(v) : num(v, 0));
  const d = cur - base;
  const moved = Math.abs(d) > (kind === "pct" ? 1e-6 : 0.5);
  const good = better === "none" ? null : better === "down" ? d < 0 : d > 0;
  const col = !moved ? TOK.inkSoft : good ? TOK.pass : TOK.fail;
  const deltaText =
    kind === "pct" ? `${d > 0 ? "+" : ""}${(d * 100).toFixed(1)} pp`
    : kind === "money" ? `${d > 0 ? "+" : ""}${money(d)}`
    : `${d > 0 ? "+" : ""}${num(d, 0)}`;

  return (
    <div className="grid grid-cols-[1.25fr_0.8fr_0.8fr] items-baseline gap-3 border-b border-line/50 py-2.5">
      <span className="text-[12.5px] text-ink">{label}</span>
      <span className="num text-[12.5px] text-ink-faint">{fmt(base)}</span>
      <span className="text-right">
        <span className="num text-[15px] font-medium text-ink">{fmt(cur)}</span>
        {moved && <span className="num ml-2 text-[11px]" style={{ color: col }}>{deltaText}</span>}
      </span>
    </div>
  );
}

export function PolicyLab({ b }: { b: Bundle }) {
  const inp = b.simulatorInputs;
  const scenarios: any[] = b.simulatorResults.scenarios ?? [];
  const stressOpts: string[] = inp.stress.options;
  const approveOpts: number[] = inp.credit.approve_pd_cutoff.options;
  const fraudOpts: number[] = inp.fraud.review_threshold.options;
  const stableOpts: number[] = inp.stablecoin.high_risk_threshold.options;

  const d = inp.defaults;
  const [sI, setSI] = useState(Math.max(0, stressOpts.indexOf(d.stress)));
  const [aI, setAI] = useState(Math.max(0, approveOpts.indexOf(d.approve)));
  const [fI, setFI] = useState(Math.max(0, fraudOpts.indexOf(d.fraud_review)));
  const [kI, setKI] = useState(Math.max(0, stableOpts.indexOf(d.stablecoin_high_risk)));

  const lookup = (stress: string, a: number, f: number, k: number) =>
    scenarios.find((s) =>
      s.stress_scenario === stress && near(s.credit_pd_cutoff, a) &&
      near(s.fraud_threshold, f) && near(s.stablecoin_threshold, k));

  const baseline = useMemo(
    () => lookup(d.stress, d.approve, d.fraud_review, d.stablecoin_high_risk),
    [scenarios]);
  const scen = useMemo(
    () => lookup(stressOpts[sI], approveOpts[aI], fraudOpts[fI], stableOpts[kI]),
    [sI, aI, fI, kI, scenarios]);

  const changed = scen && baseline && scen.scenario_id !== baseline.scenario_id;
  const reset = () => {
    setSI(Math.max(0, stressOpts.indexOf(d.stress)));
    setAI(Math.max(0, approveOpts.indexOf(d.approve)));
    setFI(Math.max(0, fraudOpts.indexOf(d.fraud_review)));
    setKI(Math.max(0, stableOpts.indexOf(d.stablecoin_high_risk)));
  };

  // stress scenarios
  const sc = b.stressLoss.scenarios;
  const order = ["base", "moderate", "severe"];
  const totalBars = order.map((k) => ({ name: k, value: sc[k]?.total_expected_loss }));
  const creditBars = order.map((k) => ({ name: k, value: sc[k]?.expected_credit_loss }));
  const sev = sc.severe?.total_expected_loss, bas = sc.base?.total_expected_loss;
  const sevMult = sev && bas ? sev / bas : null;
  const stressCol = (n: string) => (n === "severe" ? TOK.fail : n === "moderate" ? TOK.review : TOK.accent);

  return (
    <Section
      id="policy-lab"
      tone="panel"
      title="Change the policy, and watch what it costs."
      lede="Thresholds are the only real lever here: the models are fixed, the cutoffs are not. Every combination below was computed in the backend beforehand, so moving a control looks up a stored scenario rather than inventing one."
    >
      <Tabs tabs={[{ value: "thresholds", label: "Policy thresholds" }, { value: "stress", label: "Stress scenarios" }]}>
        <TabPanel value="thresholds">
          <div className="grid gap-8 lg:grid-cols-[330px_1fr] lg:gap-14">
            {/* controls */}
            <div>
              <Label right={changed ? undefined : "at baseline"}>Policy controls</Label>
              <Block tone="deep" className="space-y-6 px-5 py-6">
                <StepSlider label="Approve if PD below" options={approveOpts} index={aI} onChange={setAI} format={(v) => pct(Number(v), 0)} />
                <StepSlider label="Fraud review threshold" options={fraudOpts} index={fI} onChange={setFI} format={(v) => num(Number(v), 2)} />
                <StepSlider label="Stablecoin high-risk threshold" options={stableOpts} index={kI} onChange={setKI} format={(v) => num(Number(v), 2)} />
                <StepSlider label="Economic conditions" options={stressOpts} index={sI} onChange={setSI} format={(v) => String(v)} />
                {changed && (
                  <button onClick={reset} className="text-[12px] text-accent underline underline-offset-2 hover:text-ink">
                    reset to baseline
                  </button>
                )}
              </Block>
              <div className="mt-3">
                <Scope>
                  {scenarios.length} stored scenarios: {approveOpts.length} credit cutoffs x{" "}
                  {fraudOpts.length} fraud thresholds x {stableOpts.length} stablecoin thresholds x{" "}
                  {stressOpts.length} economic cases.
                </Scope>
              </div>
            </div>

            {/* consequences */}
            <div>
              <div className="grid grid-cols-[1.25fr_0.8fr_0.8fr] gap-3 border-b border-line pb-2">
                <span className="text-[12px] font-medium text-ink-soft">Consequence</span>
                <span className="text-[12px] text-ink-faint">baseline</span>
                <span className="text-right text-[12px] font-medium text-ink">current selection</span>
              </div>

              {scen && baseline ? (
                <div className="mt-1">
                  <Delta label="Approval rate" base={baseline.approval_rate} cur={scen.approval_rate} kind="pct" better="up" />
                  <Delta label="Review rate" base={baseline.review_rate} cur={scen.review_rate} kind="pct" better="down" />
                  <Delta label="Decline rate" base={baseline.decline_rate} cur={scen.decline_rate} kind="pct" better="down" />
                  <Delta label="Expected credit loss (approved accounts only)" base={baseline.expected_credit_loss} cur={scen.expected_credit_loss} kind="money" better="down" />
                  <Delta label="Expected fraud loss (let through)" base={baseline.expected_fraud_loss} cur={scen.expected_fraud_loss} kind="money" better="down" />
                  <Delta label="Stablecoin exposure (high-risk wallets)" base={baseline.stablecoin_risk_exposure} cur={scen.stablecoin_risk_exposure} kind="money" better="down" />
                  <Delta label="Manual review volume" base={baseline.manual_review_volume} cur={scen.manual_review_volume} kind="int" better="down" />
                  <Delta label="Total expected loss" base={baseline.total_expected_loss} cur={scen.total_expected_loss} kind="money" better="down" />
                </div>
              ) : (
                <p className="mt-4 text-[13px] text-ink-soft">No stored scenario for this combination.</p>
              )}

              {scen?.model_risk_warnings?.length > 0 && (
                <div className="mt-7">
                  <Label>Risk warnings raised by this policy</Label>
                  <ul className="space-y-1.5">
                    {scen.model_risk_warnings.map((wn: string) => (
                      <li key={wn} className="pl-3 text-[12.5px] leading-snug text-ink" style={{ borderLeft: `2px solid ${TOK.review}` }}>
                        {wn}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="mt-7">
                <Scope>
                  Baseline is the validation-supported operating point (approve below{" "}
                  {pct(d.approve, 0)}, decline at or above {pct(b.policyLoss?.operating_point?.decline ?? 0.3, 0)}),
                  under base conditions. These are policy-conditional quantities and deliberately
                  narrower than the portfolio totals in Overview and Expected loss: credit loss here
                  counts approved accounts only, fraud loss counts what the threshold lets through,
                  and stablecoin counts wallets at or above the high-risk cutoff. All modeled, not
                  realized.
                </Scope>
              </div>
            </div>
          </div>
        </TabPanel>

        <TabPanel value="stress">
          <div className="grid gap-10 lg:grid-cols-[1fr_1fr]">
            <div>
              <Label right="PD, LGD and fraud multipliers">Total expected loss by scenario</Label>
              <Block tone="flat" className="px-3 py-4">
                <BarFlat data={totalBars} x="name" y="value" money height={250} colorFor={(r) => stressCol(r.name)} />
              </Block>
              <p className="mt-3 max-w-[58ch] text-[12.5px] leading-relaxed text-ink-soft">
                {sevMult
                  ? `A severe downturn lifts total modeled loss to ${sevMult.toFixed(2)}x the base case, driven by the credit portfolio rather than fraud.`
                  : "Modeled loss under base, moderate and severe conditions."}
              </p>
            </div>
            <div>
              <Label>Credit loss carries the increase</Label>
              <Block tone="flat" className="px-3 py-4">
                <BarFlat data={creditBars} x="name" y="value" money height={250} colorFor={(r) => stressCol(r.name)} />
              </Block>
              <div className="mt-4 grid grid-cols-3 gap-4">
                {order.map((k) => (
                  <Stat key={k} size="sm" label={k} value={money(sc[k]?.total_expected_loss)}
                    sub={`PD x${num(sc[k]?.pd_multiplier, 2)} · LGD x${num(sc[k]?.lgd_multiplier, 2)}`} />
                ))}
              </div>
            </div>
          </div>
          <div className="mt-8 max-w-[86ch]">
            <Note>
              These scenarios are portfolio-wide: they cover every scored applicant and transaction,
              which is why the base case matches the Overview total rather than the smaller,
              approved-only figure on the Policy thresholds tab. Stress is applied by scaling PD,
              LGD and fraud-loss multipliers, with PD capped at 1.0. Macro series inform the choice
              of multipliers only; no causal link between a macro variable and an individual default
              is claimed. Base-case figures are recomputed through the multiplier path, so they can
              differ from the headline total by a few dollars of rounding.
            </Note>
          </div>
        </TabPanel>
      </Tabs>
    </Section>
  );
}
