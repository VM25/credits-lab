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
  "Turning raw borrower + transaction data into governed decisions, not just predictions.",
  "Calibrated probability-of-default and rare-event fraud detection (PR-AUC, not accuracy).",
  "Expected-loss translation (PD × LGD × EAD) with labeled assumptions and stress testing.",
  "Model-risk governance: honest Pass / Monitor / Fail verdicts, including a Monitor on the credit model.",
  "A full Python engine deployed behind a React decision terminal that reads only reconciled outputs.",
];

const NOT = [
  "a production lending, fraud, or regulatory-compliance system",
  "a bank report or PDF turned into a web page",
  "a generic ML dashboard or a crypto / trading product",
  "a source of real lending decisions or real customer data",
];

export function Workflow() {
  return (
    <Section id="workflow" label="How the decision engine works" title="From data to a governed decision"
      note="Read this first. Every module below is one stage of a single pipeline - not a collection of unrelated charts.">

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

      <div className="mt-2 grid gap-2 lg:grid-cols-2">
        <Panel>
          <PanelHead left="How to read this" />
          <ul className="list-none px-4 py-3 text-[12.5px] leading-relaxed text-ink">
            <li>Start at the Risk Command Center for the portfolio snapshot, then follow the sections top to bottom.</li>
            <li>Hover any underlined term (PD, PR-AUC, PSI, …) for a plain-English definition.</li>
            <li>Select a row in the applicant or transaction tables to see input → score → decision → reason → loss.</li>
            <li>Move the Policy Simulator controls to see growth, loss, and review burden trade off in real backend scenarios.</li>
          </ul>
        </Panel>
        <div className="grid gap-2">
          <Panel>
            <PanelHead left="What this proves" />
            <ul className="list-none divide-y divide-line text-[12px]">
              {PROVES.map((p) => <li key={p} className="px-4 py-1.5 text-ink">{p}</li>)}
            </ul>
          </Panel>
          <Panel>
            <PanelHead left="What this is not" />
            <div className="px-4 py-2 text-[12px] text-ink-soft">
              Not {NOT.map((n, i) => <span key={n}>{i > 0 ? ", " : ""}{n}</span>)}.
            </div>
          </Panel>
        </div>
      </div>

      <Panel className="mt-2">
        <PanelHead left="Glossary" right="hover these terms anywhere on the page" />
        <div className="grid gap-x-6 gap-y-1 px-4 py-3 md:grid-cols-2">
          {Object.entries(GLOSSARY).map(([k, v]) => (
            <div key={k} className="grid grid-cols-[130px_1fr] gap-2 border-b border-line py-1.5">
              <span className="reg text-[10px] text-accent">{k}</span>
              <span className="text-[11.5px] leading-snug text-ink-soft">{v}</span>
            </div>
          ))}
        </div>
      </Panel>
    </Section>
  );
}
