import pytest

from remote_decks.parse_remote_deck import build_remote_deck_from_csv, parse_csv_data


def test_parse_csv_data_basic():
    csv_string = "Front,Back\nhello,world\nfoo,bar"
    result = parse_csv_data(csv_string)
    assert result == [["Front", "Back"], ["hello", "world"], ["foo", "bar"]]


def test_parse_csv_data_empty():
    csv_string = "Front,Back"
    result = parse_csv_data(csv_string)
    assert result == [["Front", "Back"]]


def test_parse_csv_data_skips_no_rows():
    """parse_csv_data returns all rows including header; empty-row skipping happens in build."""
    csv_string = "Front,Back\n,\nhello,world"
    result = parse_csv_data(csv_string)
    assert len(result) == 3


def test_build_remote_deck_from_csv_valid():
    data = [["Front", "Back"], ["hello", "world"], ["foo", "bar"]]
    deck = build_remote_deck_from_csv(data, "Basic", ["Front", "Back"])
    assert len(deck.notecards) == 2
    assert deck.notecards[0]["fields"] == {"Front": "hello", "Back": "world"}
    assert deck.notecards[1]["fields"] == {"Front": "foo", "Back": "bar"}


def test_build_remote_deck_from_csv_sets_note_type():
    data = [["Front", "Back"], ["q", "a"]]
    deck = build_remote_deck_from_csv(data, "MyType", ["Front", "Back"])
    assert deck.notecards[0]["type"] == "MyType"


def test_build_remote_deck_from_csv_skips_empty_rows():
    data = [["Front", "Back"], ["", ""], ["hello", "world"]]
    deck = build_remote_deck_from_csv(data, "Basic", ["Front", "Back"])
    assert len(deck.notecards) == 1
    assert deck.notecards[0]["fields"]["Front"] == "hello"


def test_build_remote_deck_from_csv_missing_field():
    data = [["Front", "Extra"], ["hello", "world"]]
    with pytest.raises(Exception, match="CSV headers do not match note type fields"):
        build_remote_deck_from_csv(data, "Basic", ["Front", "Back"])


def test_build_remote_deck_from_csv_strips_whitespace():
    data = [["  Front  ", "  Back  "], [" hello ", " world "]]
    deck = build_remote_deck_from_csv(data, "Basic", ["Front", "Back"])
    assert deck.notecards[0]["fields"]["Front"] == "hello"
    assert deck.notecards[0]["fields"]["Back"] == "world"
