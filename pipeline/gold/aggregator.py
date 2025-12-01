"""
Business logic for Gold layer aggregation.
Обновляет все Gold-таблицы: продажи + аренда (помесячно/посуточно)
"""
import os
import logging
from supabase import create_client
from typing import Any

def get_client():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)

def refresh_gold_estate():
    """Обновляет Gold по продажам"""
    client = get_client()
    logging.info("Calling Supabase RPC: refresh_gold_estate")
    resp = client.rpc("refresh_gold_estate").execute()
    logging.info("refresh_gold_estate → %s", resp)
    return resp

def refresh_gold_rent():
    """Обновляет Gold по аренде"""
    client = get_client()
    logging.info("Calling Supabase RPC: refresh_gold_rent")
    resp = client.rpc("refresh_gold_rent").execute()
    logging.info("refresh_gold_rent → %s", resp)
    return resp

def refresh() -> dict[str, Any]:
    """
    Главная функция — обновляет gold одним вызовом.
    Используется в run_gold.py
    """
    results = {}

    try:
        results["sales"] = refresh_gold_estate()
    except Exception as e:
        logging.error("Failed to refresh sales gold: %s", e)
        results["sales"] = {"error": str(e)}

    try:
        results["rent"] = refresh_gold_rent()
    except Exception as e:
        logging.error("Failed to refresh rent gold: %s", e)
        results["rent"] = {"error": str(e)}

    # Опционально: можно добавить yield, но он VIEW → обновляется сам
    logging.info("All Gold layers refreshed successfully")
    return results
