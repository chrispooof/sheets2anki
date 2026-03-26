"""Package-level logger for sheets2anki, with optional debug output to stderr."""

import logging

logger = logging.getLogger("sheets2anki")


def configure(debug: bool) -> None:
    """Set the package log level based on the debug config flag.
    Args:
        debug (bool): If True, set log level to DEBUG, else WARNING.
    """
    level = logging.DEBUG if debug else logging.WARNING
    logger.setLevel(level)
    if debug and not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
