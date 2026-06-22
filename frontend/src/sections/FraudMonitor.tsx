import { useState } from "react";
import type { Bundle } from "../lib/load";
import { Section, Panel, PanelHead, MetricRow, Chip } from "../components/ui";
import { BarFlat, LineFlat } from "../components/charts";
import { pct, money, num, TOK, stateColor } from "../lib/format";

const toArr = (o: Record<string, number>) => Object.entries(o || {}).map(([name, value]) => ({ name, value }));

export function FraudMonitor({ b }: { b: Bundle }) {
  const f = b.fraudPolicy;
  const rows: any[] = b.fraudAlerts.rows ?? [];
  const [sel, setSel] = useState<number | null>(null);
  const view = rows.slice(0, 40);

  const mix = toArr(f.action_mix);
  const tradeoff = (f.threshold_tradeoff ?? []).map((d: any) => ({
    threshold: Number(d.threshold).toFixed(2), captured: d.fraud_captured, fp: d.false_positives,
  }));

  return (
    <Section id="fraud" label="Fraud & payments monitor" title="Transaction risk → payment action"
      note="Real Kaggle fraud labels (heavily imbalanced). PR-AUC is the headline metric; accuracy is not used. Manual review is capacity-bounded.">
      <MetricRow items={[
        { label: "PR-AUC (headline)", value: num(f.pr_auc, 3) },
        { label: "precision", value: num(f.precision, 3) },
        { label: "recall", value: num(f.recall, 3) },
        { label: "fraud capture", value: num(f.fraud_capture_rate, 3) },
      ]} />
      <div className="mt-2">
        <MetricRow items={[
          { label: "false positive rate", value: pct(f.false_positive_rate, 2) },
          { label: "false negative rate", value: pct(f.false_negative_rate, 2) },
          { label: "manual review", value: `${num(f.manual_review_volume, 0)} / ${num(f.manual_review_capacity, 0)}` },
          { label: "fraud loss avoided", value: money(f.expected_fraud_loss_avoided) },
        ]} />
      </div>

      <div className="mt-2 grid gap-2 lg:grid-cols-2">
        <Panel>
          <PanelHead left="Payment action mix" />
          <div className="px-3 py-3"><BarFlat data={mix} x="name" y="value" colorFor={(r) => stateColor(r.name)} /></div>
        </Panel>
        <Panel>
          <PanelHead left="Threshold tradeoff" right="captured vs false positives" />
          <div className="px-3 py-3">
            <LineFlat data={tradeoff} x="threshold" lines={[{ key: "captured", color: TOK.pass }, { key: "fp", color: TOK.fail }]} />
          </div>
        </Panel>
      </div>

      <Panel className="mt-2">
        <PanelHead left="Transaction alerts" right={`sample of ${num(b.fraudAlerts.row_count_total, 0)} · select for drivers`} />
        <div className="grid grid-cols-[1fr_0.8fr_0.7fr_0.7fr_1fr_1fr] reg border-b border-line bg-panel-2 text-[10px] text-ink-soft">
          {["transaction", "amount", "fraud", "anomaly", "action", "exp. loss"].map((h) => <div key={h} className="px-3 py-2">{h}</div>)}
        </div>
        <div className="max-h-[380px] overflow-auto">
          {view.map((r, i) => (
            <div key={r.transaction_id}>
              <button onClick={() => setSel(sel === i ? null : i)}
                className="grid w-full grid-cols-[1fr_0.8fr_0.7fr_0.7fr_1fr_1fr] items-center border-b border-line text-left hover:bg-panel-2"
                style={sel === i ? { background: "#bcc9bb" } : undefined}>
                <div className="num px-3 py-2 text-[12px] text-ink">{r.transaction_id}</div>
                <div className="num px-3 py-2 text-[12px] text-ink">{money(r.amount)}</div>
                <div className="num px-3 py-2 text-[12px] text-ink">{num(r.fraud_score, 2)}</div>
                <div className="num px-3 py-2 text-[12px] text-ink">{num(r.anomaly_score, 2)}</div>
                <div className="px-3 py-2"><Chip label={r.payment_action} /></div>
                <div className="num px-3 py-2 text-[12px] text-ink">{money(r.expected_fraud_loss)}</div>
              </button>
              {sel === i && (
                <div className="border-b border-line bg-bg px-4 py-2">
                  <span className="reg text-[10px] text-ink-soft">drivers · review priority {r.manual_review_priority ?? "—"}: </span>
                  {[r.top_reason_1, r.top_reason_2, r.top_reason_3].filter(Boolean).map((rc: string, k: number) => (
                    <span key={k} className="num mr-2 text-[11px] text-ink">{rc.replace(/_/g, " ")}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </Panel>
    </Section>
  );
}
