# Frontend & Design Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **PRECONDITION:** Plan 1 (Backend & Data Engine) is complete — `data/outputs` holds all 9 CSV + 16 JSON and `reconcile.required_outputs()` + `reconcile.totals()` pass. Do **not** start this plan until that is true.

**Goal:** Build the desktop-first "risk decision terminal" SPA that renders the 10 required sections entirely from `data/outputs` — no hardcoded metrics, no fake interactivity — under the strict doc-10 design system.

**Architecture:** Vite + React + TypeScript + Tailwind + shadcn/ui (de-SaaS'd) + framer-motion (functional motion only) + Recharts. A single data-loading layer fetches static JSON/CSV copied from `data/outputs`; every component is a pure function of that data. Typography and palette are produced by the mandatory design skills within the doc-10 forbidden lists and approved by the user before any UI is built.

**Tech Stack:** Vite 6, React 19, TypeScript 5, Tailwind, shadcn/ui, framer-motion, Recharts, PapaParse (CSV).

**Authority:** docs 09 (product), 10 (design system), 11 §12–14; spec §8/§9. Forbidden fonts/colors/patterns/copy are hard constraints. Every number traces to `data/outputs`.

**Conventions:**
- No metric literal in any `.tsx`. All values come from fetched files via the data layer.
- No output files created here beyond the frontend app; the simulator reads the precomputed grid (`policy_simulator_results.json`), it does not recompute risk.
- Interactions limited to doc 09 §14: policy sliders, threshold selectors, stress-scenario selector, table row selection, module tabs, chart hover.
- No `README.md`.

---

## File Structure

```
frontend/
  index.html                     # title set; no forbidden fonts
  package.json                   # deps below
  tailwind.config.ts             # tokens from approved design (Task 2)
  postcss.config.js
  tsconfig.json
  vite.config.ts                 # base path; static data served from /data/outputs
  scripts/sync-data.mjs          # copy ../data/outputs -> public/data/outputs
  public/data/outputs/           # synced copy (gitignored; regenerated)
  src/
    main.tsx
    App.tsx                      # shell: header + module tabs + sections
    theme.css                    # design tokens (approved); Tailwind layers
    lib/
      load.ts                    # typed fetchers for each JSON; CSV via PapaParse
      types.ts                   # TS interfaces mirroring output schemas
      format.ts                  # number/pct/currency formatting (display only)
    components/                  # shared primitives (de-SaaS'd shadcn wrappers, charts)
    sections/
      Hero.tsx
      CommandCenter.tsx
      Underwriting.tsx
      PolicySimulator.tsx
      FraudMonitor.tsx
      StablecoinMonitor.tsx
      ExpectedLoss.tsx
      ModelValidation.tsx
      StressTesting.tsx
      Methodology.tsx
  qa/check_frontend.mjs          # final QA scans (traceability, copy, fonts/colors, README)
```

---

## Phase 10 — Design system (gating; no UI code before approval)

### Task 10.1: Verify mandatory design capabilities (stop-condition)

**Files:** none (verification only)
- [ ] **Step 1:** Confirm each mandatory capability (doc 10 §2) is invokable now: skills `emil-design-eng`, `frontend-design`, `design-taste-frontend`, `ui-ux-pro-max`, `senior-frontend`; shadcn MCP (`mcp__Shadcn_UI__*`); framer-motion installable via npm.
- [ ] **Step 2:** If any is unavailable, **STOP and report the missing capability** (do not substitute personal taste). Otherwise record availability and proceed.
- [ ] **Step 3: Commit** (note only) — no code change; proceed to 10.2.

### Task 10.2: Produce design tokens via mandatory skills → user approval gate

**Files:** Create `frontend/src/theme.css` (tokens only), `frontend/tailwind.config.ts` (after approval)
- [ ] **Step 1:** Invoke the design skills to derive **typography + palette + spacing + component treatment** for a "risk decision terminal" (doc 10 §3 product feel). Use the shadcn MCP to plan de-SaaS'd component styling (override rounded-card defaults per doc 10 §7).
- [ ] **Step 2: Constraint check (must pass before showing user):**
  - Fonts NOT in doc 10 §4 forbidden list nor any sans/serif/mono/display/condensed/pro variant of those families; Source Code Pro only for all-caps; no system default that resolves to a forbidden family.
  - Colors NOT in doc 10 §5 (dark) / §6 (light) forbidden lists; not a black/white-only theme.
  - No forbidden UI patterns (doc 10 §7) or motion (doc 10 §8).
- [ ] **Step 3: Present tokens to the user for approval** (font choice, color tokens, sample section mock). **Do not build UI until approved.** If rejected, re-derive via skills (never personal taste) and re-present.
- [ ] **Step 4:** On approval, write `theme.css` + `tailwind.config.ts` tokens.
- [ ] **Step 5: Commit** — `git commit -m "feat(design): approved design tokens (fonts/palette/spacing) within doc-10 constraints"`

---

## Phase 11 — Frontend build (after tokens approved)

### Task 11.1: Scaffold + data sync + data layer

**Files:** `frontend/package.json`, `vite.config.ts`, `postcss.config.js`, `tailwind.config.ts`, `scripts/sync-data.mjs`, `src/main.tsx`, `src/lib/{load.ts,types.ts,format.ts}`; Test: `frontend` builds + a data-layer smoke check
- [ ] **Step 1:** Init Vite React-TS; add deps: `react react-dom framer-motion recharts papaparse` + dev `tailwindcss postcss autoprefixer @types/papaparse`. shadcn/ui initialized and components added via MCP/CLI, then de-SaaS'd per tokens.
- [ ] **Step 2:** `scripts/sync-data.mjs` copies `../data/outputs` → `public/data/outputs`; wire as `predev`/`prebuild` npm scripts. Add `public/data/outputs` to `.gitignore`.
- [ ] **Step 3:** `lib/types.ts` = TS interfaces mirroring each output JSON schema (command center, underwriting, fraud, stablecoin, expected loss, validation, simulator, methodology). `lib/load.ts` = typed `fetch` per file + CSV via PapaParse; throws if a file is missing (surfacing any traceability break).
- [ ] **Step 4: Verify** — `npm run build` succeeds; a smoke check confirms `load.ts` reads `risk_command_center.json` shape.
- [ ] **Step 5: Commit** — `git commit -m "feat(frontend): scaffold, data sync, typed data layer"`

### Task 11.2: App shell — header + module tabs

**Files:** `src/App.tsx`, `src/components/*`
- [ ] **Step 1:** Header with required title "Credit & Payments Risk Decision Engine" + subtitle "Underwriting Strategy · Fraud Monitoring · Expected Loss · Model Risk" + four module labels + data/model disclaimer (synthetic/real labeling from `methodology_summary.json`).
- [ ] **Step 2:** Module tabs/anchors for the 10 sections (doc 09 §3) — no filler sections.
- [ ] **Step 3: Verify** renders; tabs navigate.
- [ ] **Step 4: Commit** — `git commit -m "feat(frontend): app shell, header, module tabs"`

### Task 11.3–11.12: Section components (one task each; pattern below)

Each section: read its data-source file(s) via `lib/load.ts`, render the required fields/charts (Recharts, traceable), apply functional motion only, **no hardcoded numbers**. Test per section = render with the real file and assert key fields appear (and a grep proves no numeric literal in the component).

- [ ] **11.3 Hero / Overview** ← `risk_command_center.json`, `methodology_summary.json`. Shows title/subtitle/thesis, four module labels, primary KPIs, data/model disclaimer. Commit.
- [ ] **11.4 Risk Command Center** ← `risk_command_center.json`. Portfolio KPIs (doc 09 §5 list). Commit.
- [ ] **11.5 Underwriting Decision Engine** ← `underwriting_decisions.json`, `underwriting_policy_summary.json`. Applicant table (PD, grade, decision, limit, EL, reason codes) + charts (PD dist, grade dist, approval mix, EL by grade, top decline reasons); row selection. Commit.
- [ ] **11.6 Policy Simulator** ← `policy_simulator_inputs.json`, `policy_simulator_results.json`. Controls (PD cutoff, review band, fraud threshold, review capacity, stablecoin threshold, stress) select precomputed scenarios; updates decision mix, losses, review volume, **specific** model-risk warnings. Real interactivity (lookup into grid), no recompute/fake. Commit.
- [ ] **11.7 Fraud & Payments Monitor** ← `fraud_alerts.json`, `fraud_policy_summary.json`. Transaction stream (fraud/anomaly score, action, expected loss, review priority, drivers); actions Approve/Step-up/Review/Block; threshold-tradeoff charts. Commit.
- [ ] **11.8 Stablecoin Risk Monitor** ← `stablecoin_alerts.json`. Wallet/counterparty/amount/score/action/exposure/drivers; "AML-style risk indicators" copy only (no "AML compliance"). Commit.
- [ ] **11.9 Expected Loss Engine** ← `expected_loss_summary.json`, `expected_loss_by_segment.json`, `stress_loss_summary.json`. Formula `EL = PD × LGD × EAD`; EL by applicant/grade/decision; base vs stressed; fraud loss; stablecoin exposure. Commit.
- [ ] **11.10 Model Risk & Validation** ← `model_validation_summary.json`, `champion_challenger_comparison.json`, `model_risk_verdicts.json`. Calibration curve, PD decile default table, champion-vs-challenger, fraud PR tradeoff, drift/PSI, segment weakness, verdict panel (Pass/Monitor/Fail). Commit.
- [ ] **11.11 Stress Testing** ← `stress_loss_summary.json`, `policy_loss_comparison.json`. Base/Moderate/Severe impacts (PD/LGD/fraud/stablecoin/total EL); no macro-causality claims. Commit.
- [ ] **11.12 Evidence & Methodology** ← `methodology_summary.json`, `data_quality_report.csv`. Data sources, synthetic disclosure, model list, split method, loss/stress assumptions, validation methods, known limitations. Commit.

---

## Phase 12 — Final QA

### Task 12.1: Automated QA scans

**Files:** Create `qa/check_frontend.mjs` (+ reuse backend `reconcile` for outputs)
- [ ] **Step 1:** Implement scans:
  - **Traceability:** grep `frontend/src/sections` and components for hardcoded numeric metrics (allow only layout constants); fail on metric literals.
  - **Copy restrictions:** scan rendered strings for forbidden terms (doc 09 §15 / doc 10 §11): production-ready, institutional-grade, guaranteed, AML compliance, optimal policy, AI-powered, real-time bank.
  - **Fonts/colors:** scan `theme.css`/`tailwind.config.ts` for forbidden font families and forbidden color names; fail on any.
  - **Forbidden UI:** assert de-SaaS'd (no default rounded-card classes left unoverridden) — heuristic scan.
  - **README absence:** assert no `README.md` exists in repo.
- [ ] **Step 2:** Run backend gates (`python -m src.run_pipeline` clean + `pytest -q`) and `npm run build`.
- [ ] **Step 3:** Run `qa/check_frontend.mjs`; all checks pass. Any failure = do not present build.
- [ ] **Step 4: Commit** — `git commit -m "chore(qa): frontend traceability/copy/font/color/README scans green"`

### Task 12.2: Final build verification

- [ ] **Step 1:** `npm run build` → `dist/` renders all 10 sections from synced data.
- [ ] **Step 2:** Manual spot-check: every visible KPI matches its source file value.
- [ ] **Step 3:** Confirm acceptance standard (doc 11 §17): the build proves borrower/transaction data → underwriting decisions, fraud controls, expected-loss estimates, model-risk validation evidence — and only that story.
- [ ] **Step 4: Commit** — `git commit -m "feat: complete frontend build, QA verified"`

---

## Self-Review

**Spec coverage:** design gating §9 ✓ P10 (capability check + token approval); stack §8 ✓ 11.1; 10 sections §8/doc 09 §3 ✓ 11.3–11.12 each bound to its data source; no-hardcoded-numbers ✓ 11.3–11.12 + 12.1 traceability scan; interactions limited §8/doc 09 §14 ✓ 11.5/11.6; copy rules ✓ 12.1; forbidden fonts/colors/UI ✓ 10.2 + 12.1; README absence ✓ 12.1; reconciliation precondition ✓ header. 
**Placeholder scan:** design-token specifics are intentionally produced by the mandatory skills at execution time behind a user-approval gate (Task 10.2) — this is a required process gate, not a vague placeholder; every section task names exact data sources and required fields.
**Type consistency:** `lib/load.ts`/`lib/types.ts` are the single typed interface to outputs; section tasks consume them; `scripts/sync-data.mjs` + `public/data/outputs` referenced consistently; QA scans in 12.1 reuse backend `reconcile`.
**Dependency note:** Plan 2 starts only after Plan 1's reconciliation gates pass; Task 10.2 is a hard user-approval checkpoint before any UI code.
