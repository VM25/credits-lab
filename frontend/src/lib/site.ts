// Project links + risk-term reference + architecture facts.
// (Links and descriptive counts are static project facts, not risk metrics -
// every risk NUMBER still loads from data/outputs.)

export const GITHUB_URL = "https://github.com/VM25/credits-lab";

// Defined once; surfaced on hover for inline terms and in the reference drawer.
export const GLOSSARY: Record<string, string> = {
  PD: "Probability of default: the modeled chance that a borrower fails to repay.",
  LGD: "Loss given default: the share of exposure assumed lost when a default occurs. An imposed assumption here, not a recovery model.",
  EAD: "Exposure at default: the balance assumed to be outstanding when a default occurs.",
  "ROC-AUC": "The probability that a randomly chosen defaulting account scores above a randomly chosen non-defaulting one. 0.5 is no better than chance.",
  "PR-AUC": "Summarizes precision against recall on the rare class. It is the appropriate headline for fraud because it ignores the large mass of correctly approved legitimate payments, which accuracy is dominated by.",
  Brier: "Mean squared error between predicted probabilities and outcomes. Lower is better, and it penalizes overconfidence.",
  KS: "The largest gap between the cumulative score distributions of defaulting and non-defaulting accounts.",
  PSI: "Population stability index: how far the scored population has drifted from the training population. Below 0.10 is conventionally treated as stable, above 0.25 as a material shift.",
  calibration: "Whether stated probabilities match observed frequencies. In a well-calibrated model, accounts predicted at 20% default close to one time in five.",
  "champion / challenger": "The champion (a transparent logistic scorecard) makes the decisions; the challenger (gradient boosting) is held alongside as a benchmark. The champion keeps the role unless the challenger is clearly better and equally well calibrated.",
};

// Architecture / code-evidence facts (verified counts from the repo).
export const ARCH = {
  pythonFiles: 30,
  testFiles: 20,
  testFunctions: 40,
  backend: ["Python 3", "pandas", "NumPy", "scipy", "scikit-learn", "joblib", "pytest"],
  frontend: ["React 19", "TypeScript", "Tailwind CSS", "Radix UI", "Recharts", "Vite", "Netlify"],
  layers: ["data ingestion", "feature engineering", "model training + calibration", "decisioning", "expected loss", "validation", "reporting outputs", "React frontend"],
};
