"""Entry point for remote deck operations.

Provides functions to sync, add, remove, and update remote Anki decks
sourced from published Google Sheets CSV URLs.
"""

from anki.collection import Collection
from aqt import mw
from aqt.qt import QInputDialog, QLineEdit
from aqt.utils import showInfo

from .key_fields_dialog import KeyFieldsDialog
from .models.remote_deck import RemoteDeck
from .models.remote_deck_config import RemoteDeckConfig

try:
    echo_mode_normal = QLineEdit.EchoMode.Normal
except AttributeError:
    echo_mode_normal = QLineEdit.Normal  # type: ignore[attr-defined]

from .logger import configure as configure_logging
from .parse_remote_deck import get_remote_deck


def sync_decks() -> None:
    """Function to sync remote decks."""
    col = mw.col
    config = mw.addonManager.getConfig(__name__)

    configure_logging(bool(config and config.get("debug", False)))
    if not config:
        config = {"remote-decks": {}}

    for deck_key in config["remote-decks"].keys():
        try:
            current_remote_info = config["remote-decks"][deck_key]

            remote_deck_config = RemoteDeckConfig()
            remote_deck_config.url = current_remote_info["url"]
            remote_deck_config.deck_name = current_remote_info["deck_name"]
            remote_deck_config.note_type = current_remote_info["note_type"]
            remote_deck_config.note_type_fields = current_remote_info[
                "note_type_fields"
            ]
            remote_deck_config.notecard_key_field = current_remote_info[
                "notecard_key_field"
            ]
            remote_deck_config.notecard_additional_key_fields = current_remote_info.get(
                "notecard_additional_key_fields", []
            )

            remote_deck = get_remote_deck(
                current_remote_info["url"],
                remote_deck_config.note_type,
                remote_deck_config.note_type_fields,
            )
            remote_deck.deck_name = remote_deck_config.deck_name
            deck_id = get_or_create_deck(col, remote_deck_config.deck_name)
            create_or_update_notes(
                col,
                remote_deck,
                deck_id,
                remote_deck_config.note_type,
                remote_deck_config.notecard_key_field,
                remote_deck_config.notecard_additional_key_fields,
            )
        except Exception as e:
            deck_message = (
                f"\nThe following deck failed to sync: {remote_deck_config.deck_name}"
            )
            showInfo(str(e) + deck_message)
            raise


def get_or_create_deck(col: Collection, deck_name: str) -> int:
    """Get or create a deck by name and return its ID.
    Args:
        col (Collection): The Anki collection.
        deck_name (str): The name of the deck.
    Returns:
        int: The ID of the deck.
    """
    deck = col.decks.by_name(deck_name)
    if deck is None:
        deck_id = col.decks.id(deck_name)
    else:
        deck_id = deck["id"]
    return int(deck_id)  # type: ignore[arg-type]


def create_or_update_notes(
    col: Collection,
    remote_deck: RemoteDeck,
    deck_id: int,
    note_type_name: str,
    notecard_key_field: str,
    notecard_additional_key_fields: list[str],
) -> None:
    """Create or update notes in the Anki collection based on the remote deck.
    Args:
        col (Collection): The Anki collection.
        remote_deck (RemoteDeck): The remote deck (e.g. google sheets) containing notecards.
        deck_id (int): The ID of the deck where notes will be added or updated.
        note_type_name (str): The name of the note type to use.
        notecard_key_field (str): The field used as a unique key for notecards
        notecard_additional_key_fields (list[str]): Additional fields that need to be unique across cards
    """

    # Dictionaries for existing notes
    existing_notes = {}
    existing_note_ids = {}

    notes = col.find_notes(f'deck:"{remote_deck.deck_name}"')
    all_keys = [notecard_key_field] + notecard_additional_key_fields

    # Fetch existing notes in the deck
    for nid in notes:
        note = col.get_note(nid)
        keys = []

        # Use the specified key field to identify notes
        if notecard_key_field in note:
            keys.append(note[notecard_key_field])
            if len(notecard_additional_key_fields) > 0:
                for add_key_field in notecard_additional_key_fields:
                    keys.append(note[add_key_field])
        else:
            continue  # Skip notes without the specified key field
        key = "-".join(keys)
        existing_notes[key] = note
        existing_note_ids[key] = nid

    # Set to keep track of keys from Google Sheets
    gs_keys = set()

    for notecard in remote_deck.notecards:
        card_type = notecard["type"]
        fields = notecard["fields"]
        tags = notecard.get("tags", [])

        try:
            key = "-".join([fields[field] for field in all_keys])
            gs_keys.add(key)

            if key in existing_notes:
                # Update existing note
                note = existing_notes[key]
                for field_name, value in fields.items():
                    note[field_name] = value
                note.tags = tags
                note.flush()
            else:
                # Create new note
                model = col.models.by_name(note_type_name)
                if model is None:
                    showInfo(
                        f"The {note_type_name} model does not exist. Please create a {note_type_name} model in Anki."
                    )
                    continue

                col.models.set_current(model)
                model["did"] = deck_id
                col.models.save(model)

                note = col.new_note(model)
                for field_name, value in fields.items():
                    note[field_name] = value
                note.tags = tags
                col.add_note(note, deck_id)  # type: ignore[arg-type]

        except Exception as e:
            showInfo(
                f"Unknown card type '{card_type}' for card '{key}', with error: {e}.\nSkipping."
            )
            continue

    # Find notes that are in Anki but not in Google Sheets
    anki_keys = set(existing_notes.keys())
    notes_to_delete = anki_keys - gs_keys

    # Remove the corresponding notes
    if notes_to_delete:
        note_ids_to_delete = [existing_note_ids[key] for key in notes_to_delete]
        col.remove_notes(note_ids_to_delete)

    # Save changes
    col.save()


def add_new_deck() -> None:
    """Function to add a new remote deck."""
    url, ok_pressed = QInputDialog.getText(
        mw, "Add New Remote Deck", "URL of published CSV:", echo_mode_normal, ""
    )
    if not ok_pressed or not url.strip():
        return

    url = url.strip()

    if "output=csv" not in url:
        showInfo(
            "The provided URL does not appear to be a published CSV from Google Sheets."
        )
        return

    deck_name, ok_pressed = QInputDialog.getText(
        mw, "Deck Name", "Enter the name of the deck:", echo_mode_normal, ""
    )
    if not ok_pressed or not deck_name.strip():
        deck_name = "Deck from CSV"
    names_and_ids = mw.col.models.all_names_and_ids()

    note_type_name_to_id = {item.name: item.id for item in names_and_ids}
    note_type_names = list(note_type_name_to_id.keys())

    note_type_name, ok_pressed = QInputDialog.getItem(
        mw,
        "Select a Note Type to map the notecards to",
        "Select a note type:",
        note_type_names,
        0,
        False,
    )

    if not ok_pressed or not note_type_name.strip():
        note_type_name = "Basic"

    note_type_model = mw.col.models.get(note_type_name_to_id[note_type_name])  # type: ignore[arg-type]
    if note_type_model is None:
        showInfo(f"Could not load note type '{note_type_name}'.")
        return
    note_type_fields = [field["name"] for field in note_type_model["flds"]]

    note_type_fields = list(filter(lambda x: x != "Cloze", note_type_fields))

    # Use the new dialog for key field selection
    key_dialog = KeyFieldsDialog(
        available_fields=note_type_fields,
        primary_key=note_type_fields[0] if note_type_fields else "",
    )

    if key_dialog.exec():
        notecard_key_field, notecard_additional_key_fields = (
            key_dialog.get_selected_fields()
        )
    else:
        return  # User cancelled

    showInfo(
        f"Selected note type:\n\n{note_type_name}\n\n"
        f"with primary key field:\n\n{notecard_key_field}\n\n"
        f"and additional key fields:\n\n{', '.join(notecard_additional_key_fields) if notecard_additional_key_fields else 'None'}"
    )

    config = mw.addonManager.getConfig(__name__)
    if not config:
        config = {"remote-decks": {}}

    if url in config["remote-decks"]:
        showInfo(f"The deck has already been added before: {url}")
        return

    try:
        deck = get_remote_deck(url, note_type_name, note_type_fields)
        deck.deck_name = deck_name
    except Exception as e:
        showInfo(f"Error fetching the remote deck:\n{e}")
        return

    config["remote-decks"][url] = {
        "url": url,
        "deck_name": deck_name,
        "note_type": note_type_name,
        "note_type_fields": note_type_fields,
        "notecard_key_field": notecard_key_field,
        "notecard_additional_key_fields": notecard_additional_key_fields,
    }

    mw.addonManager.writeConfig(__name__, config)
    sync_decks()


def remove_remote_deck() -> None:
    """Function to remove a remote deck."""

    # Get the add-on configuration
    config = mw.addonManager.getConfig(__name__)
    if not config:
        config = {"remote-decks": {}}

    remote_decks = config["remote-decks"]

    # Get all deck names
    deck_names = [remote_decks[key]["deck_name"] for key in remote_decks]

    if len(deck_names) == 0:
        showInfo("There are currently no remote decks.")
        return

    # Ask the user to select a deck
    selection, ok_pressed = QInputDialog.getItem(
        mw, "Select a Deck to Unlink", "Select a deck to unlink:", deck_names, 0, False
    )

    # Remove the deck
    if ok_pressed:
        for key in list(remote_decks.keys()):
            if selection == remote_decks[key]["deck_name"]:
                del remote_decks[key]
                break

        # Save the updated configuration
        mw.addonManager.writeConfig(__name__, config)
        showInfo(f"The deck '{selection}' has been unlinked.")


def update_deck_key_fields() -> None:
    """Function to update key fields for existing remote decks."""
    config = mw.addonManager.getConfig(__name__)
    if not config:
        config = {"remote-decks": {}}

    remote_decks = config["remote-decks"]
    deck_names = [remote_decks[key]["deck_name"] for key in remote_decks]

    if len(deck_names) == 0:
        showInfo("There are currently no remote decks.")
        return

    # Select deck to update
    selection, ok_pressed = QInputDialog.getItem(
        mw,
        "Select Deck to Update",
        "Select a deck to update key fields:",
        deck_names,
        0,
        False,
    )

    if not ok_pressed or not selection:
        return

    # Find the deck config
    deck_config = None
    for url, config_ in remote_decks.items():
        if config_["deck_name"] == selection:
            deck_config = config_
            break

    if not deck_config:
        showInfo("Deck configuration not found.")
        return

    # Get note type fields
    note_type_fields = deck_config["note_type_fields"]

    # Show dialog with current values
    key_dialog = KeyFieldsDialog(
        available_fields=note_type_fields,
        primary_key=deck_config["notecard_key_field"],
        additional_keys=deck_config.get("notecard_additional_key_fields", []),
    )

    if key_dialog.exec():
        notecard_key_field, notecard_additional_key_fields = (
            key_dialog.get_selected_fields()
        )

        # Update config
        deck_config["notecard_key_field"] = notecard_key_field
        deck_config["notecard_additional_key_fields"] = notecard_additional_key_fields

        # Save config
        mw.addonManager.writeConfig(__name__, config)

        showInfo(
            f"Updated key fields for '{selection}':\n\n"
            f"Primary: {notecard_key_field}\n"
            f"Additional: {', '.join(notecard_additional_key_fields) if notecard_additional_key_fields else 'None'}"
        )
