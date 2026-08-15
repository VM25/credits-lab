import { useEffect, useState } from "react";
import * as Tooltip from "@radix-ui/react-tooltip";
import { loadAll, type Bundle } from "./lib/load";
import { GithubLink, ReferenceDrawer } from "./components/guide";
import { Overview } from "./sections/Overview";
import { Underwriting } from "./sections/Underwriting";
import { FraudPayments } from "./sections/FraudPayments";
import { PolicyLab } from "./sections/PolicyLab";
import { ExpectedLoss } from "./sections/ExpectedLoss";
import { Validation } from "./sections/Validation";
import { Evidence } from "./sections/Evidence";

const NAV = [
  ["overview", "Overview"],
  ["underwriting", "Underwriting"],
  ["fraud", "Fraud & payments"],
  ["policy-lab", "Policy lab"],
  ["expected-loss", "Expected loss"],
  ["validation", "Model validation"],
  ["evidence", "Evidence"],
] as const;

export function App() {
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    loadAll().then(setBundle).catch((e) => setErr(String(e)));
  }, []);

  if (err) {
    return (
      <div className="mx-auto max-w-[680px] px-5 py-20">
        <div className="text-[13px] text-fail">Could not load the risk outputs.</div>
        <p className="num mt-2 text-[13px] text-ink">{err}</p>
        <p className="mt-3 text-[13px] text-ink-soft">
          Run the pipeline first: <span className="num">python -m src.run_pipeline</span>, then rebuild the frontend.
        </p>
      </div>
    );
  }
  if (!bundle) {
    return <div className="mx-auto max-w-[1480px] px-5 py-20 text-[13px] text-ink-soft">Loading risk outputs…</div>;
  }

  return (
    <Tooltip.Provider delayDuration={120}>
      <Header />
      <main>
        <Overview b={bundle} />
        <Underwriting b={bundle} />
        <FraudPayments b={bundle} />
        <PolicyLab b={bundle} />
        <ExpectedLoss b={bundle} />
        <Validation b={bundle} />
        <Evidence b={bundle} />
      </main>
      <ReferenceDrawer />
      <Footer />
    </Tooltip.Provider>
  );
}

function Header() {
  return (
    <header>
      <div className="mx-auto max-w-[1480px] px-5 pt-9 pb-6">
        <div className="flex items-start justify-between gap-6">
          <div>
            <h1 className="text-[15px] font-semibold tracking-tight text-ink">
              Credit &amp; Payments Risk Decision Engine
            </h1>
            <p className="mt-1 text-[12.5px] text-ink-soft">
              Underwriting · fraud &amp; payments · expected loss · model risk
            </p>
          </div>
          <div className="shrink-0 pt-0.5"><GithubLink /></div>
        </div>
      </div>
      <nav className="sticky top-0 z-20 border-y border-line bg-bg">
        <div className="mx-auto flex max-w-[1480px] flex-wrap items-center gap-x-7 gap-y-1 px-5 py-2.5">
          {NAV.map(([id, label]) => (
            <a key={id} href={`#${id}`} className="text-[12.5px] text-ink-soft transition-colors hover:text-accent">
              {label}
            </a>
          ))}
        </div>
      </nav>
    </header>
  );
}

function Footer() {
  return (
    <footer className="mx-auto max-w-[1480px] px-5 pb-16 pt-8">
      <p className="max-w-[76ch] text-[13px] leading-relaxed text-ink">
        An end-to-end study of how borrower and transaction data become governed decisions:
        underwriting, fraud routing, expected loss, a policy simulator, and the validation evidence
        behind them, built as a Python engine and read by this interface.
      </p>
      <p className="mt-4 max-w-[84ch] text-[11.5px] leading-relaxed text-ink-soft">
        Portfolio research project on public LendingClub, Kaggle ULB and FRED data plus
        clearly-labeled synthetic stablecoin and payment-context features. Modeled estimates, not
        realized losses. Not a lending, fraud, or regulatory-compliance system, and no decisions
        here affect any real applicant.
      </p>
    </footer>
  );
}
