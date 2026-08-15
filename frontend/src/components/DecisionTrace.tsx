import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import type { Bundle } from "../lib/load";
import { Block, StateWord, Scope } from "./ui";
import { Term } from "./guide";
import { pct, money, moneyFull, stateColor } from "../lib/format";

// Signature element: one real applicant from underwriting_decisions.json carried
// through the engine - score, policy gate, action, limit, loss, explanation.
// The gate itself is drawn on the PD scale, so the decision is visibly a
// consequence of where the score falls against the operating cutoffs.

const readable = (s: string) => (s || "").replace(/_/g, " ");

export function DecisionTrace({ b }: { b: Bundle }) {
  const rows: any[] = b.underwritingDecisions.rows ?? [];
  const op = b.policyLoss?.operating_point ?? {};
  const approveCut = Number(op.approve);
  const declineCut = Number(op.decline);

  // Deterministic exemplars: the first applicant of each outcome in file order.
  const picks = useMemo(() => {
    const find = (d: string) => rows.find((r) => r.decision === d);
    return [find("approve"), find("review"), find("decline")].filter(Boolean);
  }, [rows]);

  const [i, setI] = useState(0);
  const r = picks[i];
  if (!r || !Number.isFinite(approveCut)) return null;

  const pd = Number(r.PD);
  const col = stateColor(r.decision);
  const reasons = [r.top_reason_1, r.top_reason_2, r.top_reason_3].filter(Boolean);

  return (
    <Block tone="deep" className="px-6 py-6 lg:px-8 lg:py-7">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h3 className="text-[17px] font-semibold tracking-tight text-ink">
          One applicant through the engine
        </h3>
        <div className="flex gap-1">
          {picks.map((p: any, k: number) => (
            <button
              key={p.applicant_id}
              onClick={() => setI(k)}
              className={`num px-2.5 py-1 text-[11px] transition-colors ${
                k === i ? "bg-ink text-bg" : "text-ink-soft hover:bg-panel-4"
              }`}
            >
              {p.decision}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6 grid gap-8 lg:grid-cols-[190px_1fr_230px] lg:gap-10">
        {/* 1. the applicant + score */}
        <div>
          <div className="text-[11.5px] text-ink-soft">applicant</div>
          <div className="num text-[15px] text-ink">{r.applicant_id}</div>
          <div className="mt-5 text-[11.5px] text-ink-soft">modeled <Term k="PD">probability of default</Term></div>
          <div className="num text-[44px] font-medium leading-none text-ink">{pct(pd)}</div>
          <div className="mt-2 text-[11.5px] text-ink-soft">
            risk grade <span className="num text-[13px] font-medium text-ink">{r.risk_grade}</span>
          </div>
        </div>

        {/* 2. the policy gate, drawn on the PD scale */}
        <div>
          <div className="text-[11.5px] text-ink-soft">policy gate</div>
          <div className="relative mt-6 h-9 w-full">
            <div className="absolute inset-x-0 top-3 flex h-3">
              <div style={{ width: `${approveCut * 100}%`, background: stateColor("approve") }} />
              <div style={{ width: `${(declineCut - approveCut) * 100}%`, background: stateColor("review") }} />
              <div style={{ flex: 1, background: stateColor("decline") }} />
            </div>
            <motion.div
              className="absolute top-0"
              initial={false}
              animate={{ left: `${Math.min(pd, 1) * 100}%` }}
              transition={{ duration: 0.32, ease: "easeOut" }}
              style={{ transform: "translateX(-50%)" }}
            >
              <div className="h-9 w-0.5 bg-ink" />
              <div className="num mt-1 whitespace-nowrap text-[11px] font-medium text-ink">{pct(pd)}</div>
            </motion.div>
          </div>
          <div className="mt-7 flex justify-between text-[11px] text-ink-soft">
            <span>approve <span className="num">PD &lt; {pct(approveCut, 0)}</span></span>
            <span>review <span className="num">{pct(approveCut, 0)}-{pct(declineCut, 0)}</span></span>
            <span>decline <span className="num">PD ≥ {pct(declineCut, 0)}</span></span>
          </div>
          <p className="mt-4 max-w-[54ch] text-[12px] leading-relaxed text-ink-soft">
            The score alone decides nothing. It is the cutoffs that turn a probability into an
            action, and those cutoffs are what the Policy Lab lets you move.
          </p>
        </div>

        {/* 3. the consequence */}
        <div>
          <div className="text-[11.5px] text-ink-soft">action</div>
          <div className="mt-0.5"><StateWord label={r.decision} size="lg" /></div>

          <div className="mt-5 grid grid-cols-2 gap-4">
            <div>
              <div className="text-[11px] text-ink-soft">recommended limit</div>
              <div className="num text-[15px] text-ink">{money(r.recommended_credit_limit)}</div>
            </div>
            <div>
              <div className="text-[11px] text-ink-soft">expected loss</div>
              <div className="num text-[15px]" style={{ color: col }}>{moneyFull(r.expected_loss)}</div>
            </div>
          </div>

          <div className="mt-5">
            <div className="text-[11px] text-ink-soft">why</div>
            <ul className="mt-1 space-y-0.5">
              {reasons.map((c: string) => (
                <li key={c} className="text-[12px] leading-snug text-ink">{readable(c)}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <div className="mt-7">
        <Scope>
          Three exemplar applicants, taken in file order from the underwriting decision output.
          Expected loss is PD x LGD x EAD under labeled assumptions, not a realized loss.
        </Scope>
      </div>
    </Block>
  );
}
