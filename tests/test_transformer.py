from unittest.mock import patch

with patch("supabase.create_client"):
    from pipeline.silver.loader import transform_record


def test_transform_record_normalizes_representative_bronze_row():
    region_raw = "Chișinău mun., Chișinău, Centru, str. București, 10/A!"
    row = (
        7,
        "https://999.md/ro/100000007",
        "100000007",
        "success",
        "Дата публикации:14 авг. 2026, 15:42",
        "Proimobil",
        "Продам",
        region_raw,
        "Квартира в центре",
        {"mdl": "2400000", "eur": "125000", "usd": "145000"},
        {
            "listing_author": "  Агентство  ",
            "number_of_rooms": "3-х комнатная квартира",
            "living_room": "Квартира с ливингом",
            "total_area_m2": "75,5 м²",
            "housing_type": "  Новострой  ",
            "floor": "5",
            "total_floors": "10",
            "developer": "  Urban Construct  ",
            "building_type": "  Кирпичный  ",
            "apartment_condition": "  Евроремонт  ",
            "layout": "  Раздельная  ",
            "living_area_m2": "50 м²",
            "kitchen_area_m2": "12,5 м²",
            "bathroom_count": "2",
            "balcony_loggia": "2 лоджии",
            "ceiling_height_cm": "280 см",
            "parking_space": "  Подземная  ",
        },
        {
            "ready_to_move_in": True,
            "furnished": False,
            "elevator": True,
        },
    )

    result = transform_record(row)

    assert result["id"] == 7
    assert result["url"] == "https://999.md/ro/100000007"
    assert result["publication_date"] == "2026-08-14"
    assert result["municipality"] == "Chișinău mun."
    assert result["city"] == "Chișinău"
    assert result["sector"] == "Centru"
    assert result["street_raw"] == "str. București"
    assert result["house"] == "10/A"
    assert result["region_raw"] == region_raw
    assert result["price_mdl"] == 2_400_000.0
    assert result["price_eur"] == 125_000.0
    assert result["price_usd"] == 145_000.0
    assert result["listing_author"] == "Агентство"
    assert result["number_of_rooms"] == 3
    assert result["living_room"] is True
    assert result["total_area_m2"] == 75.5
    assert result["housing_type"] == "Новострой"
    assert result["floor"] == 5
    assert result["total_floors"] == 10
    assert result["living_area_m2"] == 50.0
    assert result["kitchen_area_m2"] == 12.5
    assert result["bathroom_count"] == 2
    assert result["balcony_loggia"] == 2
    assert result["ceiling_height_cm"] == 280
    assert result["parking_space"] == "Подземная"
    assert result["ready_to_move_in"] is True
    assert result["furnished"] is False
    assert result["elevator"] is True
    assert result["quality_score"] == 0.875
    assert result["normalization_status"] == "success"


def test_transform_record_handles_empty_json_fields():
    row = (
        8,
        "https://999.md/ro/100000008",
        "100000008",
        "success",
        None,
        None,
        "Продам",
        None,
        None,
        "",
        "null",
        None,
    )

    result = transform_record(row)

    assert result["publication_date"] is None
    assert result["region_raw"] is None
    assert result["price_mdl"] is None
    assert result["price_eur"] is None
    assert result["price_usd"] is None
    assert result["number_of_rooms"] is None
    assert result["total_area_m2"] is None
    assert result["ready_to_move_in"] is None
    assert result["elevator"] is None
    assert result["quality_score"] == 0.0
    assert result["normalization_status"] == "failed"
