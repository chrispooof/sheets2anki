"""Tests for sync logic in remote_decks.main.

Anki's Collection is mocked; these tests focus on the key-matching and
create-vs-update decision in create_or_update_notes.
"""

from unittest.mock import MagicMock, patch


from remote_decks.main import create_or_update_notes
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
