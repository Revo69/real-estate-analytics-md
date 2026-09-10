import datetime

import pytest

from pipeline.silver.normalizers import (
    normalize_area,
    normalize_balcony,
    normalize_ceiling_height,
    normalize_date,
    normalize_int,
    normalize_living_room,
    normalize_number_of_rooms,
    normalize_price,
    normalize_region,
    normalize_text,
)
from pipeline.silver.quality import assign_status, calculate_quality_score


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2-х комнатная квартира", 2),
        ("studio", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_number_of_rooms(value, expected):
    assert normalize_number_of_rooms(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Квартира с ливингом", True),
        ("Квартира без ливинга", False),
        ("Ливинг не указан", None),
        (None, None),
    ],
)
def test_normalize_living_room(value, expected):
    assert normalize_living_room(value) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("22 м²", 22.0),
        (" 58,75 м² ", 58.75),
        ("area unknown", None),
        (None, None),
    ],
)
def test_normalize_area(value, expected):
    assert normalize_area(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("250 см", 250),
        ("не указано", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_ceiling_height(value, expected):
    assert normalize_ceiling_height(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("5", 5),
        ("-1", -1),
        ("5.0", None),
        (None, None),
    ],
)
def test_normalize_int(value, expected):
    assert normalize_int(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Нет", 0),
        ("2 лоджии", 2),
        ("не указано", None),
        (None, None),
    ],
)
def test_normalize_balcony(value, expected):
    assert normalize_balcony(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime.date(2026, 9, 10), "2026-09-10"),
        (
            datetime.datetime(2026, 9, 10, 14, 30, 5, tzinfo=datetime.UTC),
            "2026-09-10T14:30:05+00:00",
        ),
        (" 2026-09-10 ", "2026-09-10"),
        (123, None),
        (None, None),
    ],
)
def test_normalize_date(value, expected):
    assert normalize_date(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("123900.50", 123900.5),
        (0, 0.0),
        ("price unknown", None),
        (None, None),
    ],
)
def test_normalize_price(value, expected):
    assert normalize_price(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("  Centru  ", "Centru"),
        ("", None),
        (None, None),
    ],
)
def test_normalize_text(value, expected):
    assert normalize_text(value) == expected


def test_normalize_region_splits_address_and_cleans_house():
    region_raw = "Chișinău mun., Chișinău, Centru, str. București, 10/A!"

    assert normalize_region(region_raw) == {
        "municipality": "Chișinău mun.",
        "city": "Chișinău",
        "sector": "Centru",
        "street_raw": "str. București",
        "house": "10/A",
        "region_raw": region_raw,
    }


@pytest.mark.parametrize("region_raw", [None, "", "   "])
def test_normalize_region_handles_missing_value(region_raw):
    assert normalize_region(region_raw) == {
        "municipality": None,
        "city": None,
        "sector": None,
        "street_raw": None,
        "house": None,
        "region_raw": region_raw,
    }


def test_normalize_region_handles_partial_address():
    assert normalize_region("Orhei, Orhei") == {
        "municipality": "Orhei",
        "city": "Orhei",
        "sector": None,
        "street_raw": None,
        "house": None,
        "region_raw": "Orhei, Orhei",
    }


def test_calculate_quality_score_counts_only_nonempty_nonzero_fields():
    row = {
        "price_mdl": 2_400_000,
        "price_eur": 125_000,
        "number_of_rooms": 3,
        "total_area_m2": 75.5,
        "floor": 0,
        "total_floors": 10,
        "region": "Chișinău, Centru",
        "bathroom_count": None,
    }

    assert calculate_quality_score(row) == 0.75
    assert calculate_quality_score({}) == 0.0


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.0, "failed"),
        (0.549, "failed"),
        (0.55, "partial"),
        (0.849, "partial"),
        (0.85, "success"),
        (1.0, "success"),
    ],
)
def test_assign_status_boundaries(score, expected):
    assert assign_status(score) == expected
