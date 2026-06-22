import type { Bundle } from "../lib/load";
import { Section, Panel, PanelHead, MetricRow, Chip } from "../components/ui";
import { BarFlat } from "../components/charts";
import { money, num, stateColor } from "../lib/format";

const toArr = (o: Record<string, number>) => Object.entries(o || {}).map(([name, value]) => ({ name, value }));

export function StablecoinMonitor({ b }: { b: Bundle }) {
  const s = b.stablecoinAlerts;
  const rows: any[] = s.rows ?? [];
  const view = rows.slice(0, 30);
  const mix = toArr(s.action_mix);
  const lb: any[] = s.wallet_risk_leaderboard ?? [];

  return (
    <Section id="stablecoin" label="Stablecoin risk monitor" title="Wallet-risk scoring with AML-style risk indicators"
      note={s.data_note || "Synthetic stablecoin transaction sample. AML-style risk indicators only."}>
      <MetricRow items={[
        { label: "transactions", value: num(s.row_count_total, 0) },
        { label: "high-risk wallets", value: num(s.high_risk_wallet_count, 0) },
        { label: "high-risk exposure", value: money(s.risk_exposure_by_action?.high_risk) },
        { label: "review exposure", value: money(s.risk_exposure_by_action?.review) },
      ]} />

      <div className="mt-2 grid gap-2 lg:grid-cols-2">
        <Panel>
          <PanelHead left="Risk action mix" />
          <div className="px-3 py-3"><BarFlat data={mix} x="name" y="value" colorFor={(r) => stateColor(r.name)} /></div>
        </Panel>
        <Panel>
          <PanelHead left="Wallet risk leaderboard" right="by total exposure" />
          <div className="max-h-[260px] overflow-auto">
            <div className="grid grid-cols-[1.2fr_1fr_0.7fr_0.6fr] reg border-b border-line bg-panel-2 text-[10px] text-ink-soft">
              {["wallet", "exposure", "max score", "tx"].map((h) => <div key={h} className="px-3 py-1.5">{h}</div>)}
            </div>
            {lb.map((w) => (
              <div key={w.wallet_id} className="grid grid-cols-[1.2fr_1fr_0.7fr_0.6fr] items-center border-b border-line">
                <div className="num px-3 py-1.5 text-[12px] text-ink">{w.wallet_id}</div>
                <div className="num px-3 py-1.5 text-[12px] text-ink">{money(w.total_exposure)}</div>
                <div className="num px-3 py-1.5 text-[12px] text-ink">{num(w.max_score, 2)}</div>
                <div className="num px-3 py-1.5 text-[12px] text-ink">{num(w.n_tx, 0)}</div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Panel className="mt-2">
        <PanelHead left="Wallet transactions" right={`sample of ${num(s.row_count_total, 0)}`} />
        <div className="grid grid-cols-[1fr_1fr_0.9fr_0.7fr_0.9fr_1.4fr] reg border-b border-line bg-panel-2 text-[10px] text-ink-soft">
          {["wallet", "counterparty", "amount", "score", "action", "top drivers"].map((h) => <div key={h} className="px-3 py-2">{h}</div>)}
        </div>
        <div className="max-h-[360px] overflow-auto">
          {view.map((r, i) => (
            <div key={i} className="grid grid-cols-[1fr_1fr_0.9fr_0.7fr_0.9fr_1.4fr] items-center border-b border-line">
              <div className="num px-3 py-2 text-[12px] text-ink">{r.wallet_id}</div>
              <div className="num px-3 py-2 text-[12px] text-ink">{r.counterparty_wallet_id}</div>
              <div className="num px-3 py-2 text-[12px] text-ink">{money(r.amount_usd)}</div>
              <div className="num px-3 py-2 text-[12px] text-ink">{num(r.stablecoin_risk_score, 2)}</div>
              <div className="px-3 py-2"><Chip label={r.stablecoin_risk_action} /></div>
              <div className="px-3 py-2 text-[11px] text-ink-soft">
                {[r.top_reason_1, r.top_reason_2, r.top_reason_3].filter(Boolean).map((x: string) => x.replace(/_/g, " ")).join(" · ")}
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </Section>
  );
}
