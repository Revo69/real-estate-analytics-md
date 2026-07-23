import pytest

from pipeline.bronze.cleaners import PriceParseError, clean_number, parse_price


def test_clean_number_removes_regular_spaces():
    assert clean_number("45 000") == 45000


def test_clean_number_removes_non_breaking_spaces():
    assert clean_number("45\u00a0000") == 45000


def test_clean_number_returns_none_for_empty_value():
    assert clean_number("") is None


def test_clean_number_returns_none_for_invalid_value():
    assert clean_number("not a number") is None


def test_parse_price_extracts_eur_price():
    assert parse_price("45 000 €") == 45000


def test_parse_price_extracts_usd_price():
    assert parse_price("1 200 $") == 1200


def test_parse_price_extracts_mdl_price():
    assert parse_price("900000 MDL") == 900000


def test_parse_price_raises_for_empty_value():
    with pytest.raises(PriceParseError):
        parse_price("")


def test_parse_price_raises_for_invalid_value():
    with pytest.raises(PriceParseError):
        parse_price("price unknown")
