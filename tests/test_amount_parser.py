from app.utils.amount_parser import parse_amount


def test_basic_dollar_amount():
    assert parse_amount("$49.25") == 4925


def test_amount_with_comma():
    assert parse_amount("$3,000.00") == 300000


def test_parenthesised_amount():
    assert parse_amount("(49.25)") == 4925


def test_plain_number():
    assert parse_amount("3.65") == 365


def test_none_input():
    assert parse_amount(None) is None


def test_empty_string():
    assert parse_amount("") is None


def test_no_decimals():
    assert parse_amount("$100") == 100


def test_currency_prefix():
    assert parse_amount("S$49.25") == 4925
