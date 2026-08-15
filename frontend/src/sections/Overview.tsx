import type { Bundle } from "../lib/load";
import { Section, Block, Stat, Scope, StateWord, Label } from "../components/ui";
import { DecisionTrace } from "../components/DecisionTrace";
import { pct, money, num } from "../lib/format";

const STEPS = ["Data", "Risk score", "Policy", "Decision", "Expected loss", "Validation"];

const dq = (b: Bundle, name: string, field: string) => {
  const row = (b.dataQuality || []).find((r: any) => r.dataset_name === name);
  return row ? Number(row[field]) : NaN;
};

export function Overview({ b }: { b: Bundle }) {
  const c = b.commandCenter;
  const applicants = dq(b, "processed_credit_applicants", "row_count");
  const transactions = b.fraudAlerts.row_count_total;
  const scenarios = b.simulatorResults.scenario_count;
  const decisions = b.underwritingDecisions.row_count_total;
  const creditRoc = b.validationSummary?.credit_champion_metrics?.roc_auc;
  const fraudRoc = b.validationSummary?.fraud_supervised_metrics?.roc_auc;
  const verdicts: Record<string, string> = c.model_verdict_summary?.by_model ?? {};
  const hrs = c.highest_risk_segment ?? {};

  return (
    <Section
      id="overview"
      title="Turning borrower and transaction data into decisions someone has to defend."
      lede="A credit and payments risk engine built end to end: probability of default and fraud scores become governed actions under loss, capacity and model-risk constraints. Every figure on this site is read from the pipeline's own output files."
    >
      {/* research scope - typography, not tiles */}
      <div className="grid gap-8 sm:grid-cols-3 lg:max-w-[62%]">
        <Stat size="lg" label="credit applicants scored" value={applicants.toLocaleString()} sub="public LendingClub sample" />
        <Stat size="lg" label="payment transactions" value={transactions.toLocaleString()} sub="public Kaggle ULB fraud labels" />
        <Stat size="lg" label="policy scenarios" value={scenarios.toLocaleString()} sub="precomputed in the backend" />
      </div>

      <div className="mt-6 flex flex-wrap gap-x-8 gap-y-2 text-[12px] text-ink-soft">
        <span><span className="num text-ink">{decisions.toLocaleString()}</span> underwriting decisions</span>
        <span>credit model ROC-AUC <span className="num text-ink">{num(creditRoc, 3)}</span></span>
        <span>fraud model ROC-AUC <span className="num text-ink">{num(fraudRoc, 3)}</span></span>
      </div>

      {/* the pipeline, in one line */}
      <div className="mt-10 flex flex-wrap items-center gap-x-3 gap-y-2">
        {STEPS.map((s, i) => (
          <span key={s} className="flex items-center gap-3">
            <span className="text-[13px] text-ink">{s}</span>
            {i < STEPS.length - 1 && <span className="text-accent" aria-hidden="true">→</span>}
          </span>
        ))}
      </div>

      {/* signature */}
      <div className="mt-8">
        <DecisionTrace b={b} />
      </div>

      {/* current policy state */}
      <div className="mt-14">
        <h3 className="text-[17px] font-semibold tracking-tight text-ink">Where the modeled portfolio stands</h3>
        <p className="mt-2 max-w-[74ch] text-[13px] leading-relaxed text-ink-soft">
          The state of the whole modeled portfolio at the current operating point, before drilling
          into any single applicant or transaction.
        </p>

        <div className="mt-7 grid gap-x-10 gap-y-9 md:grid-cols-2 lg:grid-cols-4">
          <div>
            <Label>Credit decision mix</Label>
            <div className="flex items-baseline gap-6">
              <Stat size="md" label="approve" value={pct(c.approval_rate)} />
              <Stat size="md" label="review" value={pct(c.review_rate)} />
              <Stat size="md" label="decline" value={pct(c.decline_rate)} />
            </div>
            <div className="mt-3"><Scope>Share of all {decisions.toLocaleString()} scored applicants. Average PD {pct(c.average_PD)}.</Scope></div>
          </div>

          <div>
            <Label>Modeled credit loss</Label>
            <Stat size="lg" label="expected credit loss" value={money(c.total_expected_credit_loss)} />
            <div className="mt-3"><Scope>On {money(c.total_approved_exposure)} approved exposure, at the current cutoffs. Assumption-driven, not realized.</Scope></div>
          </div>

          <div>
            <Label>Payments risk</Label>
            <Stat size="lg" label="expected fraud loss" value={money(c.total_expected_fraud_loss)} />
            <div className="mt-3"><Scope>Probability-weighted across all {transactions.toLocaleString()} transactions in the sample, before any action is taken.</Scope></div>
          </div>

          <div>
            <Label>Review load</Label>
            <Stat size="lg" label="manual review queue" value={num(c.manual_review_volume, 0)} />
            <div className="mt-3"><Scope>Transactions actionable within the fixed review capacity assumption.</Scope></div>
          </div>
        </div>

        <div className="mt-10 grid gap-x-10 gap-y-8 lg:grid-cols-[1fr_1fr]">
          <div>
            <Label right="what validation concluded">Model health</Label>
            <div className="mt-1 divide-y divide-line/50">
              {Object.entries(verdicts).map(([m, v]) => (
                <div key={m} className="flex items-center justify-between py-2">
                  <span className="text-[12.5px] text-ink">{m.replace(/_/g, " ")}</span>
                  <StateWord label={v} size="sm" />
                </div>
              ))}
            </div>
          </div>
          <div>
            <Label>Highest-loss segment</Label>
            <div className="mt-1 flex flex-wrap items-baseline gap-x-10 gap-y-4">
              <Stat size="md" label={String(hrs.dimension || "").replace(/_/g, " ")} value={hrs.segment} />
              <Stat size="md" label="loss rate" value={pct(hrs.expected_loss_rate)} />
              <Stat size="md" label="segment expected loss" value={money(hrs.total_expected_loss)} />
            </div>
            <div className="mt-4"><Scope>Ranked by modeled loss rate across underwriting segments.</Scope></div>
          </div>
        </div>
      </div>
    </Section>
  );
}
