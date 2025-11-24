import datetime
import logging

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
    digits = ''.join(ch for ch in value if (ch.isdigit() or ch == '.'))
    try:
        return float(digits) if digits else None
    except ValueError:
        logging.warning(f"Unexpected area: {value}")
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
