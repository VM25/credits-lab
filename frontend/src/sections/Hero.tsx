import type { Bundle } from "../lib/load";
import { Panel } from "../components/ui";
import { num } from "../lib/format";

const dq = (b: Bundle, name: string, field: string) => {
  const row = (b.dataQuality || []).find((r: any) => r.dataset_name === name);
  return row ? Number(row[field]) : NaN;
};

export function Hero({ b }: { b: Bundle }) {
  const applicants = dq(b, "processed_credit_applicants", "row_count");
  const transactions = b.fraudAlerts.row_count_total;
  const scenarios = b.simulatorResults.scenario_count;
  const decisions = b.underwritingDecisions.row_count_total;
  const fraudRoc = b.fraudPolicy.roc_auc;
  const creditRoc = b.validationSummary?.credit_champion_metrics?.roc_auc;

  // Three headline numbers carry the scope of the study; model quality sits below, quieter.
  const primary = [
    { v: applicants.toLocaleString(), l: "credit applicants scored", s: "public LendingClub data" },
    { v: transactions.toLocaleString(), l: "payment transactions", s: "Kaggle ULB fraud labels" },
    { v: scenarios.toLocaleString(), l: "policy scenarios", s: "precomputed, not faked live" },
  ];

  return (
    <section id="overview" className="pb-2">
      <Panel>
        <div className="grid grid-cols-1 sm:grid-cols-3">
          {primary.map((t, i) => (
            <div key={t.l} className={`px-5 py-4 ${i > 0 ? "border-t border-line sm:border-t-0 sm:border-l" : ""}`}>
              <div className="num text-[28px] font-medium leading-none text-ink">{t.v}</div>
              <div className="mt-2 text-[12.5px] text-ink">{t.l}</div>
              <div className="reg mt-1 text-[9.5px] text-ink-soft">{t.s}</div>
            </div>
          ))}
        </div>
      </Panel>
      <p className="num mt-2 text-[11.5px] text-ink-soft">
        {decisions.toLocaleString()} underwriting decisions · fraud model ROC-AUC {num(fraudRoc, 2)} · credit model ROC-AUC {num(creditRoc, 2)} (verdict Monitor)
      </p>
    </section>
  );
}
