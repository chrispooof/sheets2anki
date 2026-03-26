class RemoteDeckConfig:
    """Configuration for a single remote deck mapping.

    Attributes:
        url: Published CSV URL for the Google Sheet.
        deck_name: Target Anki deck name.
        note_type: Anki note type name to use for all cards in this deck.
        note_type_fields: Ordered list of field names defined by the note type.
        notecard_key_field: Primary field used to uniquely identify a notecard.
        notecard_additional_key_fields: Extra fields included in the composite key.
    """

    def __init__(self):
        self.url: str = ""
        self.deck_name: str = ""
        self.note_type: str = ""
        self.note_type_fields: list[str] = []
        self.notecard_key_field: str = ""
        self.notecard_additional_key_fields: list[str] = []
