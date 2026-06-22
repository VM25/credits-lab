import { useEffect, useState } from "react";
import { loadAll, type Bundle } from "./lib/load";
import { Hero } from "./sections/Hero";
import { CommandCenter } from "./sections/CommandCenter";
import { Underwriting } from "./sections/Underwriting";
import { PolicySimulator } from "./sections/PolicySimulator";
import { FraudMonitor } from "./sections/FraudMonitor";
import { StablecoinMonitor } from "./sections/StablecoinMonitor";
import { ExpectedLoss } from "./sections/ExpectedLoss";
import { ModelValidation } from "./sections/ModelValidation";
import { StressTesting } from "./sections/StressTesting";
import { Methodology } from "./sections/Methodology";

const NAV = [
  ["overview", "Overview"],
  ["command-center", "Command center"],
  ["underwriting", "Underwriting"],
  ["policy-simulator", "Policy simulator"],
  ["fraud", "Fraud & payments"],
  ["stablecoin", "Stablecoin"],
  ["expected-loss", "Expected loss"],
  ["validation", "Model validation"],
  ["stress", "Stress testing"],
  ["methodology", "Methodology"],
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
        <p className="mt-3 text-[13px] text-ink-soft">
          Run the backend pipeline first: <span className="num">python -m src.run_pipeline</span>, then rebuild the frontend.
        </p>
      </div>
    );
  }
  if (!bundle) {
    return <div className="mx-auto max-w-[1480px] px-5 py-20 reg text-[12px] text-ink-soft">loading risk outputs…</div>;
  }

  return (
    <div className="mx-auto max-w-[1480px] px-5">
      <Header />
      <nav className="sticky top-0 z-20 -mx-5 mb-2 flex flex-wrap gap-x-4 gap-y-1 border-b border-line bg-bg px-5 py-2">
        {NAV.map(([id, label]) => (
          <a key={id} href={`#${id}`} className="reg text-[10.5px] text-ink-soft hover:text-accent">
            {label}
          </a>
        ))}
      </nav>

      <Hero b={bundle} />
      <CommandCenter b={bundle} />
      <Underwriting b={bundle} />
      <PolicySimulator b={bundle} />
      <FraudMonitor b={bundle} />
      <StablecoinMonitor b={bundle} />
      <ExpectedLoss b={bundle} />
      <ModelValidation b={bundle} />
      <StressTesting b={bundle} />
      <Methodology b={bundle} />

      <footer className="border-t border-line py-8 text-[12px] text-ink-soft">
        <span className="reg text-[10.5px]">Credit &amp; Payments Risk · Decision Terminal</span>
        <span className="mx-2">·</span>
        Modeled estimates from hybrid (real + clearly-labeled synthetic) data. Not a deployed system.
      </footer>
    </div>
  );
}

function Header() {
  return (
    <header className="py-7">
      <div className="reg text-[11px] text-accent">
        Underwriting Strategy · Fraud Monitoring · Expected Loss · Model Risk
      </div>
      <h1 className="mt-2 text-[30px] font-bold leading-tight tracking-tight text-ink">
        Credit &amp; Payments Risk Decision Engine
      </h1>
      <p className="mt-2 max-w-[80ch] text-[14px] text-ink-soft">
        Borrower and transaction data translated into underwriting decisions, fraud controls,
        expected-loss estimates, and model-risk validation evidence.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {["Underwriting", "Fraud & payments", "Expected loss", "Model risk"].map((m) => (
          <span key={m} className="reg border border-line px-2 py-1 text-[10px] text-ink">{m}</span>
        ))}
      </div>
    </header>
  );
}
