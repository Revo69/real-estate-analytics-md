"""
Business logic for Gold layer aggregation.
Updates all Gold tables: sales + rent (monthly/daily)
"""

import os
import logging
from supabase import create_client
from typing import Any, Dict


def get_client():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def refresh_gold_estate():
    """Refresh Gold for sales"""
    client = get_client()
    logging.info("Calling Supabase RPC: refresh_gold_estate")
    resp = client.rpc("refresh_gold_estate").execute()
    logging.info("refresh_gold_estate → success")
    return resp


def refresh_gold_rent():
    """Refresh Gold for rent"""
    client = get_client()
    logging.info("Calling Supabase RPC: refresh_gold_rent")
    resp = client.rpc("refresh_gold_rent").execute()
    logging.info("refresh_gold_rent → success")
    return resp


def refresh() -> Dict[str, Any]:
    """Refresh sales and rent Gold layers; fail if either refresh fails."""
    results = {}
    errors = {}

    try:
        results["sales"] = refresh_gold_estate()
    except Exception as error:
        logging.exception("Failed to refresh sales Gold layer")
        errors["sales"] = error

    try:
        results["rent"] = refresh_gold_rent()
    except Exception as error:
        logging.exception("Failed to refresh rent Gold layer")
        errors["rent"] = error

    if errors:
        error_summary = "; ".join(
            f"{layer}: {error}" for layer, error in errors.items()
        )
        raise RuntimeError(f"Gold refresh failed — {error_summary}")

    logging.info("All Gold layers refreshed successfully")
    return results


# For local testing: python -m pipeline.gold.aggregator
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    refresh()
