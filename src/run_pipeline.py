"""End-to-end pipeline orchestrator.

Runs every phase in doc order and fails fast on any hard gate (leakage,
reconciliation, missing output). One command rebuilds a complete, reconciled
``data/outputs``:

    python -m src.run_pipeline
"""
import sys

from src.data import ingest_macro, ingest_credit, ingest_payments, ingest_stablecoin
from src.data import features, quality
from src.risk import underwriting, fraud, stablecoin, expected_loss, policy_simulator
from src.validation import validate
from src.reporting import command_center, methodology, reconcile


def main() -> None:
    print("[1/14] macro ingest");        ingest_macro.run()
    print("[2/14] credit ingest");       ingest_credit.run()
    print("[3/14] payments ingest");     ingest_payments.run()
    print("[4/14] stablecoin ingest");   ingest_stablecoin.run()
    print("[5/14] features + datasets"); features.run()
    print("[6/14] data quality + leakage gate"); quality.run()      # raises LeakageError
    print("[7/14] underwriting engine"); underwriting.build()
    print("[8/14] fraud engine");        fraud.build()
    print("[9/14] stablecoin module");   stablecoin.build()
    print("[10/14] expected-loss engine"); expected_loss.build()   # raises ReconciliationError
    print("[11/14] model-risk validation"); validate.build()
    print("[12/14] policy simulator");   policy_simulator.build()
    print("[13/14] reporting (command center + methodology)")
    command_center.build()
    methodology.build()
    print("[14/14] reconciliation gates")
    counts = reconcile.required_outputs()   # raises MissingOutputError
    rec = reconcile.totals()                # raises ReconciliationError
    print(f"OK — outputs: {counts}; reconciliation: {rec}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # fail fast with a clear message
        print(f"PIPELINE FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
