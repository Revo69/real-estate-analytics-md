from unittest.mock import Mock, call, patch

import pytest

from pipeline.gold import aggregator, loader


def test_refresh_raises_when_one_gold_rpc_fails():
    rent_result = object()

    with (
        patch.object(
            aggregator,
            "refresh_gold_estate",
            side_effect=RuntimeError("sales RPC unavailable"),
        ) as refresh_estate,
        patch.object(
            aggregator,
            "refresh_gold_rent",
            return_value=rent_result,
        ) as refresh_rent,
        pytest.raises(
            RuntimeError,
            match="Gold refresh failed — sales: sales RPC unavailable",
        ),
    ):
        aggregator.refresh()

    refresh_estate.assert_called_once_with()
    refresh_rent.assert_called_once_with()


def test_successful_gold_loader_sets_refresh_flag_before_finishing():
    events = Mock()

    with (
        patch.object(loader, "get_run_id", return_value="run-123") as get_run_id,
        patch.object(loader, "update_run") as update_run,
        patch.object(loader.aggregator, "refresh") as refresh,
        patch.object(loader, "finish_run") as finish_run,
    ):
        events.attach_mock(get_run_id, "get_run_id")
        events.attach_mock(update_run, "update_run")
        events.attach_mock(refresh, "refresh")
        events.attach_mock(finish_run, "finish_run")

        loader.main()

    assert events.mock_calls == [
        call.get_run_id(),
        call.update_run("run-123", current_stage="gold"),
        call.refresh(),
        call.update_run("run-123", gold_refreshed=True),
        call.finish_run("run-123", status="succeeded"),
    ]
