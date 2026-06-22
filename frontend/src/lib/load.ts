import Papa from "papaparse";

// Single typed gateway to the backend outputs synced into public/data/outputs.
// Every section is a pure function of this bundle; no metric is inlined in TSX.

const BASE = import.meta.env.BASE_URL;

async function getJson<T = any>(name: string): Promise<T> {
  const res = await fetch(`${BASE}data/outputs/${name}`);
  if (!res.ok) throw new Error(`load ${name}: ${res.status}`);
  return (await res.json()) as T;
}

async function getCsv<T = Record<string, any>>(name: string): Promise<T[]> {
  const res = await fetch(`${BASE}data/outputs/${name}`);
  if (!res.ok) throw new Error(`load ${name}: ${res.status}`);
  const text = await res.text();
  const out = Papa.parse<T>(text, { header: true, dynamicTyping: true, skipEmptyLines: true });
  return out.data;
}

export interface Bundle {
  commandCenter: any;
  underwritingDecisions: any;
  underwritingPolicy: any;
  fraudAlerts: any;
  fraudPolicy: any;
  stablecoinAlerts: any;
  expectedLossSummary: any;
  expectedLossSegment: any;
  stressLoss: any;
  policyLoss: any;
  simulatorInputs: any;
  simulatorResults: any;
  validationSummary: any;
  championChallenger: any;
  verdicts: any;
  methodology: any;
  dataQuality: any[];
}

export async function loadAll(): Promise<Bundle> {
  const [
    commandCenter, underwritingDecisions, underwritingPolicy, fraudAlerts, fraudPolicy,
    stablecoinAlerts, expectedLossSummary, expectedLossSegment, stressLoss, policyLoss,
    simulatorInputs, simulatorResults, validationSummary, championChallenger, verdicts,
    methodology, dataQuality,
  ] = await Promise.all([
    getJson("risk_command_center.json"),
    getJson("underwriting_decisions.json"),
    getJson("underwriting_policy_summary.json"),
    getJson("fraud_alerts.json"),
    getJson("fraud_policy_summary.json"),
    getJson("stablecoin_alerts.json"),
    getJson("expected_loss_summary.json"),
    getJson("expected_loss_by_segment.json"),
    getJson("stress_loss_summary.json"),
    getJson("policy_loss_comparison.json"),
    getJson("policy_simulator_inputs.json"),
    getJson("policy_simulator_results.json"),
    getJson("model_validation_summary.json"),
    getJson("champion_challenger_comparison.json"),
    getJson("model_risk_verdicts.json"),
    getJson("methodology_summary.json"),
    getCsv("data_quality_report.csv"),
  ]);
  return {
    commandCenter, underwritingDecisions, underwritingPolicy, fraudAlerts, fraudPolicy,
    stablecoinAlerts, expectedLossSummary, expectedLossSegment, stressLoss, policyLoss,
    simulatorInputs, simulatorResults, validationSummary, championChallenger, verdicts,
    methodology, dataQuality,
  };
}

// Verdicts file may be a list or {verdicts:[...]}.
export const asVerdictList = (v: any): any[] => (Array.isArray(v) ? v : v?.verdicts ?? []);
