import re


class PriceParseError(ValueError):
    """Raised when a price value cannot be parsed."""


def clean_number(num_str: str) -> int | None:
    if not num_str:
        return None

    try:
        return int(num_str.replace(" ", "").replace("\u00a0", ""))
    except (ValueError, AttributeError):
        return None


def parse_price(value: str) -> int:
    if not value or not value.strip():
        raise PriceParseError("Price value is empty")

    match = re.search(r"[\d\s\u00a0]+", value)
    if not match:
        raise PriceParseError(f"Could not parse price: {value!r}")

    price = clean_number(match.group(0))
    if price is None:
        raise PriceParseError(f"Could not parse price: {value!r}")

    return price
