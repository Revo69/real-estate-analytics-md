from typing import Optional


def clean_number(num_str: str) -> Optional[int]:
    if not num_str:
        return None

    try:
        return int(num_str.replace(" ", "").replace("\u00a0", ""))
    except (ValueError, AttributeError):
        return None
