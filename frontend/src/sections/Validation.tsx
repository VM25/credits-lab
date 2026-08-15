import type { Bundle } from "../lib/load";
import { asVerdictList } from "../lib/load";
import { Section, Block, Stat, Scope, Label, StateWord, Tabs, TabPanel, Note, KV } from "../components/ui";
import { Term } from "../components/guide";
import { LineFlat } from "../components/charts";
import { pct, num, TOK } from "../lib/format";

const readable = (s: string) => (s || "").replace(/_/g, " ");

// One model, one answer, then the dimensions behind it.
function VerdictCard({ v }: { v: any }) {
  const dims: [string, string][] = [
    ["discrimination", v.discrimination_status],
    ["calibration", v.calibration_status],
    ["stability", v.stability_status],
    ["segments", v.segment_status],
    ["explainability", v.explainability_status],
  ].filter(([, s]) => s) as [string, string][];

  return (
    <Block tone="deep" className="px-6 py-6">
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-[15px] font-medium leading-snug text-ink">{readable(v.model_name)}</h3>
        <StateWord label={v.validation_verdict} size="lg" />
      </div>
      {v.primary_metric != null && (
        <div className="num mt-3 text-[12px] text-ink-soft">
          {readable(v.primary_metric_name)} <span className="text-[14px] text-ink">{num(v.primary_metric, 3)}</span>
        </div>
      )}
      <dl className="mt-5 space-y-1.5">
        {dims.map(([k, s]) => (
          <div key={k} className="flex items-baseline justify-between gap-4">
            <dt className="text-[12px] text-ink-soft">{k}</dt>
            <dd className="text-[12px] text-ink">{readable(s)}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-5 max-w-[44ch] text-[11.5px] leading-relaxed text-ink-faint">{v.verdict_reason}</p>
    </Block>
  );
}

export function Validation({ b }: { b: Bundle }) {
  const v = b.validationSummary;
  const verdicts = asVerdictList(b.verdicts);
  const cc = b.championChallenger;
  const champ = cc.champion ?? {};
  const chal = cc.challenger ?? {};
  const psi = v.psi ?? {};

  const cal = (v.calibration_curve ?? []).map((d: any) => ({
    mp: Number(d.mean_predicted).toFixed(2), observed: d.observed, perfect: d.mean_predicted,
  }));
  const decile: any[] = v.decile_default_table ?? [];
  const segs: any[] = v.segment_performance ?? [];
  const weak = segs.filter((s) => s.weak_segment);

  const cmp: [string, string, string][] = [
    ["ROC-AUC", num(champ.roc_auc, 4), num(chal.roc_auc, 4)],
    ["PR-AUC", num(champ.pr_auc, 4), num(chal.pr_auc, 4)],
    ["Brier after calibration", num(champ.brier_after_cal, 4), num(chal.brier_after_cal, 4)],
    ["PSI", `${num(champ.psi, 3)} ${champ.psi_status ?? ""}`, `${num(chal.psi, 3)} ${chal.psi_status ?? ""}`],
    ["explainability", String(champ.explainability ?? ""), String(chal.explainability ?? "")],
  ];

  return (
    <Section
      id="validation"
      tone="panel"
      title="Can these models be trusted to make the call?"
      lede="Validation decides which model is used and says plainly where each one is weak. A model that ranks well but is poorly calibrated or opaque does not get promoted here, and the credit scorecard's modest discrimination is disclosed rather than smoothed over."
    >
      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        {verdicts.map((x: any) => <VerdictCard key={x.model_name} v={x} />)}
      </div>

      <div className="mt-14">
        <Tabs
          tabs={[
            { value: "calibration", label: "Calibration" },
            { value: "cvc", label: "Champion vs challenger" },
            { value: "stability", label: "Stability & segments" },
          ]}
        >
          <TabPanel value="calibration">
            <div className="grid gap-10 lg:grid-cols-[1.1fr_1fr]">
              <div>
                <Label right="credit champion">Do the probabilities mean what they say? (<Term k="calibration">calibration</Term>)</Label>
                <Block tone="flat" className="px-3 py-4">
                  <LineFlat data={cal} x="mp" height={260}
                    lines={[{ key: "observed", color: TOK.accent }, { key: "perfect", color: TOK.inkSoft }]} />
                </Block>
                <p className="mt-3 max-w-[60ch] text-[12.5px] leading-relaxed text-ink-soft">
                  The observed default rate is plotted against the predicted probability. Where the
                  two lines track each other, a stated 20% really does default about one time in five.
                </p>
              </div>
              <div>
                <Label>Default rate by PD decile</Label>
                <Block tone="flat">
                  <div className="grid grid-cols-[0.6fr_1fr_1fr] border-b border-line text-[11px] text-ink-soft">
                    {["decile", "mean predicted", "observed"].map((h) => <div key={h} className="px-3 py-2">{h}</div>)}
                  </div>
                  <div className="max-h-[280px] overflow-auto">
                    {decile.map((d: any, i: number) => (
                      <div key={i} className="grid grid-cols-[0.6fr_1fr_1fr] border-b border-line/50 text-[12px]">
                        <div className="num px-3 py-1.5 text-ink">{d.decile}</div>
                        <div className="num px-3 py-1.5 text-ink">{pct(d.mean_predicted)}</div>
                        <div className="num px-3 py-1.5 text-ink">{pct(d.observed_default_rate ?? d.observed)}</div>
                      </div>
                    ))}
                  </div>
                </Block>
                <p className="mt-3 max-w-[56ch] text-[12.5px] leading-relaxed text-ink-soft">
                  Default rates rise monotonically across deciles, so the ranking is sound even where
                  the separation between good and bad accounts is modest.
                </p>
              </div>
            </div>
          </TabPanel>

          <TabPanel value="cvc">
            <div className="grid gap-10 lg:grid-cols-[1.2fr_1fr]">
              <div>
                <Label right="the simpler model holds the job">Scorecard against gradient boosting</Label>
                <div className="grid grid-cols-[1.2fr_1fr_1fr] border-b border-line pb-2 text-[12px]">
                  <span className="text-ink-soft">metric</span>
                  <span className="font-medium text-ink">champion scorecard</span>
                  <span className="text-ink-soft">challenger GBM</span>
                </div>
                {cmp.map(([k, a, c]) => (
                  <div key={k} className="grid grid-cols-[1.2fr_1fr_1fr] items-baseline border-b border-line/50 py-2.5 text-[12.5px]">
                    <span className="text-ink-soft">{k}</span>
                    <span className="num font-medium text-ink">{a}</span>
                    <span className="num text-ink-faint">{c}</span>
                  </div>
                ))}
              </div>
              <div>
                <Note>
                  The challenger ranks marginally better and is still not promoted. Where
                  every decision needs a reason code, a transparent scorecard with equivalent
                  calibration is worth more than a fractional gain in ranking from a model that
                  cannot explain itself.
                </Note>
                <div className="mt-8 grid grid-cols-2 gap-6">
                  <Stat size="md" label="champion Brier" value={num(champ.brier_after_cal, 4)} sub="after calibration" />
                  <Stat size="md" label="champion KS" value={num(v.credit_champion_metrics?.ks, 3)} sub="separation at its widest" />
                </div>
              </div>
            </div>
          </TabPanel>

          <TabPanel value="stability">
            <div className="grid gap-10 lg:grid-cols-[1fr_1.2fr]">
              <div>
                <Label right="under 0.10 is stable">Population drift (<Term k="PSI">PSI</Term>)</Label>
                <div className="divide-y divide-line/50">
                  {Object.entries(psi).map(([k, o]: [string, any]) => (
                    <KV key={k} k={readable(k)} v={`${num(o.value, 3)} · ${readable(o.status)}`} />
                  ))}
                </div>
                <p className="mt-4 max-w-[52ch] text-[12.5px] leading-relaxed text-ink-soft">
                  Both models sit inside the stable band, so the scoring population has not shifted
                  far from what they were trained on.
                </p>
              </div>
              <div>
                <Label right={`${weak.length} flagged weak`}>Performance by segment</Label>
                <Block tone="flat">
                  <div className="grid grid-cols-[1fr_0.7fr_0.7fr_0.7fr] border-b border-line text-[11px] text-ink-soft">
                    {["segment", "count", "avg score", "event rate"].map((h) => <div key={h} className="px-3 py-2">{h}</div>)}
                  </div>
                  <div className="max-h-[300px] overflow-auto">
                    {segs.map((s: any, i: number) => (
                      <div key={i} className="grid grid-cols-[1fr_0.7fr_0.7fr_0.7fr] border-b border-line/50 text-[12px]">
                        <div className="px-3 py-1.5 text-ink">
                          {readable(s.segment_type)} {s.segment_value}
                          {s.weak_segment && <span className="ml-2 text-[10.5px]" style={{ color: TOK.review }}>weak</span>}
                        </div>
                        <div className="num px-3 py-1.5 text-ink">{num(s.count, 0)}</div>
                        <div className="num px-3 py-1.5 text-ink">{pct(s.average_score)}</div>
                        <div className="num px-3 py-1.5 text-ink">{pct(s.event_rate)}</div>
                      </div>
                    ))}
                  </div>
                </Block>
                <div className="mt-3">
                  <Scope>A segment is flagged weak where its average score diverges materially from its observed event rate.</Scope>
                </div>
              </div>
            </div>
          </TabPanel>
        </Tabs>
      </div>
    </Section>
  );
}
