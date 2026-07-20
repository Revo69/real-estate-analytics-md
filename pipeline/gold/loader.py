"""
Loader entrypoint for Gold layer.
Delegates to aggregator logic.
"""

import logging
from pipeline.gold import aggregator
from common.pipeline_runs import finish_run, get_run_id, update_run


def main():
    run_id = get_run_id()
    update_run(run_id, current_stage="gold")

    try:
        logging.info("Starting Gold loader...")
        aggregator.refresh()

    except Exception as error:
        logging.exception("Gold refresh failed")

        finish_run(
            run_id,
            status="failed",
            failed_stage="gold",
            error_message=str(error),
        )

        raise

    finish_run(run_id, status="succeeded")
    logging.info("Gold loader finished successfully.")
