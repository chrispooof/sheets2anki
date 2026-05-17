"""Tests for sync logic in remote_decks.main.

Anki's Collection is mocked; these tests focus on the key-matching and
create-vs-update decision in create_or_update_notes.
"""

from unittest.mock import MagicMock, patch


from remote_decks.main import create_or_update_notes, sync_decks
from remote_decks.models.remote_deck import RemoteDeck


def _make_deck(notecards):
    deck = RemoteDeck()
    deck.deck_name = "Test Deck"
    deck.notecards = notecards
    return deck


def _make_col(existing_note_data: dict):
    """Build a minimal mock Collection pre-populated with existing notes.

    existing_note_data maps key_value -> {field: value} dicts.
    """
    col = MagicMock()

    notes = {}
    note_ids = {}
    for i, (key_val, fields) in enumerate(existing_note_data.items()):
        note = MagicMock()
        note.__contains__ = lambda self, item, _f=fields: item in _f
        note.__getitem__ = lambda self, item, _f=fields: _f[item]
        note.__setitem__ = MagicMock()
        note.tags = []
        notes[key_val] = note
        note_ids[key_val] = i + 1

    col.find_notes.return_value = list(note_ids.values())

    def get_note(nid):
        for key_val, nid_ in note_ids.items():
            if nid_ == nid:
                return notes[key_val]
        raise KeyError(nid)

    col.get_note.side_effect = get_note
    return col, notes, note_ids


class TestCreateOrUpdateNotes:
    def test_creates_new_note_when_not_exists(self):
        col, _, _ = _make_col({})
        model = {"did": None, "flds": []}
        col.models.by_name.return_value = model
        new_note = MagicMock()
        col.new_note.return_value = new_note

        deck = _make_deck(
            [
                {
                    "type": "Basic",
                    "fields": {"Front": "hello", "Back": "world"},
                    "tags": [],
                }
            ]
        )
        create_or_update_notes(
            col,
            deck,
            deck_id=1,
            note_type_name="Basic",
            notecard_key_field="Front",
            notecard_additional_key_fields=[],
        )

        col.add_note.assert_called_once_with(new_note, 1)

    def test_updates_existing_note(self):
        col, notes, _ = _make_col({"hello": {"Front": "hello", "Back": "old"}})
        deck = _make_deck(
            [
                {
                    "type": "Basic",
                    "fields": {"Front": "hello", "Back": "new"},
                    "tags": ["tag1"],
                }
            ]
        )

        create_or_update_notes(
            col,
            deck,
            deck_id=1,
            note_type_name="Basic",
            notecard_key_field="Front",
            notecard_additional_key_fields=[],
        )

        note = notes["hello"]
        note.__setitem__.assert_any_call("Back", "new")
        col.add_note.assert_not_called()

    def test_deletes_note_missing_from_remote(self):
        col, _, note_ids = _make_col({"stale": {"Front": "stale", "Back": "old"}})
        deck = _make_deck([])  # remote has no cards

        create_or_update_notes(
            col,
            deck,
            deck_id=1,
            note_type_name="Basic",
            notecard_key_field="Front",
            notecard_additional_key_fields=[],
        )

        col.remove_notes.assert_called_once_with([note_ids["stale"]])

    def test_composite_key_matching(self):
        col, notes, _ = _make_col(
            {"hello-A": {"Front": "hello", "Chapter": "A", "Back": "old"}}
        )
        deck = _make_deck(
            [
                {
                    "type": "Basic",
                    "fields": {"Front": "hello", "Chapter": "A", "Back": "new"},
                    "tags": [],
                }
            ]
        )

        create_or_update_notes(
            col,
            deck,
            deck_id=1,
            note_type_name="Basic",
            notecard_key_field="Front",
            notecard_additional_key_fields=["Chapter"],
        )

        note = notes["hello-A"]
        note.__setitem__.assert_any_call("Back", "new")
        col.add_note.assert_not_called()

    def test_missing_model_skips_note(self):
        col, _, _ = _make_col({})
        col.models.by_name.return_value = None

        deck = _make_deck(
            [
                {
                    "type": "Missing",
                    "fields": {"Front": "hello", "Back": "world"},
                    "tags": [],
                }
            ]
        )
        with patch("remote_decks.main.showInfo"):
            create_or_update_notes(
                col,
                deck,
                deck_id=1,
                note_type_name="Missing",
                notecard_key_field="Front",
                notecard_additional_key_fields=[],
            )

        col.add_note.assert_not_called()


def _make_remote_deck_config(note_type_fields):
    return {
        "url": "https://example.com/sheet.csv",
        "deck_name": "Test Deck",
        "note_type": "Basic",
        "note_type_fields": list(note_type_fields),
        "notecard_key_field": "Front",
        "notecard_additional_key_fields": [],
    }


def _make_model(field_names):
    return {"flds": [{"name": name} for name in field_names]}


class TestSyncDecksRefreshesNoteTypeFields:
    """`sync_decks` should refresh `note_type_fields` from the live Anki note type."""

    def _run_sync(self, stored_fields, live_fields):
        config = {"remote-decks": {"deck1": _make_remote_deck_config(stored_fields)}}

        addon_manager = MagicMock()
        addon_manager.getConfig.return_value = config

        col = MagicMock()
        if live_fields is None:
            col.models.by_name.return_value = None
        else:
            col.models.by_name.return_value = _make_model(live_fields)

        mw_mock = MagicMock()
        mw_mock.col = col
        mw_mock.addonManager = addon_manager

        with (
            patch("remote_decks.main.mw", mw_mock),
            patch("remote_decks.main.get_remote_deck") as mock_get_remote_deck,
            patch("remote_decks.main.get_or_create_deck", return_value=1),
            patch("remote_decks.main.create_or_update_notes"),
        ):
            mock_get_remote_deck.return_value = RemoteDeck()
            sync_decks()

        return config, addon_manager, mock_get_remote_deck

    def test_refreshes_when_stored_fields_are_stale(self):
        config, addon_manager, mock_get_remote_deck = self._run_sync(
            stored_fields=["Front", "Back"],
            live_fields=["Front", "Back", "Extra"],
        )

        assert config["remote-decks"]["deck1"]["note_type_fields"] == [
            "Front",
            "Back",
            "Extra",
        ]
        addon_manager.writeConfig.assert_called_once()
        # Refreshed fields should be passed to get_remote_deck for validation.
        _, _, passed_fields = mock_get_remote_deck.call_args[0]
        assert passed_fields == ["Front", "Back", "Extra"]

    def test_no_write_when_fields_already_match(self):
        config, addon_manager, _ = self._run_sync(
            stored_fields=["Front", "Back"],
            live_fields=["Front", "Back"],
        )

        assert config["remote-decks"]["deck1"]["note_type_fields"] == ["Front", "Back"]
        addon_manager.writeConfig.assert_not_called()

    def test_skips_refresh_when_note_type_missing(self):
        config, addon_manager, mock_get_remote_deck = self._run_sync(
            stored_fields=["Front", "Back"],
            live_fields=None,
        )

        assert config["remote-decks"]["deck1"]["note_type_fields"] == ["Front", "Back"]
        addon_manager.writeConfig.assert_not_called()
        _, _, passed_fields = mock_get_remote_deck.call_args[0]
        assert passed_fields == ["Front", "Back"]
