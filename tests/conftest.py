"""Mock Anki modules so remote_decks can be imported without Anki installed."""

import sys
from unittest.mock import MagicMock

# Stub out every Anki module the package imports at module-level
for mod in [
    "anki",
    "anki.collection",
    "aqt",
    "aqt.qt",
    "aqt.utils",
]:
    sys.modules.setdefault(mod, MagicMock())
