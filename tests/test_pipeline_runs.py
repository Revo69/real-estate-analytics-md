from datetime import UTC, datetime
from unittest.mock import Mock, patch

from common import pipeline_runs


def test_finish_run_records_terminal_fields_through_supabase_client():
    client = Mock()
    table = client.table.return_value
    update_query = table.update.return_value
    filtered_query = update_query.eq.return_value
    started_at = datetime.now(UTC)

    with patch.object(pipeline_runs, "_get_client", return_value=client):
        pipeline_runs.finish_run(
            "run-123",
            status="failed",
            failed_stage="gold",
            error_message="sales RPC unavailable",
        )

    finished_at = datetime.now(UTC)
    payload = table.update.call_args.args[0]

    client.table.assert_called_once_with("pipeline_runs")
    assert payload["status"] == "failed"
    assert payload["current_stage"] is None
    assert payload["failed_stage"] == "gold"
    assert payload["error_message"] == "sales RPC unavailable"
    assert started_at <= datetime.fromisoformat(payload["finished_at"]) <= finished_at
    update_query.eq.assert_called_once_with("run_id", "run-123")
    filtered_query.execute.assert_called_once_with()
