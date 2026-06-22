import type { Bundle } from "../lib/load";
import { Section, Panel, PanelHead } from "../components/ui";
import { BarFlat } from "../components/charts";
import { money, num, TOK } from "../lib/format";

export function StressTesting({ b }: { b: Bundle }) {
  const sc = b.stressLoss.scenarios;
  const order = ["base", "moderate", "severe"];
  const totalBars = order.map((k) => ({ name: k, value: sc[k]?.total_expected_loss }));

  return (
    <Section id="stress" label="Stress testing" title="Loss sensitivity under worse conditions"
      note="Simulated stress via PD/LGD/fraud multipliers (PD capped at 1.0). Macro variables inform overlays only; no individual-default causality is claimed.">
      <div className="grid gap-2 lg:grid-cols-[1fr_1.3fr]">
        <Panel>
          <PanelHead left="Total expected loss by scenario" />
          <div className="px-3 py-3">
            <BarFlat data={totalBars} x="name" y="value" money height={220}
              colorFor={(r) => r.name === "severe" ? TOK.fail : r.name === "moderate" ? TOK.review : TOK.accent} />
          </div>
        </Panel>
        <Panel>
          <PanelHead left="Scenario components" />
          <div className="grid grid-cols-[1fr_0.9fr_0.9fr_0.9fr_0.9fr] reg border-b border-line bg-panel-2 text-[10px] text-ink-soft">
            {["scenario", "credit", "fraud", "stablecoin", "total"].map((h) => <div key={h} className="px-3 py-2">{h}</div>)}
          </div>
          {order.map((k) => (
            <div key={k} className="grid grid-cols-[1fr_0.9fr_0.9fr_0.9fr_0.9fr] border-b border-line">
              <div className="px-3 py-2 text-[12px] text-ink">
                {k}
                <span className="num ml-2 text-[10px] text-ink-soft">PD×{num(sc[k]?.pd_multiplier, 2)} LGD×{num(sc[k]?.lgd_multiplier, 2)} fraud×{num(sc[k]?.fraud_loss_multiplier, 2)}</span>
              </div>
              <div className="num px-3 py-2 text-[12px] text-ink">{money(sc[k]?.expected_credit_loss)}</div>
              <div className="num px-3 py-2 text-[12px] text-ink">{money(sc[k]?.expected_fraud_loss)}</div>
              <div className="num px-3 py-2 text-[12px] text-ink">{money(sc[k]?.stablecoin_risk_exposure)}</div>
              <div className="num px-3 py-2 text-[12px] font-medium text-ink">{money(sc[k]?.total_expected_loss)}</div>
            </div>
          ))}
        </Panel>
      </div>
    </Section>
  );
}
