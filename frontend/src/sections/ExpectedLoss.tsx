import type { Bundle } from "../lib/load";
import { Section, Panel, PanelHead, MetricRow } from "../components/ui";
import { BarFlat } from "../components/charts";
import { money, pct, num, TOK, stateColor } from "../lib/format";

const toArr = (o: Record<string, number>) => Object.entries(o || {}).map(([name, value]) => ({ name, value }));

export function ExpectedLoss({ b }: { b: Bundle }) {
  const e = b.expectedLossSummary;
  const st = b.stressLoss.scenarios;
  const a = e.assumptions ?? {};

  const elGrade = toArr(e.expected_loss_by_risk_grade).sort((x, y) => x.name.localeCompare(y.name));
  const elDecision = toArr(e.expected_loss_by_decision);
  const stressBars = ["base", "moderate", "severe"].map((k) => ({ name: k, value: st[k]?.expected_credit_loss }));

  return (
    <Section id="expected-loss" label="Expected loss engine" title="Risk scores → financial loss estimates"
      note="Assumption-driven estimates (LGD/EAD/severity labeled), not realized losses.">
      <Panel className="mb-3">
        <div className="px-4 py-3 num text-[15px] text-ink">
          Expected Loss = PD × LGD × EAD
          <span className="ml-3 text-[11px] text-ink-soft">
            LGD {pct(a.lgd_by_risk?.low, 0)}/{pct(a.lgd_by_risk?.standard, 0)}/{pct(a.lgd_by_risk?.high, 0)} by grade · utilization {pct(a.utilization, 0)} · fraud severity {pct(a.fraud_loss_severity, 0)}
        </span>
      </div>
      </Panel>

      <MetricRow items={[
        { label: "expected credit loss", value: money(e.total_expected_credit_loss) },
        { label: "expected fraud loss", value: money(e.total_expected_fraud_loss) },
        { label: "stablecoin exposure", value: money(e.total_stablecoin_risk_exposure) },
        { label: "approved exposure", value: money(e.total_approved_exposure) },
      ]} />

      <div className="mt-2 grid gap-2 lg:grid-cols-3">
        <Panel>
          <PanelHead left="EL by risk grade" />
          <div className="px-3 py-3"><BarFlat data={elGrade} x="name" y="value" money height={200} /></div>
        </Panel>
        <Panel>
          <PanelHead left="EL by decision" />
          <div className="px-3 py-3"><BarFlat data={elDecision} x="name" y="value" money height={200} colorFor={(r) => stateColor(r.name)} /></div>
        </Panel>
        <Panel>
          <PanelHead left="Credit EL: base vs stressed" />
          <div className="px-3 py-3"><BarFlat data={stressBars} x="name" y="value" money height={200} colorFor={(r) => r.name === "severe" ? TOK.fail : r.name === "moderate" ? TOK.review : TOK.accent} /></div>
        </Panel>
      </div>
      <p className="mt-2 num text-[11px] text-ink-soft">{a.note}</p>
    </Section>
  );
}
