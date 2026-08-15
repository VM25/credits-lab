// Project links + plain-English glossary + architecture facts.
// (Links and descriptive counts are static project facts, not risk metrics -
// every risk NUMBER still loads from data/outputs.)

export const GITHUB_URL = "https://github.com/VM25/credits-lab";
export const SITE_URL = "https://credits-engine.netlify.app";

// Jargon defined once; surfaced on hover for inline terms.
export const GLOSSARY: Record<string, string> = {
  PD: "The model's estimated chance that a borrower fails to repay.",
  LGD: "The share of a loan assumed lost if the borrower defaults. An assumption here, not a recovery model.",
  EAD: "The dollar amount estimated to be at risk when a default happens.",
  "ROC-AUC": "How well the model ranks riskier cases above safer ones. 0.5 is random; 1.0 is perfect separation.",
  "PR-AUC": "The right score for rare fraud: it rewards catching fraud without over-flagging good payments. Accuracy looks great here and means nothing.",
  Brier: "How close predicted probabilities land to what actually happened. Lower is better.",
  KS: "How far apart the good and bad score distributions sit at their widest point.",
  PSI: "How much recent data has drifted from the training data. Under 0.10 is stable; past 0.25 is a meaningful shift.",
  calibration: "Whether the probabilities mean what they say. A 20% group should default about one time in five.",
  "champion / challenger": "The champion (a transparent logistic scorecard) makes the decisions; the challenger (gradient boosting) is a tougher benchmark kept to keep it honest. The simpler model wins unless the challenger is clearly better and still well-calibrated.",
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
