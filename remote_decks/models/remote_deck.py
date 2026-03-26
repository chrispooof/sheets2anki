from typing import Any


class RemoteDeck:
    def __init__(self):
        self.deck_name: str = ""
        self.notecards: list[dict[str, Any]] = []
