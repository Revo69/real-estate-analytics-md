"""Repository helpers for operational pipeline run metadata."""

import os
import uuid
from datetime import UTC, datetime
from typing import Any

from supabase import create_client


def get_run_id() -> str:
    """Return one stable identifier shared by all jobs of a GitHub workflow."""
    github_run_id = os.getenv("GITHUB_RUN_ID")
    github_attempt = os.getenv("GITHUB_RUN_ATTEMPT")

    if github_run_id and github_attempt:
        return f"github-{github_run_id}-attempt-{github_attempt}"

    return f"local-{uuid.uuid4()}"


def _get_client():
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_KEY"],
    )


def start_run(run_id: str) -> None:
    """Create one metadata record at the beginning of a pipeline execution."""
    github_run_id = os.getenv("GITHUB_RUN_ID")

    payload: dict[str, Any] = {
        "run_id": run_id,
        "pipeline_name": "real-estate-pipeline",
        "status": "running",
        "current_stage": "collect_links",
        "git_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": int(github_run_id) if github_run_id else None,
        "github_run_attempt": int(os.getenv("GITHUB_RUN_ATTEMPT", "1")),
    }

    _get_client().table("pipeline_runs").insert(payload).execute()


def update_run(run_id: str, **changes: Any) -> None:
    """Update status, stage, counters, or diagnostics for an existing run."""
    if not changes:
        return

    _get_client().table("pipeline_runs").update(changes).eq("run_id", run_id).execute()


def finish_run(
    run_id: str,
    *,
    status: str,
    failed_stage: str | None = None,
    error_message: str | None = None,
) -> None:
    """Mark a run as succeeded or failed."""
    if status not in {"succeeded", "failed"}:
        raise ValueError("status must be 'succeeded' or 'failed'")

    update_run(
        run_id,
        status=status,
        current_stage=None,
        failed_stage=failed_stage,
        error_message=error_message,
        finished_at=datetime.now(UTC).isoformat(),
    )
