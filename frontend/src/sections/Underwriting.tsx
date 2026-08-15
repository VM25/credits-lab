import { useState } from "react";
import type { Bundle } from "../lib/load";
import {
  Section, Block, Stat, Scope, Label, Chip, StateWord, Tabs, TabPanel, RowButton, TableHead, KV,
} from "../components/ui";
import { BarFlat } from "../components/charts";
import { pct, money, moneyFull, num, TOK, stateColor } from "../lib/format";

const toArr = (o: Record<string, number>) => Object.entries(o || {}).map(([name, value]) => ({ name, value }));
const readable = (s: string) => (s || "").replace(/_/g, " ");

const COLS = "1fr 0.6fr 0.5fr 0.8fr";

export function Underwriting({ b }: { b: Bundle }) {
  const p = b.underwritingPolicy;
  const rows: any[] = b.underwritingDecisions.rows ?? [];
  const view = rows.slice(0, 40);
  const [sel, setSel] = useState(0);
  const r = view[sel];

  const pdHist = (p.champion_vs_challenger?.champion?.pd_distribution ?? []).map((d: any) => ({
    bin: d.bin_left?.toFixed ? d.bin_left.toFixed(2) : d.bin_left, count: d.count,
  }));
  const grades = toArr(p.risk_grade_distribution).sort((a, b) => a.name.localeCompare(b.name));
  const mix = toArr(p.approval_mix);
  const elGrade = toArr(p.expected_loss_by_risk_grade).sort((a, b) => a.name.localeCompare(b.name));
  const reasons = toArr(p.top_decline_reasons).sort((a, b) => b.value - a.value).slice(0, 7);
  const topGrade = elGrade.length ? elGrade.reduce((m, x) => (x.value > m.value ? x : m), elGrade[0]) : null;

  return (
    <Section
      id="underwriting"
      tone="panel"
      title="Who should get credit, and what it costs to be wrong."
      lede="A calibrated logistic scorecard estimates each applicant's probability of default, then policy turns that number into an action, a limit and an explanation. Pick an applicant to follow one decision end to end."
    >
      <Tabs tabs={[{ value: "decision", label: "Decision view" }, { value: "portfolio", label: "Portfolio analysis" }]}>
        <TabPanel value="decision">
          <div className="grid gap-6 lg:grid-cols-[380px_1fr] lg:gap-10">
            {/* master */}
            <div>
              <Label right={`${view.length} of ${num(b.underwritingDecisions.row_count_total, 0)}`}>Applicants</Label>
              <Block tone="flat">
                <TableHead cols={COLS} headers={["applicant", "PD", "grade", "action"]} />
                <div className="max-h-[520px] overflow-auto">
                  {view.map((row, i) => (
                    <RowButton key={row.applicant_id} selected={i === sel} onClick={() => setSel(i)} cols={COLS}>
                      <div className="num px-3 py-2 text-[12px] text-ink">{row.applicant_id}</div>
                      <div className="num px-3 py-2 text-[12px] text-ink">{pct(row.PD)}</div>
                      <div className="num px-3 py-2 text-[12px] text-ink">{row.risk_grade}</div>
                      <div className="px-3 py-2"><Chip label={row.decision} size="sm" /></div>
                    </RowButton>
                  ))}
                </div>
              </Block>
              <div className="mt-3"><Scope>A labeled display sample of the decision file. Portfolio figures cover the full scored sample.</Scope></div>
            </div>

            {/* detail - dominant */}
            {r && (
              <Block tone="deep" className="px-7 py-7">
                <div className="flex flex-wrap items-start justify-between gap-6">
                  <div>
                    <div className="text-[11.5px] text-ink-soft">applicant</div>
                    <div className="num text-[19px] font-medium text-ink">{r.applicant_id}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-[11.5px] text-ink-soft">action</div>
                    <StateWord label={r.decision} size="lg" />
                  </div>
                </div>

                <div className="mt-8 grid gap-8 sm:grid-cols-3">
                  <Stat size="xl" label="probability of default" value={pct(r.PD)} />
                  <Stat size="lg" label="risk grade" value={r.risk_grade} />
                  <Stat size="lg" label="expected loss" value={moneyFull(r.expected_loss)} color={stateColor(r.decision)} />
                </div>

                <div className="mt-9 grid gap-x-12 gap-y-1 sm:grid-cols-2">
                  <div className="divide-y divide-line/50">
                    <KV k="recommended credit limit" v={money(r.recommended_credit_limit)} />
                    <KV k="exposure at default (EAD)" v={money(r.EAD)} />
                    <KV k="loss given default (LGD)" v={num(r.LGD, 2)} />
                  </div>
                  <div className="divide-y divide-line/50">
                    <KV k="expected loss rate" v={pct(r.expected_loss_rate)} />
                    <KV k="scoring model" v={<span className="text-[12px]">{readable(r.model_used)}</span>} />
                    <KV k="model verdict" v={<StateWord label="Monitor" size="sm" />} mono={false} />
                  </div>
                </div>

                <div className="mt-8">
                  <div className="text-[11.5px] text-ink-soft">reason codes</div>
                  <ul className="mt-2 space-y-1">
                    {[r.top_reason_1, r.top_reason_2, r.top_reason_3].filter(Boolean).map((c: string) => (
                      <li key={c} className="text-[13px] leading-snug text-ink">{readable(c)}</li>
                    ))}
                  </ul>
                </div>
              </Block>
            )}
          </div>
        </TabPanel>

        <TabPanel value="portfolio">
          <div className="grid gap-10 lg:grid-cols-2">
            <div>
              <Label right="calibrated champion scorecard">Where the sample's risk sits</Label>
              <Block tone="flat" className="px-3 py-4">
                <BarFlat data={pdHist} x="bin" y="count" height={260} />
              </Block>
              <p className="mt-3 max-w-[60ch] text-[12.5px] leading-relaxed text-ink-soft">
                Most applicants score between 10% and 40% default probability, so this sample has no
                large low-risk tail to approve cheaply. That is why the approval rate is modest.
              </p>
            </div>
            <div>
              <Label right="assumption-driven">Loss concentrates in the weakest grades</Label>
              <Block tone="flat" className="px-3 py-4">
                <BarFlat data={elGrade} x="name" y="value" money height={260} />
              </Block>
              <p className="mt-3 max-w-[60ch] text-[12.5px] leading-relaxed text-ink-soft">
                {topGrade
                  ? `Grade ${topGrade.name} alone carries ${money(topGrade.value)} of modeled expected loss, the largest single grade contribution.`
                  : "Modeled expected loss by risk grade."}
              </p>
            </div>
          </div>

          <div className="mt-12 grid gap-10 lg:grid-cols-3">
            <div>
              <Label>Risk grade mix</Label>
              <Block tone="flat" className="px-3 py-4"><BarFlat data={grades} x="name" y="value" height={200} /></Block>
            </div>
            <div>
              <Label>Decision mix</Label>
              <Block tone="flat" className="px-3 py-4">
                <BarFlat data={mix} x="name" y="value" height={200} colorFor={(row) => stateColor(row.name)} />
              </Block>
            </div>
            <div>
              <Label>Why applicants are declined</Label>
              <Block tone="flat" className="px-3 py-4">
                <BarFlat data={reasons} x="name" y="value" height={200} colorFor={() => TOK.fail} />
              </Block>
            </div>
          </div>
          <div className="mt-5"><Scope>Aggregates cover all {num(b.underwritingDecisions.row_count_total, 0)} scored applicants at the current operating point.</Scope></div>
        </TabPanel>
      </Tabs>
    </Section>
  );
}
