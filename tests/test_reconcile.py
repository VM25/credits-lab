from src.reporting import command_center, methodology, reconcile


def test_required_outputs_and_totals():
    # ensure reporting outputs exist, then run the gates
    command_center.build()
    methodology.build()
    counts = reconcile.required_outputs()
    assert counts["csv"] == 9 and counts["json"] == 16 and counts["processed"] == 7
    rec = reconcile.totals()
    assert rec["reconciled"] is True
    assert rec["verdicts"] == 5
