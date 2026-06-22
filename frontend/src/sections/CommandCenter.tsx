import type { Bundle } from "../lib/load";
import { Section, MetricRow, Panel, PanelHead, Chip } from "../components/ui";
import { pct, money, num } from "../lib/format";

export function CommandCenter({ b }: { b: Bundle }) {
  const c = b.commandCenter;
  const verdicts: Record<string, string> = c.model_verdict_summary?.by_model ?? {};
  const hrs = c.highest_risk_segment ?? {};
  return (
    <Section id="command-center" label="Risk command center" title="Portfolio-level risk state"
      note="Every figure traces to data/outputs. Modeled estimates, not realized losses.">
      <MetricRow items={[
        { label: "approval rate", value: pct(c.approval_rate) },
        { label: "review rate", value: pct(c.review_rate) },
        { label: "decline rate", value: pct(c.decline_rate) },
        { label: "average PD", value: pct(c.average_PD) },
      ]} />
      <div className="mt-2">
        <MetricRow items={[
          { label: "approved exposure", value: money(c.total_approved_exposure) },
          { label: "expected credit loss", value: money(c.total_expected_credit_loss) },
          { label: "expected fraud loss", value: money(c.total_expected_fraud_loss) },
          { label: "stablecoin exposure", value: money(c.stablecoin_risk_exposure) },
        ]} />
      </div>

      <div className="mt-4 grid gap-2 md:grid-cols-2">
        <Panel>
          <PanelHead left="Model verdict summary" />
          <div className="divide-y divide-line">
            {Object.entries(verdicts).map(([m, v]) => (
              <div key={m} className="flex items-center justify-between px-4 py-2">
                <span className="num text-[12px] text-ink">{m.replace(/_/g, " ")}</span>
                <Chip label={v} />
              </div>
            ))}
          </div>
        </Panel>
        <Panel>
          <PanelHead left="Highest-risk segment" right="manual review" />
          <div className="px-4 py-3">
            <div className="text-[13px] text-ink">
              {hrs.dimension?.replace(/_/g, " ")} = <span className="num font-medium">{hrs.segment}</span>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <div>
                <div className="reg text-[10px] text-ink-soft">loss rate</div>
                <div className="num text-[20px] text-ink">{pct(hrs.expected_loss_rate)}</div>
              </div>
              <div>
                <div className="reg text-[10px] text-ink-soft">segment EL</div>
                <div className="num text-[20px] text-ink">{money(hrs.total_expected_loss)}</div>
              </div>
            </div>
            <div className="mt-3 reg text-[10px] text-ink-soft">manual review queue</div>
            <div className="num text-[18px] text-ink">{num(c.manual_review_volume, 0)} transactions</div>
          </div>
        </Panel>
      </div>
    </Section>
  );
}
