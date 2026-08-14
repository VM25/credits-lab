import type { Bundle } from "../lib/load";
import { Panel } from "../components/ui";
import { GithubLink } from "../components/guide";
import { num } from "../lib/format";

const dq = (b: Bundle, name: string, field: string) => {
  const row = (b.dataQuality || []).find((r: any) => r.dataset_name === name);
  return row ? Number(row[field]) : NaN;
};

export function Hero({ b }: { b: Bundle }) {
  const c = b.commandCenter;
  const applicants = dq(b, "processed_credit_applicants", "row_count");
  const decisions = b.underwritingDecisions.row_count_total;
  const transactions = b.fraudAlerts.row_count_total;
  const scenarios = b.simulatorResults.scenario_count;
  const fraudRoc = b.fraudPolicy.roc_auc;
  const creditRoc = b.validationSummary?.credit_champion_metrics?.roc_auc;

  const tiles = [
    { label: "credit applicants", value: applicants.toLocaleString(), sub: "LendingClub (real)" },
    { label: "underwriting decisions", value: num(decisions, 0) === "-" ? "-" : decisions.toLocaleString(), sub: "accepted book" },
    { label: "payment transactions", value: transactions.toLocaleString(), sub: "Kaggle (real labels)" },
    { label: "policy scenarios", value: scenarios.toLocaleString(), sub: "precomputed grid" },
    { label: "fraud ROC-AUC", value: num(fraudRoc, 3), sub: "supervised model" },
    { label: "credit champion ROC-AUC", value: num(creditRoc, 3), sub: "verdict: Monitor" },
  ];

  return (
    <section id="overview" className="py-2">
      <p className="mb-3 max-w-[90ch] text-[13.5px] leading-relaxed text-ink">
        This system turns borrower and transaction data into <span className="font-medium">underwriting decisions</span>, <span className="font-medium">fraud controls</span>, <span className="font-medium">expected-loss estimates</span>, <span className="font-medium">policy simulations</span>, and <span className="font-medium">model-validation evidence</span> - a decision engine, not a prediction notebook.
      </p>

      <Panel>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6">
          {tiles.map((t, i) => (
            <div key={t.label} className={`px-4 py-3 ${i % 6 !== 0 ? "border-l border-line" : ""} ${i >= 3 ? "border-t border-line md:border-t-0 lg:border-t-0" : ""}`}>
              <div className="reg text-[9px] text-ink-soft">{t.label}</div>
              <div className="num mt-1 text-[19px] font-medium text-ink">{t.value}</div>
              <div className="mt-0.5 text-[10px] text-ink-soft">{t.sub}</div>
            </div>
          ))}
        </div>
      </Panel>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <GithubLink />
        <a href="#workflow" className="reg text-[10.5px] text-accent hover:underline">How the engine works ↓</a>
        <span className="text-[12px] text-ink-soft">{c.data_disclaimer}</span>
      </div>
    </section>
  );
}
