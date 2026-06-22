import type { Config } from "tailwindcss";

// Approved design tokens (doc 10). Flat, sharp, hairline, no shadows.
// Fonts: Fira Sans (text) + Fira Code (tabular numerics) — both pass the font ban.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#D8E0D7",
        panel: "#C7D2C6",
        "panel-2": "#BCC9BB",
        line: "#9CAF9D",
        ink: "#18241E",
        "ink-soft": "#45554C",
        accent: "#285C5E",
        pass: "#35684F",
        review: "#6C6440",
        fail: "#7C4B40",
      },
      fontFamily: {
        sans: ['"Fira Sans"', "system-ui", "sans-serif"],
        mono: ['"Fira Code"', "ui-monospace", "monospace"],
      },
      borderRadius: {
        none: "0",
        DEFAULT: "0",
      },
    },
  },
  plugins: [],
} satisfies Config;
