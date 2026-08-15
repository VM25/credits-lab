import { Section, Panel, PanelHead } from "../components/ui";
import { GLOSSARY } from "../lib/site";

const STEPS = [
  "borrower / transaction data",
  "risk features + model scores",
  "policy rules + thresholds",
  "approve / review / decline · payment action",
  "expected loss estimate",
  "model-risk validation",
  "policy simulation",
];

const QUESTIONS: [string, string][] = [
  ["Who should get credit?", "Underwriting engine → PD, risk grade, approve / review / decline, credit limit, reason codes."],
  ["Which payments are risky?", "Fraud & payments monitor → fraud score, action (approve / step-up / review / block), expected loss."],
  ["How much could be lost?", "Expected-loss engine → PD × LGD × EAD, by segment, under base and stressed conditions."],
  ["Can the models be trusted?", "Model-risk validation → calibration, drift, segment behavior, Pass / Monitor / Fail verdicts."],
  ["What if thresholds change?", "Policy simulator → 180 precomputed scenarios trading growth against loss and review burden."],
];

const PROVES = [
  "Raw borrower and transaction data becoming governed decisions, not just predictions.",
  "Calibrated probability-of-default and rare-event fraud detection scored the right way (PR-AUC, not accuracy).",
  "Expected loss (PD × LGD × EAD) built from labeled assumptions and put under stress.",
  "Honest model-risk governance, including a Monitor verdict left standing on the credit model.",
];

const NOT = [
  "a production lending, fraud, or compliance system",
  "a bank report or PDF dressed up as a web page",
  "a generic ML dashboard or a crypto / trading product",
];

export function Workflow() {
  return (
    <Section id="workflow" label="How the decision engine works" title="From data to a governed decision"
      note="Every module below is one stage of a single pipeline, not a set of unrelated charts. The credit book, the payment stream, and the policy grid all flow through the same path.">

      <Panel>
        <PanelHead left="The pipeline" />
        <div className="flex flex-wrap items-stretch gap-1 px-3 py-4">
          {STEPS.map((s, i) => (
            <div key={s} className="flex items-center">
              <div className="border border-line bg-panel-2 px-3 py-2 text-[12px] leading-tight text-ink" style={{ maxWidth: 150 }}>
                <span className="num mr-1 text-[10px] text-accent">{i + 1}</span>{s}
              </div>
              {i < STEPS.length - 1 && <span className="mx-1 text-accent" aria-hidden="true">→</span>}
            </div>
          ))}
        </div>
      </Panel>

      <Panel className="mt-2">
        <PanelHead left="The five questions this system answers" right="each maps to a section below" />
        <div className="divide-y divide-line">
          {QUESTIONS.map(([q, a]) => (
            <div key={q} className="grid gap-1 px-4 py-2.5 md:grid-cols-[300px_1fr]">
              <div className="text-[13px] font-medium text-ink">{q}</div>
              <div className="text-[12.5px] text-ink-soft">{a}</div>
            </div>
          ))}
        </div>
      </Panel>

      <div className="mt-2 grid gap-2 lg:grid-cols-[1.4fr_1fr]">
        <Panel>
          <PanelHead left="What this proves" />
          <ul className="list-none divide-y divide-line text-[12.5px]">
            {PROVES.map((p) => <li key={p} className="px-4 py-2 text-ink">{p}</li>)}
          </ul>
        </Panel>
        <Panel>
          <PanelHead left="What this is not" />
          <div className="px-4 py-2.5 text-[12.5px] leading-relaxed text-ink-soft">
            It is not {NOT.map((n, i) => <span key={n}>{i === NOT.length - 1 ? ", or " : i > 0 ? ", " : ""}{n}</span>)}, and it makes no lending decisions and touches no real customer data.
          </div>
        </Panel>
      </div>

      <Panel className="mt-2">
        <PanelHead left="Key risk terms" />
        <dl className="grid gap-x-8 gap-y-3 px-4 py-4 md:grid-cols-2">
          {Object.entries(GLOSSARY).map(([k, v]) => (
            <div key={k}>
              <dt className="reg text-[10px] text-accent">{k}</dt>
              <dd className="mt-0.5 text-[12px] leading-snug text-ink-soft">{v}</dd>
            </div>
          ))}
        </dl>
      </Panel>
    </Section>
  );
}
