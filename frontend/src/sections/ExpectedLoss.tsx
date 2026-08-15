import type { Bundle } from "../lib/load";
import { Section, Block, Stat, Scope, Label, Tabs, TabPanel, Note, KV } from "../components/ui";
import { Term } from "../components/guide";
import { BarFlat } from "../components/charts";
import { money, moneyFull, pct, num, stateColor } from "../lib/format";

const toArr = (o: Record<string, number>) => Object.entries(o || {}).map(([name, value]) => ({ name, value }));

export function ExpectedLoss({ b }: { b: Bundle }) {
  const e = b.expectedLossSummary;
  const a = e.assumptions ?? {};
  const rows: any[] = b.underwritingDecisions.rows ?? [];
  const r = rows[0];

  const elGrade = toArr(e.expected_loss_by_risk_grade).sort((x, y) => x.name.localeCompare(y.name));
  const elDecision = toArr(e.expected_loss_by_decision);

  return (
    <Section
      id="expected-loss"
      title="What a probability is worth in dollars."
      lede="A score only becomes a business decision once it is priced. Expected loss multiplies the chance of default by how much is at risk and how much of it would be lost, which is why two applicants with the same PD can carry very different exposure."
    >
      <Tabs tabs={[{ value: "one", label: "One decision" }, { value: "portfolio", label: "Portfolio loss" }]}>
        <TabPanel value="one">
          {r && (
            <Block tone="deep" className="px-7 py-8">
              <div className="text-[11.5px] text-ink-soft">applicant <span className="num text-ink">{r.applicant_id}</span></div>

              <div className="mt-6 flex flex-wrap items-end gap-x-5 gap-y-6">
                <div>
                  <div className="text-[11.5px] text-ink-soft"><Term k="PD">probability of default</Term></div>
                  <div className="num text-[34px] font-medium leading-none text-ink">{pct(r.PD)}</div>
                </div>
                <span className="pb-2 text-[22px] text-ink-soft">×</span>
                <div>
                  <div className="text-[11.5px] text-ink-soft"><Term k="LGD">loss given default</Term></div>
                  <div className="num text-[34px] font-medium leading-none text-ink">{num(r.LGD, 2)}</div>
                </div>
                <span className="pb-2 text-[22px] text-ink-soft">×</span>
                <div>
                  <div className="text-[11.5px] text-ink-soft"><Term k="EAD">exposure at default</Term></div>
                  <div className="num text-[34px] font-medium leading-none text-ink">{moneyFull(r.EAD)}</div>
                </div>
                <span className="pb-2 text-[22px] text-ink-soft">=</span>
                <div>
                  <div className="text-[11.5px] text-ink-soft">expected loss</div>
                  <div className="num text-[34px] font-medium leading-none" style={{ color: stateColor(r.decision) }}>
                    {moneyFull(r.expected_loss)}
                  </div>
                </div>
              </div>

              <p className="mt-8 max-w-[70ch] text-[13px] leading-relaxed text-ink-soft">
                Only the first term is modeled. Loss given default and exposure at default are
                assumptions applied by grade and utilization, so the dollar figure inherits every
                one of them. That is the honest limit of an expected-loss number built on a public
                benchmark rather than an active lending portfolio.
              </p>

              <div className="mt-8 grid gap-x-12 gap-y-1 sm:grid-cols-2">
                <div className="divide-y divide-line/50">
                  <KV k="LGD by grade (low / standard / high)" v={`${pct(a.lgd_by_risk?.low, 0)} / ${pct(a.lgd_by_risk?.standard, 0)} / ${pct(a.lgd_by_risk?.high, 0)}`} />
                  <KV k="assumed utilization" v={pct(a.utilization, 0)} />
                </div>
                <div className="divide-y divide-line/50">
                  <KV k="fraud loss severity" v={pct(a.fraud_loss_severity, 0)} />
                  <KV k="expected loss rate on this account" v={pct(r.expected_loss_rate)} />
                </div>
              </div>
            </Block>
          )}
        </TabPanel>

        <TabPanel value="portfolio">
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            <Stat size="lg" label="expected credit loss" value={money(e.total_expected_credit_loss)}
              sub={`every scored applicant; ${money(e.expected_loss_by_decision?.approve)} of it on approved accounts`} />
            <Stat size="lg" label="expected fraud loss" value={money(e.total_expected_fraud_loss)}
              sub="across all scored transactions, before action" />
            <Stat size="lg" label="stablecoin risk exposure" value={money(e.total_stablecoin_risk_exposure)}
              sub="synthetic sample, exposure not loss" />
            <Stat size="lg" label="approved exposure" value={money(e.total_approved_exposure)}
              sub="principal the approved sample would carry" />
          </div>

          <div className="mt-6 max-w-[86ch]">
            <Note tone="caveat">
              These are modeled estimates on a public benchmark dataset under labeled assumptions,
              not losses realized by any lender. Read the rankings and rates rather than the
              absolute dollar totals.
            </Note>
          </div>

          <div className="mt-12 grid gap-10 lg:grid-cols-2">
            <div>
              <Label>Loss by risk grade</Label>
              <Block tone="flat" className="px-3 py-4">
                <BarFlat data={elGrade} x="name" y="value" money height={250} />
              </Block>
              <p className="mt-3 max-w-[58ch] text-[12.5px] leading-relaxed text-ink-soft">
                Modeled loss climbs steeply through the weaker grades, which is what the grade
                boundaries are for.
              </p>
            </div>
            <div>
              <Label>Loss by decision</Label>
              <Block tone="flat" className="px-3 py-4">
                <BarFlat data={elDecision} x="name" y="value" money height={250} colorFor={(row) => stateColor(row.name)} />
              </Block>
              <p className="mt-3 max-w-[58ch] text-[12.5px] leading-relaxed text-ink-soft">
                Declined applicants carry the largest modeled loss, which is the point: that loss is
                avoided rather than booked.
              </p>
            </div>
          </div>

          <div className="mt-6">
            <Scope>
              These totals match the overview because they share its scope: every scored applicant
              and every scored transaction. The Policy Lab reports narrower quantities on purpose -
              credit loss on approved accounts only, and the fraud loss a policy lets through - so
              its figures are smaller by design rather than in conflict with these.
            </Scope>
          </div>
        </TabPanel>
      </Tabs>
    </Section>
  );
}
