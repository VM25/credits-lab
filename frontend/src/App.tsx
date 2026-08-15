import { useEffect, useState } from "react";
import * as Tooltip from "@radix-ui/react-tooltip";
import { loadAll, type Bundle } from "./lib/load";
import { GithubLink } from "./components/guide";
import { Hero } from "./sections/Hero";
import { Workflow } from "./sections/Workflow";
import { CommandCenter } from "./sections/CommandCenter";
import { Underwriting } from "./sections/Underwriting";
import { FraudMonitor } from "./sections/FraudMonitor";
import { PolicySimulator } from "./sections/PolicySimulator";
import { ExpectedLoss } from "./sections/ExpectedLoss";
import { ModelValidation } from "./sections/ModelValidation";
import { StablecoinMonitor } from "./sections/StablecoinMonitor";
import { StressTesting } from "./sections/StressTesting";
import { Methodology } from "./sections/Methodology";
import { Architecture } from "./sections/Architecture";

const NAV = [
  ["overview", "Overview"],
  ["workflow", "Workflow"],
  ["command-center", "Command center"],
  ["underwriting", "Underwriting"],
  ["fraud", "Fraud"],
  ["policy-simulator", "Simulator"],
  ["expected-loss", "Expected loss"],
  ["validation", "Validation"],
  ["stablecoin", "Stablecoin"],
  ["stress", "Stress"],
  ["methodology", "Methodology"],
  ["architecture", "Architecture"],
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
        <div className="reg text-[11px] text-fail">data load error</div>
        <p className="num mt-2 text-[13px] text-ink">{err}</p>
        <p className="mt-3 text-[13px] text-ink-soft">Run the backend pipeline first: <span className="num">python -m src.run_pipeline</span>, then rebuild the frontend.</p>
      </div>
    );
  }
  if (!bundle) {
    return <div className="mx-auto max-w-[1480px] px-5 py-20 reg text-[12px] text-ink-soft">loading risk outputs…</div>;
  }

  return (
    <Tooltip.Provider delayDuration={120}>
      <div className="mx-auto max-w-[1480px] px-5">
        <Header />
        <nav className="sticky top-0 z-20 -mx-5 mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-line bg-bg px-5 py-2">
          {NAV.map(([id, label]) => (
            <a key={id} href={`#${id}`} className="reg text-[10.5px] text-ink-soft hover:text-accent">{label}</a>
          ))}
        </nav>

        <Hero b={bundle} />
        <Workflow />
        <CommandCenter b={bundle} />
        <Underwriting b={bundle} />
        <FraudMonitor b={bundle} />
        <PolicySimulator b={bundle} />
        <ExpectedLoss b={bundle} />
        <ModelValidation b={bundle} />
        <StablecoinMonitor b={bundle} />
        <StressTesting b={bundle} />
        <Methodology b={bundle} />
        <Architecture />

        <footer className="mt-4 border-t border-line py-8">
          <p className="max-w-[70ch] text-[13px] leading-relaxed text-ink">
            An end-to-end study of how borrower and transaction data become governed decisions: underwriting, fraud routing, expected loss, a policy simulator, and the validation evidence behind them, built as a Python engine and deployed behind this React terminal.
          </p>
          <p className="mt-4 max-w-[80ch] text-[11.5px] leading-relaxed text-ink-soft">
            Portfolio research project on public LendingClub, Kaggle ULB, and FRED data plus clearly-labeled synthetic stablecoin and payment-context features. Modeled estimates, not realized losses. Not a production lending, fraud, or regulatory-compliance system.
          </p>
        </footer>
      </div>
    </Tooltip.Provider>
  );
}

function Header() {
  return (
    <header className="py-7">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[31px] font-bold leading-tight tracking-tight text-ink">Credit &amp; Payments Risk Decision Engine</h1>
          <p className="mt-2 max-w-[78ch] text-[14.5px] leading-snug text-ink-soft">
            Borrower and transaction data, turned into underwriting decisions, fraud controls, expected-loss estimates, and the evidence to trust the models behind them.
          </p>
        </div>
        <div className="shrink-0 pt-1"><GithubLink compact /></div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {["Underwriting", "Fraud & payments", "Expected loss", "Model risk"].map((m) => (
          <span key={m} className="reg border border-line px-2 py-1 text-[10px] text-ink">{m}</span>
        ))}
      </div>
    </header>
  );
}
