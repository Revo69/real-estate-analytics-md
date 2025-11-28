"""
Business logic for Gold layer aggregation.
Handles RPC call to refresh_gold_estate in Supabase.
"""

import os
import logging
from supabase import create_client

def refresh():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    supabase = create_client(url, key)

    logging.info("Calling Supabase RPC: refresh_gold_estate")
    resp = supabase.rpc("refresh_gold_estate").execute()
    logging.info("RPC response: %s", resp)
    return resp
