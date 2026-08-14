// Project links + plain-English glossary + architecture facts.
// (Links and descriptive counts are static project facts, not risk metrics -
// every risk NUMBER still loads from data/outputs.)

export const GITHUB_URL = "https://github.com/VM25/credits-lab";
export const SITE_URL = "https://credits-engine.netlify.app";

// Jargon defined in one place; surfaced via hover tooltips.
export const GLOSSARY: Record<string, string> = {
  PD: "Probability of default - the model's estimated chance a borrower fails to repay.",
  LGD: "Loss given default - the assumed share of exposure lost if a borrower defaults (an assumption, not observed recovery).",
  EAD: "Exposure at default - the estimated dollar amount at risk when default occurs.",
  "ROC-AUC": "Ranking quality - the chance the model scores a true bad above a true good. 0.5 = coin flip, 1.0 = perfect.",
  "PR-AUC": "Precision-recall AUC - the headline metric for rare-event fraud. It rewards catching fraud without over-flagging good payments. Accuracy is misleading when 99%+ of payments are legitimate.",
  Brier: "Brier score - how well predicted probabilities match reality; lower is better.",
  KS: "Kolmogorov-Smirnov - the maximum separation between the score distributions of goods and bads.",
  PSI: "Population stability index - drift between training and recent data. <0.10 stable, 0.10-0.25 monitor, ≥0.25 material shift.",
  calibration: "Whether predicted probabilities match observed outcomes - a 20% PD group should default about 20% of the time.",
  "champion / challenger": "The champion is the model that makes decisions (a transparent logistic scorecard). The challenger (gradient boosting) is a stronger benchmark used to stress-test it. The champion is kept for explainability unless the challenger is clearly better AND still well-calibrated.",
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
