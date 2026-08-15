import { useState } from "react";
import type { Bundle } from "../lib/load";
import {
  Section, Block, Stat, Scope, Label, Chip, StateWord, Tabs, TabPanel, RowButton, TableHead, KV, Note,
} from "../components/ui";
import { Term } from "../components/guide";
import { BarFlat, LineFlat } from "../components/charts";
import { pct, money, moneyFull, num, TOK, stateColor } from "../lib/format";

const toArr = (o: Record<string, number>) => Object.entries(o || {}).map(([name, value]) => ({ name, value }));
const readable = (s: string) => (s || "").replace(/_/g, " ");

const TX_COLS = "0.9fr 0.7fr 0.6fr 0.8fr";
const SC_COLS = "1fr 0.7fr 0.9fr";

export function FraudPayments({ b }: { b: Bundle }) {
  const f = b.fraudPolicy;
  const sup = b.validationSummary?.fraud_supervised_metrics ?? {};
  const rows: any[] = b.fraudAlerts.rows ?? [];
  const view = rows.slice(0, 40);
  const [sel, setSel] = useState(0);
  const t = view[sel];
  const w = f.composite_weights ?? {};

  const mix = toArr(f.action_mix);
  const tradeoff = (f.threshold_tradeoff ?? []).map((d: any) => ({
    threshold: Number(d.threshold).toFixed(2), captured: d.fraud_captured, fp: d.false_positives,
  }));
  const prCurve = (b.validationSummary?.fraud_pr_curve ?? []).map((d: any) => ({
    recall: Number(d.recall).toFixed(2), precision: d.precision,
  }));

  // stablecoin extension
  const s = b.stablecoinAlerts;
  const sMix = toArr(s.action_mix);
  const lb: any[] = s.wallet_risk_leaderboard ?? [];

  return (
    <Section
      id="fraud"
      title="Which payments look wrong, and what to do about them."
      lede="Every transaction is scored by rules, a supervised model and an anomaly detector, then routed to approve, step-up, review or block. Fraud is roughly 0.6% of the sample, so ranking quality matters far more than accuracy."
    >
      <Tabs
        tabs={[
          { value: "investigate", label: "Investigation" },
          { value: "performance", label: "Model performance" },
          { value: "stablecoin", label: "Stablecoin extension" },
        ]}
      >
        {/* ------------------------------------------------ investigation */}
        <TabPanel value="investigate">
          <div className="grid gap-6 lg:grid-cols-[400px_1fr] lg:gap-10">
            <div>
              <Label right={`${view.length} of ${num(b.fraudAlerts.row_count_total, 0)}`}>Transaction queue</Label>
              <Block tone="flat">
                <TableHead cols={TX_COLS} headers={["transaction", "amount", "score", "action"]} />
                <div className="max-h-[520px] overflow-auto">
                  {view.map((row, i) => (
                    <RowButton key={row.transaction_id} selected={i === sel} onClick={() => setSel(i)} cols={TX_COLS}>
                      <div className="num px-3 py-2 text-[12px] text-ink">{row.transaction_id}</div>
                      <div className="num px-3 py-2 text-[12px] text-ink">{moneyFull(row.amount)}</div>
                      <div className="num px-3 py-2 text-[12px] text-ink">{num(row.fraud_score, 2)}</div>
                      <div className="px-3 py-2"><Chip label={row.payment_action} size="sm" /></div>
                    </RowButton>
                  ))}
                </div>
              </Block>
              <div className="mt-3"><Scope>A labeled display sample of the alert file, in file order.</Scope></div>
            </div>

            {t && (
              <Block tone="deep" className="px-7 py-7">
                <div className="flex flex-wrap items-start justify-between gap-6">
                  <div>
                    <div className="text-[11.5px] text-ink-soft">transaction</div>
                    <div className="num text-[19px] font-medium text-ink">{t.transaction_id}</div>
                    <div className="num mt-1 text-[11.5px] text-ink-soft">{t.transaction_time} · account {t.account_id}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-[11.5px] text-ink-soft">payment action</div>
                    <StateWord label={t.payment_action} size="lg" />
                  </div>
                </div>

                <div className="mt-8 grid gap-8 sm:grid-cols-3">
                  <Stat size="xl" label="amount" value={moneyFull(t.amount)} />
                  <Stat size="lg" label="composite fraud score" value={num(t.fraud_score, 3)} />
                  <Stat size="lg" label="expected fraud loss" value={moneyFull(t.expected_fraud_loss)} color={stateColor(t.payment_action)} />
                </div>

                <div className="mt-9 grid gap-x-12 gap-y-1 sm:grid-cols-2">
                  <div className="divide-y divide-line/50">
                    <KV k="model fraud probability" v={num(t.fraud_probability, 4)} />
                    <KV k="anomaly score" v={num(t.anomaly_score, 4)} />
                    <KV k="manual review priority" v={t.manual_review_priority ?? "not queued"} />
                  </div>
                  <div className="divide-y divide-line/50">
                    <KV k="score weight: model" v={num(w.fraud_probability, 2)} />
                    <KV k="score weight: anomaly" v={num(w.anomaly_score, 2)} />
                    <KV k="score weight: rules" v={num(w.rule_score, 2)} />
                  </div>
                </div>

                <div className="mt-8">
                  <div className="text-[11.5px] text-ink-soft">what triggered</div>
                  <ul className="mt-2 space-y-1">
                    {[t.top_reason_1, t.top_reason_2, t.top_reason_3].filter(Boolean).map((c: string) => (
                      <li key={c} className="text-[13px] leading-snug text-ink">{readable(c.toLowerCase())}</li>
                    ))}
                    {![t.top_reason_1, t.top_reason_2, t.top_reason_3].filter(Boolean).length && (
                      <li className="text-[13px] text-ink-soft">no rule triggered; routed on score alone</li>
                    )}
                  </ul>
                </div>
              </Block>
            )}
          </div>

          <div className="mt-10">
            <Label>Where the queue goes</Label>
            <div className="grid gap-10 lg:grid-cols-[1fr_1.2fr]">
              <Block tone="flat" className="px-3 py-4">
                <BarFlat data={mix} x="name" y="value" height={210} colorFor={(row) => stateColor(row.name)} />
              </Block>
              <div className="flex flex-col justify-center gap-6">
                <div className="flex flex-wrap gap-x-12 gap-y-6">
                  <Stat size="lg" label="manual review queue" value={num(f.manual_review_volume, 0)}
                    sub="capped by the review-capacity assumption, so not every high score is queued" />
                  <Stat size="lg" label="fraud caught at the review boundary" value={pct(f.fraud_capture_rate)}
                    sub="share of confirmed frauds routed to review or block" />
                </div>
              </div>
            </div>
          </div>
        </TabPanel>

        {/* ------------------------------------------------- performance */}
        <TabPanel value="performance">
          <div className="grid gap-x-12 gap-y-10 lg:grid-cols-2">
            <div>
              <Label>Two <Term k="PR-AUC">PR-AUC</Term>s, two different things being scored</Label>
              <Block tone="deep" className="px-6 py-6">
                <div className="grid gap-8 sm:grid-cols-2">
                  <Stat size="lg" label="supervised model only" value={num(sup.pr_auc, 3)}
                    sub="the logistic fraud model's own probability, held-out test split" />
                  <Stat size="lg" label="composite routing score" value={num(f.pr_auc, 3)}
                    sub="the blended score that actually routes payments, same test split" />
                </div>
                <p className="mt-6 max-w-[62ch] text-[12.5px] leading-relaxed text-ink-soft">
                  Both are measured on the same held-out transactions against the same labels. They
                  differ because they score different quantities: the routing score is{" "}
                  <span className="num">{num(w.fraud_probability, 2)}</span> model probability +{" "}
                  <span className="num">{num(w.anomaly_score, 2)}</span> anomaly +{" "}
                  <span className="num">{num(w.rule_score, 2)}</span> rules. Blending in the
                  unsupervised and rule components costs ranking quality against the fraud label,
                  which is the honest cost of keeping rule coverage in the decision path.
                </p>
              </Block>
            </div>

            <div>
              <Label right="held-out test split">At the review boundary</Label>
              <div className="grid gap-8 sm:grid-cols-2">
                <Stat size="lg" label="fraud capture" value={pct(f.fraud_capture_rate)} sub="recall on confirmed frauds" />
                <Stat size="lg" label="false positive rate" value={pct(f.false_positive_rate, 2)} sub="legitimate payments flagged, composite routing score" />
                <Stat size="md" label="precision" value={num(f.precision, 3)} sub="composite routing score" />
                <Stat size="md" label="ROC-AUC" value={num(f.roc_auc, 3)} sub="composite routing score" />
              </div>
              <div className="mt-6">
                <Note>
                  Accuracy is not reported. With fraud at roughly 0.6% of transactions, approving
                  everything would score above 99% while catching nothing, so precision and recall
                  on the rare class are the only informative measures.
                </Note>
              </div>
            </div>
          </div>

          <div className="mt-12 grid gap-10 lg:grid-cols-2">
            <div>
              <Label right="composite routing score">Raising the threshold trades catches for noise</Label>
              <Block tone="flat" className="px-3 py-4">
                <LineFlat data={tradeoff} x="threshold" height={250}
                  lines={[{ key: "captured", color: TOK.pass }, { key: "fp", color: TOK.fail }]} />
              </Block>
              <p className="mt-3 max-w-[58ch] text-[12.5px] leading-relaxed text-ink-soft">
                False positives fall away far faster than captured fraud as the threshold rises,
                which is what makes a review band worth operating.
              </p>
            </div>
            <div>
              <Label right="supervised model only">Precision against recall</Label>
              <Block tone="flat" className="px-3 py-4">
                <LineFlat data={prCurve} x="recall" height={250} lines={[{ key: "precision", color: TOK.accent }]} />
              </Block>
              <p className="mt-3 max-w-[58ch] text-[12.5px] leading-relaxed text-ink-soft">
                Precision holds up across much of the recall range before collapsing, the shape that
                the {num(sup.pr_auc, 3)} PR-AUC summarizes.
              </p>
            </div>
          </div>

          <div className="mt-10">
            <Label>Fraud loss, and what each figure covers</Label>
            <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
              <Stat size="lg" label="expected fraud loss" value={money(b.commandCenter.total_expected_fraud_loss)}
                sub="probability-weighted across all 80,000 transactions, before any action" />
              <Stat size="lg" label="loss avoided by flagging" value={moneyFull(f.expected_fraud_loss_avoided)}
                sub="modeled loss on confirmed frauds that review or block caught, test split only" />
              <Stat size="lg" label="false positive rate" value={pct(f.false_positive_rate, 2)}
                sub="the cost side: good payments interrupted" />
            </div>
            <div className="mt-4">
              <Scope>
                These two dollar figures are not comparable totals. The first spreads a small
                probability across every transaction in the whole sample; the second counts only
                confirmed fraud in the held-out split that the policy actually stopped.
              </Scope>
            </div>
          </div>
        </TabPanel>

        {/* -------------------------------------------------- stablecoin */}
        <TabPanel value="stablecoin">
          <div className="max-w-[80ch]">
            <Note tone="caveat">
              Secondary extension. The stablecoin data is entirely synthetic, including its risk
              label. These are AML-style risk indicators used to demonstrate transaction-monitoring
              logic, with no compliance claim, and no trading, DeFi, yield or token-price modeling.
            </Note>
          </div>

          <div className="mt-8 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            <Stat size="lg" label="transactions" value={num(s.row_count_total, 0)} sub="synthetic sample" />
            <Stat size="lg" label="high-risk wallets" value={num(s.high_risk_wallet_count, 0)} />
            <Stat size="lg" label="risk exposure" value={money(b.commandCenter.stablecoin_risk_exposure)} sub="exposure-weighted across the synthetic sample" />
            <Stat size="lg" label="discrimination AUC" value={num(b.validationSummary?.stablecoin?.discrimination_auc_vs_synthetic_label, 3)}
              sub="against the synthetic label the score was not trained on" />
          </div>

          <div className="mt-10 grid gap-10 lg:grid-cols-[1fr_1.1fr]">
            <div>
              <Label>Wallet action mix</Label>
              <Block tone="flat" className="px-3 py-4">
                <BarFlat data={sMix} x="name" y="value" height={210} colorFor={(row) => stateColor(row.name)} />
              </Block>
            </div>
            <div>
              <Label right="by risk score">Highest-risk wallets</Label>
              <Block tone="flat">
                <TableHead cols={SC_COLS} headers={["wallet", "risk score", "exposure"]} />
                <div className="max-h-[260px] overflow-auto">
                  {lb.slice(0, 10).map((row: any) => (
                    <div key={row.wallet_id} className="grid border-b border-line/50 text-[12px]" style={{ gridTemplateColumns: SC_COLS }}>
                      <div className="num px-3 py-2 text-ink">{row.wallet_id}</div>
                      <div className="num px-3 py-2 text-ink">{num(row.stablecoin_risk_score ?? row.risk_score, 3)}</div>
                      <div className="num px-3 py-2 text-ink">{money(row.risk_exposure_score ?? row.total_exposure)}</div>
                    </div>
                  ))}
                </div>
              </Block>
            </div>
          </div>
        </TabPanel>
      </Tabs>
    </Section>
  );
}
