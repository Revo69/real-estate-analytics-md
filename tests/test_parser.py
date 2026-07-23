from pipeline.bronze.cleaners import clean_number


def test_clean_number_removes_regular_spaces():
    assert clean_number("45 000") == 45000


def test_clean_number_removes_non_breaking_spaces():
    assert clean_number("45\u00a0000") == 45000


def test_clean_number_returns_none_for_empty_value():
    assert clean_number("") is None


def test_clean_number_returns_none_for_invalid_value():
    assert clean_number("not a number") is None
