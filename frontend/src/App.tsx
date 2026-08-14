import { useEffect, useState } from "react";
import * as Tooltip from "@radix-ui/react-tooltip";
import { loadAll, type Bundle } from "./lib/load";
import { GITHUB_URL, SITE_URL } from "./lib/site";
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

const DEMONSTRATES = [
  "credit underwriting decisioning",
  "fraud & payments-risk scoring",
  "expected-loss modeling",
  "model validation & calibration",
  "policy-threshold simulation",
  "full Python-to-React deployment",
  "public/synthetic data disclosure",
  "testing & reconciliation discipline",
];

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
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="reg ml-auto text-[10.5px] text-accent hover:underline">GitHub ↗</a>
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
          <div className="reg text-[11px] text-accent">What this project demonstrates</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {DEMONSTRATES.map((d) => <span key={d} className="border border-line px-2 py-1 text-[11px] text-ink">{d}</span>)}
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <GithubLink />
            <a href={SITE_URL} className="reg text-[10.5px] text-accent hover:underline">{SITE_URL.replace("https://", "")}</a>
          </div>
          <p className="mt-3 max-w-[90ch] text-[11.5px] text-ink-soft">
            Credit &amp; Payments Risk Decision Engine - a portfolio research project using public (LendingClub, Kaggle, FRED) and clearly-labeled synthetic data. Modeled estimates, not realized losses. Not a production lending, fraud, or regulatory-compliance system.
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
          <div className="reg text-[11px] text-accent">Underwriting Strategy · Fraud Monitoring · Expected Loss · Model Risk</div>
          <h1 className="mt-2 text-[30px] font-bold leading-tight tracking-tight text-ink">Credit &amp; Payments Risk Decision Engine</h1>
          <p className="mt-2 max-w-[80ch] text-[14px] text-ink-soft">
            Borrower and transaction data translated into underwriting decisions, fraud controls, expected-loss estimates, and model-risk validation evidence.
          </p>
        </div>
        <div className="shrink-0 pt-1"><GithubLink compact /></div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {["Underwriting Strategy", "Fraud & Payments", "Expected Loss", "Model Risk & Validation"].map((m) => (
          <span key={m} className="reg border border-line px-2 py-1 text-[10px] text-ink">{m}</span>
        ))}
      </div>
    </header>
  );
}
