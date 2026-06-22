import type { Bundle } from "../lib/load";
import { MetricRow } from "../components/ui";
import { pct, money, num } from "../lib/format";

export function Hero({ b }: { b: Bundle }) {
  const c = b.commandCenter;
  return (
    <section id="overview" className="py-2">
      <MetricRow
        items={[
          { label: "applicants scored", value: num(c.total_applicants, 0) === "—" ? "—" : c.total_applicants.toLocaleString(), sub: "LendingClub accepted (real)" },
          { label: "approval rate", value: pct(c.approval_rate), sub: "validation-derived policy" },
          { label: "expected credit loss", value: money(c.total_expected_credit_loss), sub: "PD × LGD × EAD (modeled)" },
          { label: "expected fraud loss", value: money(c.total_expected_fraud_loss), sub: "Kaggle labels (real)" },
        ]}
      />
      <p className="mt-3 text-[12px] text-ink-soft">{c.data_disclaimer}</p>
    </section>
  );
}
