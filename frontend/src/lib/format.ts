// Display-only formatting. Never alters underlying values.

export const pct = (x: number | null | undefined, dp = 1): string =>
  x == null || Number.isNaN(x) ? "—" : `${(x * 100).toFixed(dp)}%`;

export const num = (x: number | null | undefined, dp = 2): string =>
  x == null || Number.isNaN(x) ? "—" : x.toFixed(dp);

export const int = (x: number | null | undefined): string =>
  x == null || Number.isNaN(x) ? "—" : Math.round(x).toLocaleString("en-US");

// Compact USD, e.g. $162.3M / $901.1K.
export const money = (x: number | null | undefined): string => {
  if (x == null || Number.isNaN(x)) return "—";
  const a = Math.abs(x);
  if (a >= 1e9) return `$${(x / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `$${(x / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `$${(x / 1e3).toFixed(1)}K`;
  return `$${x.toFixed(0)}`;
};

export const moneyFull = (x: number | null | undefined): string =>
  x == null || Number.isNaN(x)
    ? "—"
    : x.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

// Token hexes for chart libraries (mirror of theme.css :root).
export const TOK = {
  bg: "#d8e0d7",
  panel: "#c7d2c6",
  panel2: "#bcc9bb",
  line: "#9caf9d",
  ink: "#18241e",
  inkSoft: "#45554c",
  accent: "#285c5e",
  pass: "#35684f",
  review: "#6c6440",
  fail: "#7c4b40",
} as const;

// Decision / verdict / action -> token color.
export const stateColor = (s: string): string => {
  const k = (s || "").toLowerCase();
  if (["approve", "approved", "pass", "normal"].includes(k)) return TOK.pass;
  if (["review", "monitor", "step_up", "stepup"].includes(k)) return TOK.review;
  if (["decline", "declined", "fail", "block", "blocked", "high_risk"].includes(k)) return TOK.fail;
  return TOK.accent;
};
