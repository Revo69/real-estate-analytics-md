import datetime
import logging
from typing import Optional, Dict
import re

def normalize_number_of_rooms(value: str):
    """'2-х комнатная квартира' → 2"""
    if not value:
        return None
    digits = ''.join(ch for ch in value if ch.isdigit())
    try:
        return int(digits) if digits else None
    except ValueError:
        logging.warning(f"Unexpected number_of_rooms: {value}")
        return None

def normalize_living_room(value: str):
    """'Квартира с ливингом' → True, 'Квартира без ливинга' → False"""
    if not value:
        return None
    val = value.lower()
    if "без" in val:
        return False
    if "с " in val:
        return True
    return None

def normalize_area(value: str):
    """'22 м²' → 22.0"""
    if not value:
        return None
    # заменяем запятую на точку и убираем лишние пробелы
    val = str(value).replace(",", ".").strip()
    # ищем число (целое или с точкой)
    match = re.search(r"\d+(\.\d+)?", val)
    if match:
        try:
            return float(match.group())
        except ValueError:
            logging.warning(f"Unexpected area parse error: {value}")
            return None
    logging.warning(f"Unexpected area format: {value}")
    return None

def normalize_ceiling_height(value: str):
    """'250 см' → 250 (int)"""
    if not value:
        return None
    val = value.lower().replace("см", "").strip()
    digits = ''.join(ch for ch in val if ch.isdigit())
    try:
        return int(digits) if digits else None
    except ValueError:
        logging.warning(f"Unexpected ceiling_height: {value}")
        return None

def normalize_int(value: str):
    """'5' → 5"""
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def normalize_balcony(value: str):
    """'Нет' → 0, '1' → 1"""
    if not value:
        return None
    val = value.lower()
    if val in ["нет", "none", "no"]:
        return 0
    digits = ''.join(ch for ch in value if ch.isdigit())
    return int(digits) if digits else None

def normalize_date(value):
    """Convert date/datetime to ISO string"""
    if not value:
        return None
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, str):
        return value.strip()
    return None

def normalize_price(value):
    """Ensure price is numeric or None"""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def normalize_text(value: str):
    """Return stripped text or None"""
    if not value:
        return None
    return value.strip()

def normalize_region(region_raw: Optional[str]) -> Dict[str, Optional[str]]:
    """
    Final production-grade normalization of Moldovan addresses
    """
    if not region_raw or not region_raw.strip():
        return {
            "municipality": None,
            "city": None,
            "sector": None,
            "street_raw": None,
            "house": None,
            "region_raw": region_raw
        }

    # Protection against extra commas + exactly 5 fields
    parts = [p.strip() for p in region_raw.split(",", 5)]
    while len(parts) < 5:
        parts.append("")

    municipality = parts[0] or None
    city         = parts[1] or None
    sector       = parts[2] or None
    street_raw   = parts[3] or None

    # House — only clean garbage
    house = None
    if parts[4]:
        house = re.sub(r"[^\w\/\-\s]", "", parts[4]).strip() or None

    return {
        "municipality": municipality,
        "city": city,
        "sector": sector,
        "street_raw": street_raw,
        "house": house,
        "region_raw": region_raw
    }
