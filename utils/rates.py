import requests
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

# Cache rates for 6 hours to avoid hitting the API on every request
_cache: Dict[str, float] = {}
_last_update: Optional[datetime] = None
CACHE_TTL = timedelta(hours=6)

# Fallback rates (updated 08.12.2025)
FALLBACK_RATES = {
    "eur_to_mdl": 19.8153,
    "eur_to_usd": 1.16,
    "mdl_to_eur": 1 / 19.8153,   # ≈ 0.0505
    "mdl_to_usd": 1 / 17.0154,   # ≈ 0.0588
    "usd_to_eur": 1 / 1.16,      # ≈ 0.8621
    "usd_to_mdl": 17.0154,
}

def get_current_rates() -> Dict[str, float]:

    global _cache, _last_update
    
    # If cache is fresh, return it
    if _last_update and datetime.now() - _last_update < CACHE_TTL and _cache:
        return _cache
    
    try:
        # Free API (no key required up to 1500 requests/month)
        resp = requests.get("https://api.exchangerate-api.com/v4/latest/EUR", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        eur_to_mdl = data["rates"]["MDL"]
        eur_to_usd = data["rates"]["USD"]
        
        # Calculate all needed rates
        rates = {
            "eur_to_mdl": round(eur_to_mdl, 4),
            "eur_to_usd": round(eur_to_usd, 4),
            "mdl_to_eur": round(1 / eur_to_mdl, 6),
            "mdl_to_usd": round(eur_to_usd / eur_to_mdl, 6),
            "usd_to_eur": round(1 / eur_to_usd, 6),
            "usd_to_mdl": round(eur_to_mdl / eur_to_usd, 4),
        }
        
        # Update cache
        _cache = rates
        _last_update = datetime.now()
        
        logging.info(f"✅ Курсы валют обновлены: EUR→MDL={eur_to_mdl:.3f}, EUR→USD={eur_to_usd:.3f}")
        return rates
        
    except Exception as e:
        logging.warning(f"⚠️ Не удалось получить курсы валют: {e}. Используем запасные курсы.")
        
        # If cache exists but is stale, still use it
        if _cache:
            logging.info("Используем устаревший кэш")
            return _cache
        
        # As a last resort, return the fallback rates
        return FALLBACK_RATES

def convert_currency(amount: int, from_curr: str, to_curr: str) -> int:
    """Конвертировать валюту по актуальному курсу."""
    if from_curr == to_curr:
        return amount
    
    rates = get_current_rates()
    rate_key = f"{from_curr}_to_{to_curr}"
    rate = rates.get(rate_key, 1.0)
    
    return round(amount * rate)
