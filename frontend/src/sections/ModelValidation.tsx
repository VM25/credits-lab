import type { Bundle } from "../lib/load";
import { asVerdictList } from "../lib/load";
import { Section, Panel, PanelHead, Chip } from "../components/ui";
import { LineFlat } from "../components/charts";
import { pct, num, TOK } from "../lib/format";

export function ModelValidation({ b }: { b: Bundle }) {
  const v = b.validationSummary;
  const verdicts = asVerdictList(b.verdicts);
  const cc = b.championChallenger;
  const cal = (v.calibration_curve ?? []).map((d: any) => ({
    mp: Number(d.mean_predicted).toFixed(2), observed: d.observed, perfect: d.mean_predicted,
  }));
  const decile: any[] = v.decile_default_table ?? [];

  const champ = cc.champion ?? {};
  const chal = cc.challenger ?? {};
  const cmpRows = [
    ["ROC-AUC", num(champ.roc_auc, 4), num(chal.roc_auc, 4)],
    ["PR-AUC", num(champ.pr_auc, 4), num(chal.pr_auc, 4)],
    ["Brier (calibrated)", num(champ.brier_after_cal, 4), num(chal.brier_after_cal, 4)],
    ["PSI / status", `${num(champ.psi, 3)} ${champ.psi_status ?? ""}`, `${num(chal.psi, 3)} ${chal.psi_status ?? ""}`],
    ["explainability", String(champ.explainability ?? ""), String(chal.explainability ?? "")],
  ];

  return (
    <Section id="validation" label="Model risk & validation" title="Can the models be trusted for decisions?"
      note="Calibration, drift (PSI), discrimination, segment behavior, and champion-vs-challenger. Verdicts weigh calibration and explainability, not AUC alone.">

      <Panel>
        <PanelHead left="Model verdicts" right="Pass / Monitor / Fail" />
        <div className="divide-y divide-line">
          {verdicts.map((r: any) => (
            <div key={r.model_name} className="px-4 py-2.5">
              <div className="flex items-center justify-between">
                <span className="num text-[12px] text-ink">{r.model_name.replace(/_/g, " ")}</span>
                <div className="flex items-center gap-2">
                  <span className="num text-[11px] text-ink-soft">{r.primary_metric_name?.replace(/_/g, " ")} {num(r.primary_metric, 3)}</span>
                  <Chip label={r.validation_verdict} />
                </div>
              </div>
              <p className="mt-1 text-[12px] text-ink-soft">{r.verdict_reason}</p>
            </div>
          ))}
        </div>
      </Panel>

      <div className="mt-2 grid gap-2 lg:grid-cols-2">
        <Panel>
          <PanelHead left="Credit calibration curve" right="predicted vs observed" />
          <div className="px-3 py-3">
            <LineFlat data={cal} x="mp" lines={[{ key: "observed", color: TOK.accent }, { key: "perfect", color: TOK.line }]} />
          </div>
        </Panel>
        <Panel>
          <PanelHead left="PD decile default table" />
          <div className="max-h-[240px] overflow-auto">
            <div className="grid grid-cols-4 reg border-b border-line bg-panel-2 text-[10px] text-ink-soft">
              {["decile", "mean PD", "actual default", "count"].map((h) => <div key={h} className="px-3 py-1.5">{h}</div>)}
            </div>
            {decile.map((d) => (
              <div key={d.decile} className="grid grid-cols-4 border-b border-line">
                <div className="num px-3 py-1.5 text-[12px] text-ink">{d.decile}</div>
                <div className="num px-3 py-1.5 text-[12px] text-ink">{pct(d.pd_mean)}</div>
                <div className="num px-3 py-1.5 text-[12px] text-ink">{pct(d.actual_default_rate)}</div>
                <div className="num px-3 py-1.5 text-[12px] text-ink">{num(d.count, 0)}</div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Panel className="mt-2">
        <PanelHead left="Champion vs challenger" right={`recommended: ${cc.recommendation?.replace(/_/g, " ")}`} />
        <div className="grid grid-cols-[1.2fr_1fr_1fr] reg border-b border-line bg-panel-2 text-[10px] text-ink-soft">
          <div className="px-3 py-2">metric</div>
          <div className="px-3 py-2">champion (scorecard)</div>
          <div className="px-3 py-2">challenger (GBM)</div>
        </div>
        {cmpRows.map((r) => (
          <div key={r[0]} className="grid grid-cols-[1.2fr_1fr_1fr] border-b border-line">
            <div className="px-3 py-1.5 text-[12px] text-ink-soft">{r[0]}</div>
            <div className="num px-3 py-1.5 text-[12px] text-ink">{r[1]}</div>
            <div className="num px-3 py-1.5 text-[12px] text-ink">{r[2]}</div>
          </div>
        ))}
        <p className="px-4 py-2.5 text-[12px] text-ink-soft">{cc.rationale}</p>
      </Panel>
    </Section>
  );
}
