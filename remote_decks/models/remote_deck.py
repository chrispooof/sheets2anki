from typing import Any


class RemoteDeck:
    """Represents a remote deck fetched from a CSV source (e.g. Google Sheets).

    Attributes:
        deck_name: Display name of the Anki deck.
        notecards: List of notecard dicts, each with 'type', 'fields', and 'tags' keys.
    """

    def __init__(self):
        self.deck_name: str = ""
        self.notecards: list[dict[str, Any]] = []
