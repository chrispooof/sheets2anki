import logging

logger = logging.getLogger("sheets2anki")


def configure(debug: bool) -> None:
    """Set the package log level based on the debug config flag."""
    level = logging.DEBUG if debug else logging.WARNING
    logger.setLevel(level)
    if debug and not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
