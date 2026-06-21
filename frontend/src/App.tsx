import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Database,
  FileText,
  Gauge,
  Landmark,
  ListFilter,
  LockKeyhole,
  Scale,
  ShieldAlert,
  SlidersHorizontal,
  TableProperties,
  WalletCards,
} from "lucide-react";

const OUTPUT_ROOT = "/data/outputs/";

type Row = Record<string, string | number>;
type JsonObject = Record<string, unknown>;

type Outputs = {
  command: JsonObject;
  underwriting: JsonObject;
  underwritingSummary: JsonObject;
  fraud: JsonObject;
  fraudSummary: JsonObject;
  stablecoin: JsonObject;
  expectedLoss: JsonObject;
  expectedLossSegments: JsonObject;
  stress: JsonObject;
  policyInputs: JsonObject;
  policyResults: JsonObject;
  validation: JsonObject;
  challenger: JsonObject;
  verdicts: JsonObject;
  methodology: JsonObject;
  underwritingRows: Row[];
  fraudRows: Row[];
  stablecoinRows: Row[];
  applicantLossRows: Row[];
  qualityRows: Row[];
};

type PolicyState = {
  approvalCutoff: number;
  reviewBand: number;
  fraudThreshold: number;
  stablecoinThreshold: number;
  manualCapacity: number;
  stressScenario: string;
};

type PolicyMetrics = {
  approvalRate: number;
  reviewRate: number;
  declineRate: number;
  approvedExposure: number;
  expectedCreditLoss: number;
  expectedFraudLoss: number;
  stablecoinRiskExposure: number;
  totalExpectedLoss: number;
  lossRate: number;
  manualReviewVolume: number;
  blockedTransactionRate: number;
  warnings: string[];
};

const sectionLinks = [
  ["overview", "Overview", Landmark],
  ["command", "Command", Gauge],
  ["underwriting", "Underwriting", Scale],
  ["policy", "Policy", SlidersHorizontal],
  ["fraud", "Fraud", ShieldAlert],
  ["stablecoin", "Stablecoin", WalletCards],
  ["loss", "Loss", BarChart3],
  ["validation", "Validation", CheckCircle2],
  ["stress", "Stress", Activity],
  ["evidence", "Evidence", FileText],
] as const;

function numberValue(value: unknown): number {
  if (typeof value === "number") return Number.isFinite(value) ? value : 0;
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function textValue(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number") return String(value);
  return "";
}

function getObject<T = JsonObject>(source: unknown, key: string, fallback: T): T {
  if (!source || typeof source !== "object") return fallback;
  const value = (source as JsonObject)[key];
  return (value ?? fallback) as T;
}

function getArray<T = JsonObject>(source: unknown, key: string): T[] {
  const value = getObject<unknown>(source, key, []);
  return Array.isArray(value) ? (value as T[]) : [];
}

function formatNumber(value: unknown, digits = 0): string {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(numberValue(value));
}

function formatMoney(value: unknown): string {
  const n = numberValue(value);
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${formatNumber(n, 0)}`;
}

function formatPercent(value: unknown, digits = 1): string {
  return `${(numberValue(value) * 100).toFixed(digits)}%`;
}

async function fetchJson<T>(file: string): Promise<T> {
  const response = await fetch(`${OUTPUT_ROOT}${file}`);
  if (!response.ok) throw new Error(`Unable to load ${file}`);
  return response.json();
}

function parseCsvLine(line: string): string[] {
  const result: string[] = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    const next = line[i + 1];
    if (char === '"' && inQuotes && next === '"') {
      current += '"';
      i += 1;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      result.push(current);
      current = "";
    } else {
      current += char;
    }
  }
  result.push(current);
  return result;
}

function coerceCell(value: string): string | number {
  const trimmed = value.trim();
  if (trimmed === "") return "";
  if (/^-?\d+(\.\d+)?$/.test(trimmed)) return Number(trimmed);
  return trimmed;
}

async function fetchCsv(file: string): Promise<Row[]> {
  const response = await fetch(`${OUTPUT_ROOT}${file}`);
  if (!response.ok) throw new Error(`Unable to load ${file}`);
  const text = await response.text();
  const lines = text.trim().split(/\r?\n/);
  const headers = parseCsvLine(lines[0]);
  return lines.slice(1).map((line) => {
    const cells = parseCsvLine(line);
    return headers.reduce<Row>((row, header, index) => {
      row[header] = coerceCell(cells[index] ?? "");
      return row;
    }, {});
  });
}

function sourceName(file: string): string {
  return `data/outputs/${file}`;
}

function calculatePolicy(outputs: Outputs, policy: PolicyState): PolicyMetrics {
  const stressControls = getObject<JsonObject>(getObject(outputs.policyInputs, "controls", {}), "stress_controls", {});
  const chosenStress = getObject<JsonObject>(stressControls, policy.stressScenario, {});
  const pdMultiplier = numberValue(chosenStress.PD_multiplier || 1);
  const lgdMultiplier = numberValue(chosenStress.LGD_multiplier || 1);
  const fraudMultiplier = numberValue(chosenStress.fraud_loss_multiplier || 1);
  const stableMultiplier = numberValue(chosenStress.stablecoin_risk_multiplier || 1);
  const declineCutoff = Math.min(policy.approvalCutoff + policy.reviewBand, 0.99);

  let approvals = 0;
  let reviews = 0;
  let declines = 0;
  let exposure = 0;
  let creditLoss = 0;

  outputs.underwritingRows.forEach((row) => {
    const pd = Math.min(numberValue(row.PD) * pdMultiplier, 1);
    const lgd = Math.min(numberValue(row.LGD) * lgdMultiplier, 1);
    const loanAmount = numberValue(row.loan_amount);
    if (pd < policy.approvalCutoff) {
      approvals += 1;
      exposure += loanAmount;
      creditLoss += pd * lgd * loanAmount;
    } else if (pd < declineCutoff) {
      reviews += 1;
      exposure += loanAmount;
      creditLoss += pd * lgd * loanAmount;
    } else {
      declines += 1;
    }
  });

  let fraudFlagged = 0;
  let fraudLoss = 0;
  let blocked = 0;
  outputs.fraudRows.forEach((row) => {
    const score = numberValue(row.fraud_score);
    if (score >= policy.fraudThreshold) {
      fraudFlagged += 1;
    } else {
      fraudLoss += numberValue(row.expected_fraud_loss) * fraudMultiplier;
    }
    if (score >= 0.8) blocked += 1;
  });

  let stableExposure = 0;
  outputs.stablecoinRows.forEach((row) => {
    if (numberValue(row.stablecoin_risk_score) >= policy.stablecoinThreshold) {
      stableExposure += numberValue(row.stablecoin_risk_exposure) * stableMultiplier;
    }
  });

  const verdicts = getArray<JsonObject>(outputs.verdicts, "verdicts");
  const warnings: string[] = [];
  const manualVolume = reviews + fraudFlagged;
  if (manualVolume > policy.manualCapacity) {
    const over = (manualVolume - policy.manualCapacity) / Math.max(policy.manualCapacity, 1);
    warnings.push(`Manual review volume exceeds capacity by ${(over * 100).toFixed(0)}%.`);
  }
  const watchModels = verdicts
    .filter((item) => ["Monitor", "Fail"].includes(textValue(item.validation_verdict)))
    .map((item) => textValue(item.model_name));
  if (watchModels.length > 0) {
    warnings.push(`Model validation verdict requires monitoring for ${watchModels.join(", ")}.`);
  }
  const totalStable = outputs.stablecoinRows.reduce((sum, row) => sum + numberValue(row.stablecoin_risk_exposure), 0);
  if (stableExposure > totalStable * 0.5) warnings.push("Stablecoin high-risk exposure exceeds 50% of proxy exposure.");

  return {
    approvalRate: approvals / outputs.underwritingRows.length,
    reviewRate: reviews / outputs.underwritingRows.length,
    declineRate: declines / outputs.underwritingRows.length,
    approvedExposure: exposure,
    expectedCreditLoss: creditLoss,
    expectedFraudLoss: fraudLoss,
    stablecoinRiskExposure: stableExposure,
    totalExpectedLoss: creditLoss + fraudLoss + stableExposure,
    lossRate: exposure > 0 ? creditLoss / exposure : 0,
    manualReviewVolume: manualVolume,
    blockedTransactionRate: blocked / outputs.fraudRows.length,
    warnings,
  };
}

function DataSource({ files }: { files: string[] }) {
  return (
    <div className="source-line">
      <Database size={13} />
      {files.map(sourceName).join(" | ")}
    </div>
  );
}

function MetricCell({ label, value, source }: { label: string; value: string; source?: string }) {
  return (
    <motion.div className="metric-cell" layout>
      <span>{label}</span>
      <strong>{value}</strong>
      {source ? <small>{sourceName(source)}</small> : null}
    </motion.div>
  );
}

function Section({
  id,
  title,
  icon: Icon,
  source,
  children,
}: {
  id: string;
  title: string;
  icon: typeof Gauge;
  source: string[];
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="section-band">
      <div className="section-heading">
        <div>
          <span className="section-kicker">
            <Icon size={15} />
            {title}
          </span>
        </div>
        <DataSource files={source} />
      </div>
      {children}
    </section>
  );
}

function BarList({
  rows,
  labelKey,
  valueKey,
  valueFormat = "number",
}: {
  rows: JsonObject[];
  labelKey: string;
  valueKey: string;
  valueFormat?: "number" | "money" | "percent";
}) {
  const max = Math.max(...rows.map((row) => numberValue(row[valueKey])), 1);
  const format = valueFormat === "money" ? formatMoney : valueFormat === "percent" ? formatPercent : formatNumber;
  return (
    <div className="bar-list">
      {rows.map((row, index) => {
        const value = numberValue(row[valueKey]);
        return (
          <div className="bar-row" key={`${textValue(row[labelKey])}-${index}`}>
            <span>{textValue(row[labelKey])}</span>
            <div className="bar-track" aria-hidden="true">
              <div style={{ width: `${Math.max(2, (value / max) * 100)}%` }} />
            </div>
            <strong>{format(value)}</strong>
          </div>
        );
      })}
    </div>
  );
}

function Table({
  rows,
  columns,
  onSelect,
  selectedId,
  idKey,
}: {
  rows: Row[];
  columns: [string, string, (value: unknown, row: Row) => string][];
  onSelect?: (row: Row) => void;
  selectedId?: string;
  idKey: string;
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map(([key, label]) => (
              <th key={key}>{label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const id = textValue(row[idKey]);
            return (
              <tr
                key={id}
                className={selectedId === id ? "selected" : ""}
                onClick={() => onSelect?.(row)}
              >
                {columns.map(([key, , formatter]) => (
                  <td key={key}>{formatter(row[key], row)}</td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function VerdictMark({ verdict }: { verdict: string }) {
  return <span className={`verdict verdict-${verdict.toLowerCase()}`}>{verdict}</span>;
}

function App() {
  const [outputs, setOutputs] = useState<Outputs | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedApplicant, setSelectedApplicant] = useState<Row | null>(null);
  const [selectedTransaction, setSelectedTransaction] = useState<Row | null>(null);
  const [selectedWallet, setSelectedWallet] = useState<Row | null>(null);
  const [policy, setPolicy] = useState<PolicyState>({
    approvalCutoff: 0.06,
    reviewBand: 0.06,
    fraudThreshold: 0.6,
    stablecoinThreshold: 0.65,
    manualCapacity: 420,
    stressScenario: "Base",
  });

  useEffect(() => {
    Promise.all([
      fetchJson<JsonObject>("risk_command_center.json"),
      fetchJson<JsonObject>("underwriting_decisions.json"),
      fetchJson<JsonObject>("underwriting_policy_summary.json"),
      fetchJson<JsonObject>("fraud_alerts.json"),
      fetchJson<JsonObject>("fraud_policy_summary.json"),
      fetchJson<JsonObject>("stablecoin_alerts.json"),
      fetchJson<JsonObject>("expected_loss_summary.json"),
      fetchJson<JsonObject>("expected_loss_by_segment.json"),
      fetchJson<JsonObject>("stress_loss_summary.json"),
      fetchJson<JsonObject>("policy_simulator_inputs.json"),
      fetchJson<JsonObject>("policy_simulator_results.json"),
      fetchJson<JsonObject>("model_validation_summary.json"),
      fetchJson<JsonObject>("champion_challenger_comparison.json"),
      fetchJson<JsonObject>("model_risk_verdicts.json"),
      fetchJson<JsonObject>("methodology_summary.json"),
      fetchCsv("underwriting_decisions.csv"),
      fetchCsv("fraud_alerts.csv"),
      fetchCsv("stablecoin_alerts.csv"),
      fetchCsv("expected_loss_applicant_level.csv"),
      fetchCsv("data_quality_report.csv"),
    ])
      .then(
        ([
          command,
          underwriting,
          underwritingSummary,
          fraud,
          fraudSummary,
          stablecoin,
          expectedLoss,
          expectedLossSegments,
          stress,
          policyInputs,
          policyResults,
          validation,
          challenger,
          verdicts,
          methodology,
          underwritingRows,
          fraudRows,
          stablecoinRows,
          applicantLossRows,
          qualityRows,
        ]) => {
          setOutputs({
            command,
            underwriting,
            underwritingSummary,
            fraud,
            fraudSummary,
            stablecoin,
            expectedLoss,
            expectedLossSegments,
            stress,
            policyInputs,
            policyResults,
            validation,
            challenger,
            verdicts,
            methodology,
            underwritingRows,
            fraudRows,
            stablecoinRows,
            applicantLossRows,
            qualityRows,
          });
          setSelectedApplicant(underwritingRows[0] ?? null);
          setSelectedTransaction(fraudRows[0] ?? null);
          setSelectedWallet(stablecoinRows[0] ?? null);
        }
      )
      .catch((err: Error) => setError(err.message));
  }, []);

  const policyMetrics = useMemo(() => (outputs ? calculatePolicy(outputs, policy) : null), [outputs, policy]);

  if (error) {
    return (
      <main className="shell">
        <div className="load-state">
          <AlertTriangle />
          <p>{error}</p>
        </div>
      </main>
    );
  }

  if (!outputs || !policyMetrics) {
    return (
      <main className="shell">
        <div className="load-state">
          <Activity />
          <p>Loading risk outputs from data/outputs.</p>
        </div>
      </main>
    );
  }

  const command = outputs.command;
  const underwritingCharts = getObject<JsonObject>(outputs.underwritingSummary, "charts", {});
  const fraudMetrics = getObject<JsonObject>(outputs.fraudSummary, "metrics", {});
  const stableSummary = getObject<JsonObject>(outputs.stablecoin, "summary", {});
  const expectedPortfolio = getObject<JsonObject>(outputs.expectedLoss, "portfolio", {});
  const validationCredit = getObject<JsonObject>(outputs.validation, "credit_model_metrics", {});
  const validationFraud = getObject<JsonObject>(outputs.validation, "fraud_model_metrics", {});
  const methodology = outputs.methodology;
  const verdictRows = getArray<JsonObject>(outputs.verdicts, "verdicts");
  const stressRows = getArray<JsonObject>(outputs.stress, "scenarios");
  const applicantRows = [...outputs.underwritingRows].sort((a, b) => numberValue(b.PD) - numberValue(a.PD)).slice(0, 14);
  const fraudRows = [...outputs.fraudRows].sort((a, b) => numberValue(b.fraud_score) - numberValue(a.fraud_score)).slice(0, 14);
  const walletRows = [...outputs.stablecoinRows].sort((a, b) => numberValue(b.stablecoin_risk_score) - numberValue(a.stablecoin_risk_score)).slice(0, 12);

  return (
    <main className="shell">
      <nav className="module-tabs" aria-label="Module navigation">
        {sectionLinks.map(([id, label, Icon]) => (
          <a href={`#${id}`} key={id} title={label}>
            <Icon size={16} />
            <span>{label}</span>
          </a>
        ))}
      </nav>

      <section id="overview" className="hero-band">
        <div className="hero-copy">
          <span className="section-kicker">
            <LockKeyhole size={15} />
            Decision Evidence Terminal
          </span>
          <h1>Credit & Payments Risk Decision Engine</h1>
          <p className="subtitle">Underwriting Strategy · Fraud Monitoring · Expected Loss · Model Risk</p>
          <p className="thesis">
            Borrower and transaction data flow into underwriting decisions, fraud controls, expected-loss estimates,
            and model-risk validation evidence.
          </p>
          <div className="module-strip">
            {["Underwriting", "Fraud Controls", "Expected Loss", "Model Validation"].map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
          <DataSource files={["risk_command_center.json", "methodology_summary.json"]} />
        </div>
        <div className="hero-ledger">
          <MetricCell label="Applicants" value={formatNumber(command.total_applicants)} source="risk_command_center.json" />
          <MetricCell label="Approval Rate" value={formatPercent(command.approval_rate)} source="risk_command_center.json" />
          <MetricCell label="Expected Credit Loss" value={formatMoney(command.total_expected_credit_loss)} source="risk_command_center.json" />
          <MetricCell label="Manual Review Volume" value={formatNumber(command.manual_review_volume)} source="risk_command_center.json" />
        </div>
        <p className="disclosure">{textValue(methodology.synthetic_data_disclosure)}</p>
      </section>

      <Section id="command" title="Risk Command Center" icon={Gauge} source={["risk_command_center.json"]}>
        <div className="metric-grid dense">
          <MetricCell label="Total Applicants" value={formatNumber(command.total_applicants)} source="risk_command_center.json" />
          <MetricCell label="Review Rate" value={formatPercent(command.review_rate)} source="risk_command_center.json" />
          <MetricCell label="Decline Rate" value={formatPercent(command.decline_rate)} source="risk_command_center.json" />
          <MetricCell label="Average PD" value={formatPercent(command.average_PD)} source="risk_command_center.json" />
          <MetricCell label="Approved Exposure" value={formatMoney(command.total_approved_exposure)} source="risk_command_center.json" />
          <MetricCell label="Expected Fraud Loss" value={formatMoney(command.total_expected_fraud_loss)} source="risk_command_center.json" />
          <MetricCell label="Stablecoin Risk Exposure" value={formatMoney(command.stablecoin_risk_exposure)} source="risk_command_center.json" />
          <MetricCell label="Model Verdicts" value={Object.entries(getObject<JsonObject>(command, "model_verdict_summary", {})).map(([k, v]) => `${k} ${v}`).join(" / ")} source="risk_command_center.json" />
        </div>
        <div className="split-grid">
          <div className="panel-flat">
            <h3>Decision Mix</h3>
            <BarList rows={getArray<JsonObject>(underwritingCharts, "approval_review_decline_mix")} labelKey="decision" valueKey="applicant_share" valueFormat="percent" />
          </div>
          <div className="panel-flat">
            <h3>Highest Risk Segment</h3>
            <dl className="definition-list">
              {Object.entries(getObject<JsonObject>(command, "highest_risk_segment", {})).map(([key, value]) => (
                <div key={key}>
                  <dt>{key.replaceAll("_", " ")}</dt>
                  <dd>{key.includes("rate") ? formatPercent(value) : textValue(value)}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </Section>

      <Section id="underwriting" title="Underwriting Decision Engine" icon={Scale} source={["underwriting_decisions.csv", "underwriting_policy_summary.json"]}>
        <div className="analytics-grid">
          <div className="panel-flat">
            <h3>PD Distribution</h3>
            <BarList rows={getArray<JsonObject>(underwritingCharts, "PD_distribution")} labelKey="label" valueKey="count" />
          </div>
          <div className="panel-flat">
            <h3>Risk Grade Distribution</h3>
            <BarList rows={getArray<JsonObject>(underwritingCharts, "risk_grade_distribution")} labelKey="label" valueKey="count" />
          </div>
          <div className="panel-flat">
            <h3>Expected Loss By Risk Grade</h3>
            <BarList rows={getArray<JsonObject>(underwritingCharts, "expected_loss_by_risk_grade")} labelKey="risk_grade" valueKey="expected_loss" valueFormat="money" />
          </div>
        </div>
        <div className="data-detail-grid">
          <Table
            rows={applicantRows}
            idKey="applicant_id"
            selectedId={textValue(selectedApplicant?.applicant_id)}
            onSelect={setSelectedApplicant}
            columns={[
              ["applicant_id", "Applicant", (value) => textValue(value)],
              ["PD", "PD", (value) => formatPercent(value)],
              ["risk_grade", "Grade", (value) => textValue(value)],
              ["decision", "Decision", (value) => textValue(value)],
              ["recommended_credit_limit", "Limit", (value) => formatMoney(value)],
              ["expected_loss", "Expected Loss", (value) => formatMoney(value)],
            ]}
          />
          <motion.div className="selection-panel" key={textValue(selectedApplicant?.applicant_id)} initial={{ opacity: 0.6 }} animate={{ opacity: 1 }}>
            <h3>Selected Applicant</h3>
            <p className="large-id">{textValue(selectedApplicant?.applicant_id)}</p>
            <dl className="definition-list">
              <div><dt>Decision</dt><dd>{textValue(selectedApplicant?.decision)}</dd></div>
              <div><dt>Modeled Probability</dt><dd>{formatPercent(selectedApplicant?.PD)}</dd></div>
              <div><dt>LGD / EAD</dt><dd>{formatPercent(selectedApplicant?.LGD)} / {formatMoney(selectedApplicant?.EAD)}</dd></div>
              <div><dt>Reason Codes</dt><dd>{[selectedApplicant?.top_reason_1, selectedApplicant?.top_reason_2, selectedApplicant?.top_reason_3].map(textValue).filter(Boolean).join(" | ")}</dd></div>
            </dl>
          </motion.div>
        </div>
      </Section>

      <Section id="policy" title="Policy Simulator" icon={SlidersHorizontal} source={["underwriting_decisions.csv", "fraud_alerts.csv", "stablecoin_alerts.csv", "policy_simulator_inputs.json"]}>
        <div className="policy-grid">
          <div className="control-panel">
            <label>
              Approval PD cutoff <strong>{formatPercent(policy.approvalCutoff)}</strong>
              <input type="range" min="0.03" max="0.12" step="0.01" value={policy.approvalCutoff} onChange={(event) => setPolicy({ ...policy, approvalCutoff: Number(event.target.value) })} />
            </label>
            <label>
              Review band <strong>{formatPercent(policy.reviewBand)}</strong>
              <input type="range" min="0.03" max="0.10" step="0.01" value={policy.reviewBand} onChange={(event) => setPolicy({ ...policy, reviewBand: Number(event.target.value) })} />
            </label>
            <label>
              Fraud threshold <strong>{formatPercent(policy.fraudThreshold, 0)}</strong>
              <input type="range" min="0.25" max="0.85" step="0.05" value={policy.fraudThreshold} onChange={(event) => setPolicy({ ...policy, fraudThreshold: Number(event.target.value) })} />
            </label>
            <label>
              Stablecoin risk threshold <strong>{formatPercent(policy.stablecoinThreshold, 0)}</strong>
              <input type="range" min="0.35" max="0.9" step="0.05" value={policy.stablecoinThreshold} onChange={(event) => setPolicy({ ...policy, stablecoinThreshold: Number(event.target.value) })} />
            </label>
            <label>
              Manual-review capacity <strong>{formatNumber(policy.manualCapacity)}</strong>
              <input type="range" min="120" max="1800" step="60" value={policy.manualCapacity} onChange={(event) => setPolicy({ ...policy, manualCapacity: Number(event.target.value) })} />
            </label>
            <label>
              Stress scenario
              <select value={policy.stressScenario} onChange={(event) => setPolicy({ ...policy, stressScenario: event.target.value })}>
                {stressRows.map((row) => <option key={textValue(row.scenario)}>{textValue(row.scenario)}</option>)}
              </select>
            </label>
          </div>
          <motion.div className="sim-output" key={`${policy.approvalCutoff}-${policy.reviewBand}-${policy.fraudThreshold}-${policy.stablecoinThreshold}-${policy.stressScenario}`} initial={{ opacity: 0.7 }} animate={{ opacity: 1 }}>
            <div className="metric-grid compact">
              <MetricCell label="Approval Rate" value={formatPercent(policyMetrics.approvalRate)} />
              <MetricCell label="Decline Rate" value={formatPercent(policyMetrics.declineRate)} />
              <MetricCell label="Expected Credit Loss" value={formatMoney(policyMetrics.expectedCreditLoss)} />
              <MetricCell label="Expected Fraud Loss" value={formatMoney(policyMetrics.expectedFraudLoss)} />
              <MetricCell label="Stablecoin Risk Exposure" value={formatMoney(policyMetrics.stablecoinRiskExposure)} />
              <MetricCell label="Manual Review Volume" value={formatNumber(policyMetrics.manualReviewVolume)} />
              <MetricCell label="Total Expected Loss" value={formatMoney(policyMetrics.totalExpectedLoss)} />
              <MetricCell label="Loss Rate" value={formatPercent(policyMetrics.lossRate)} />
            </div>
            <div className="warning-stack">
              {policyMetrics.warnings.map((warning) => (
                <p key={warning}><AlertTriangle size={14} />{warning}</p>
              ))}
            </div>
          </motion.div>
        </div>
      </Section>

      <Section id="fraud" title="Fraud & Payments Monitor" icon={ShieldAlert} source={["fraud_alerts.csv", "fraud_policy_summary.json"]}>
        <div className="metric-grid dense">
          <MetricCell label="PR-AUC" value={formatPercent(fraudMetrics.PR_AUC)} source="fraud_policy_summary.json" />
          <MetricCell label="Fraud Capture Rate" value={formatPercent(fraudMetrics.fraud_capture_rate)} source="fraud_policy_summary.json" />
          <MetricCell label="False Positive Rate" value={formatPercent(fraudMetrics.false_positive_rate)} source="fraud_policy_summary.json" />
          <MetricCell label="Manual Review Volume" value={formatNumber(fraudMetrics.manual_review_volume)} source="fraud_policy_summary.json" />
        </div>
        <div className="analytics-grid">
          <div className="panel-flat">
            <h3>Payment Action Mix</h3>
            <BarList rows={getArray<JsonObject>(outputs.fraudSummary, "payment_action_mix")} labelKey="payment_action" valueKey="transaction_share" valueFormat="percent" />
          </div>
          <div className="panel-flat">
            <h3>Expected Fraud Loss By Action</h3>
            <BarList rows={getArray<JsonObject>(outputs.fraudSummary, "expected_fraud_loss_by_action")} labelKey="payment_action" valueKey="expected_fraud_loss" valueFormat="money" />
          </div>
          <div className="panel-flat">
            <h3>Top Fraud Drivers</h3>
            <BarList rows={getArray<JsonObject>(outputs.fraudSummary, "top_fraud_drivers").slice(0, 7)} labelKey="reason_code" valueKey="count" />
          </div>
        </div>
        <div className="data-detail-grid">
          <Table
            rows={fraudRows}
            idKey="transaction_id"
            selectedId={textValue(selectedTransaction?.transaction_id)}
            onSelect={setSelectedTransaction}
            columns={[
              ["transaction_id", "Transaction", (value) => textValue(value)],
              ["fraud_score", "Score", (value) => formatPercent(value)],
              ["anomaly_score", "Anomaly", (value) => formatPercent(value)],
              ["payment_action", "Action", (value) => textValue(value)],
              ["amount", "Amount", (value) => formatMoney(value)],
              ["expected_fraud_loss", "Expected Loss", (value) => formatMoney(value)],
            ]}
          />
          <motion.div className="selection-panel" key={textValue(selectedTransaction?.transaction_id)} initial={{ opacity: 0.6 }} animate={{ opacity: 1 }}>
            <h3>Selected Transaction</h3>
            <p className="large-id">{textValue(selectedTransaction?.transaction_id)}</p>
            <dl className="definition-list">
              <div><dt>Payment Action</dt><dd>{textValue(selectedTransaction?.payment_action)}</dd></div>
              <div><dt>Manual Review Priority</dt><dd>{formatNumber(selectedTransaction?.manual_review_priority)}</dd></div>
              <div><dt>Risk Drivers</dt><dd>{[selectedTransaction?.top_reason_1, selectedTransaction?.top_reason_2, selectedTransaction?.top_reason_3].map(textValue).filter(Boolean).join(" | ")}</dd></div>
            </dl>
          </motion.div>
        </div>
      </Section>

      <Section id="stablecoin" title="Stablecoin Risk Monitor" icon={WalletCards} source={["stablecoin_alerts.csv", "stablecoin_alerts.json"]}>
        <p className="module-note">Stablecoin payments-risk monitoring uses AML-style risk indicators.</p>
        <div className="analytics-grid">
          <div className="panel-flat">
            <h3>Stablecoin Action Mix</h3>
            <BarList rows={getArray<JsonObject>(stableSummary, "stablecoin_action_mix")} labelKey="stablecoin_risk_action" valueKey="transaction_share" valueFormat="percent" />
          </div>
          <div className="panel-flat">
            <h3>Risk Exposure By Action</h3>
            <BarList rows={getArray<JsonObject>(stableSummary, "risk_exposure_by_action")} labelKey="stablecoin_risk_action" valueKey="risk_exposure" valueFormat="money" />
          </div>
          <div className="panel-flat">
            <h3>Wallet-Risk Drivers</h3>
            <BarList rows={getArray<JsonObject>(stableSummary, "top_wallet_risk_drivers").slice(0, 7)} labelKey="reason_code" valueKey="count" />
          </div>
        </div>
        <div className="data-detail-grid">
          <Table
            rows={walletRows}
            idKey="wallet_id"
            selectedId={textValue(selectedWallet?.wallet_id)}
            onSelect={setSelectedWallet}
            columns={[
              ["wallet_id", "Wallet", (value) => textValue(value)],
              ["counterparty_wallet_id", "Counterparty", (value) => textValue(value)],
              ["stablecoin_risk_score", "Score", (value) => formatPercent(value)],
              ["stablecoin_risk_action", "Action", (value) => textValue(value)],
              ["amount_usd", "Amount", (value) => formatMoney(value)],
              ["stablecoin_risk_exposure", "Exposure", (value) => formatMoney(value)],
            ]}
          />
          <motion.div className="selection-panel" key={textValue(selectedWallet?.wallet_id)} initial={{ opacity: 0.6 }} animate={{ opacity: 1 }}>
            <h3>Selected Wallet Flow</h3>
            <p className="large-id">{textValue(selectedWallet?.wallet_id)}</p>
            <dl className="definition-list">
              <div><dt>Risk Action</dt><dd>{textValue(selectedWallet?.stablecoin_risk_action)}</dd></div>
              <div><dt>Counterparty</dt><dd>{textValue(selectedWallet?.counterparty_wallet_id)}</dd></div>
              <div><dt>Risk Drivers</dt><dd>{[selectedWallet?.top_reason_1, selectedWallet?.top_reason_2, selectedWallet?.top_reason_3].map(textValue).filter(Boolean).join(" | ")}</dd></div>
            </dl>
          </motion.div>
        </div>
      </Section>

      <Section id="loss" title="Expected Loss Engine" icon={BarChart3} source={["expected_loss_summary.json", "expected_loss_by_segment.json", "expected_loss_applicant_level.csv"]}>
        <div className="formula-line">Expected Loss = PD × LGD × EAD</div>
        <div className="metric-grid dense">
          <MetricCell label="Base Expected Loss" value={formatMoney(expectedPortfolio.base_expected_loss)} source="expected_loss_summary.json" />
          <MetricCell label="Expected Credit Loss" value={formatMoney(expectedPortfolio.expected_credit_loss)} source="expected_loss_summary.json" />
          <MetricCell label="Expected Fraud Loss" value={formatMoney(expectedPortfolio.expected_fraud_loss)} source="expected_loss_summary.json" />
          <MetricCell label="Stablecoin Risk Exposure" value={formatMoney(expectedPortfolio.stablecoin_risk_exposure)} source="expected_loss_summary.json" />
        </div>
        <div className="analytics-grid">
          <div className="panel-flat">
            <h3>Expected Loss By Decision</h3>
            <BarList rows={getArray<JsonObject>(outputs.expectedLoss, "expected_loss_by_decision")} labelKey="segment_value" valueKey="total_expected_loss" valueFormat="money" />
          </div>
          <div className="panel-flat">
            <h3>Loss Waterfall</h3>
            <BarList rows={getArray<JsonObject>(outputs.expectedLoss, "expected_loss_waterfall")} labelKey="component" valueKey="amount" valueFormat="money" />
          </div>
          <div className="panel-flat">
            <h3>Fraud Loss By Payment Action</h3>
            <BarList rows={getArray<JsonObject>(outputs.expectedLoss, "fraud_loss_by_payment_action")} labelKey="segment_value" valueKey="total_expected_loss" valueFormat="money" />
          </div>
        </div>
      </Section>

      <Section id="validation" title="Model Risk & Validation" icon={CheckCircle2} source={["model_validation_summary.json", "champion_challenger_comparison.json", "model_risk_verdicts.json"]}>
        <div className="metric-grid dense">
          <MetricCell label="Credit ROC-AUC" value={formatPercent(validationCredit.ROC_AUC)} source="model_validation_summary.json" />
          <MetricCell label="Credit PR-AUC" value={formatPercent(validationCredit.PR_AUC)} source="model_validation_summary.json" />
          <MetricCell label="Brier Score" value={formatNumber(validationCredit.Brier_score, 4)} source="model_validation_summary.json" />
          <MetricCell label="Fraud PR-AUC" value={formatPercent(validationFraud.PR_AUC)} source="model_validation_summary.json" />
        </div>
        <div className="split-grid">
          <div className="panel-flat">
            <h3>PD Decile Default Table</h3>
            <BarList rows={getArray<JsonObject>(validationCredit, "decile_default_table")} labelKey="bin" valueKey="actual_default_rate" valueFormat="percent" />
          </div>
          <div className="panel-flat">
            <h3>Model Verdict Panel</h3>
            <div className="verdict-list">
              {verdictRows.map((row) => (
                <div key={textValue(row.model_name)}>
                  <span>{textValue(row.model_name)}</span>
                  <VerdictMark verdict={textValue(row.validation_verdict)} />
                  <p>{textValue(row.verdict_reason)}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Section>

      <Section id="stress" title="Stress Testing" icon={Activity} source={["stress_loss_summary.json"]}>
        <div className="analytics-grid">
          <div className="panel-flat wide">
            <h3>Base Vs Stressed Loss</h3>
            <BarList rows={stressRows} labelKey="scenario" valueKey="total_expected_loss" valueFormat="money" />
          </div>
          <div className="panel-flat">
            <h3>Stress Multipliers</h3>
            <div className="mini-table">
              {stressRows.map((row) => (
                <div key={textValue(row.scenario)}>
                  <span>{textValue(row.scenario)}</span>
                  <strong>PD {formatNumber(row.PD_multiplier, 2)} | LGD {formatNumber(row.LGD_multiplier, 2)} | Fraud {formatNumber(row.fraud_loss_multiplier, 2)}</strong>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Section>

      <Section id="evidence" title="Evidence & Methodology" icon={FileText} source={["methodology_summary.json", "data_quality_report.csv"]}>
        <div className="split-grid">
          <div className="panel-flat">
            <h3>Data Quality</h3>
            <Table
              rows={outputs.qualityRows}
              idKey="dataset_name"
              columns={[
                ["dataset_name", "Dataset", (value) => textValue(value)],
                ["row_count", "Rows", (value) => formatNumber(value)],
                ["target_rate", "Target Rate", (value) => (value === "" ? "" : formatPercent(value))],
                ["leakage_check_status", "Leakage", (value) => textValue(value)],
                ["schema_check_status", "Schema", (value) => textValue(value)],
              ]}
            />
          </div>
          <div className="panel-flat">
            <h3>Methodology Disclosure</h3>
            <dl className="definition-list evidence">
              <div><dt>Split Method</dt><dd>{textValue(methodology.split_method)}</dd></div>
              <div><dt>Known Limitations</dt><dd>{getArray<string>(methodology, "known_limitations").join(" | ")}</dd></div>
              <div><dt>Model List</dt><dd>{getArray<string>(methodology, "model_list").join(" | ")}</dd></div>
            </dl>
          </div>
        </div>
      </Section>
    </main>
  );
}

export default App;
