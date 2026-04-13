from app.utils.date_parser import parse_date


def test_day_month_year():
    assert parse_date("30-Nov-2022") == "30/11/2022"


def test_day_month_year_spaces():
    assert parse_date("30 Nov 2022") == "30/11/2022"


def test_slash_separated():
    assert parse_date("12/09/2022") == "12/09/2022"


def test_iso_format():
    assert parse_date("2022-11-30") == "30/11/2022"


def test_none_input():
    assert parse_date(None) is None


def test_jan_caps():
    assert parse_date("04-JAN-2023") == "04/01/2023"
