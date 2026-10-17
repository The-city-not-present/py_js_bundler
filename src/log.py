"""Logging for the bundler.

All output goes through the single ``py_js_bundler`` logger:

* the detailed per-module trace is logged at DEBUG level (silent by default);
* warnings (e.g. a config file that failed to parse) are logged at WARNING.

Raise the verbosity from the caller with :func:`configure` (``0`` = warnings
only, ``1`` = info, ``2``+ = debug), or pass ``verbosity`` in the ``config``
dict accepted by ``src.run.process``.
"""

import logging

LOGGER_NAME = "py_js_bundler"

logger = logging.getLogger(LOGGER_NAME)


def configure(verbosity=0):
    """Set the bundler's verbosity.

    * ``0`` (default): warnings only — the detailed debug trace is silent.
    * ``1``: info messages.
    * ``2`` and above: debug messages (the detailed per-module trace).

    When ``verbosity >= 1`` the logger writes to stderr directly, so the output
    appears regardless of the host application's logging configuration.
    """
    levels = {0: logging.WARNING, 1: logging.INFO}
    level = levels.get(verbosity, logging.DEBUG)

    logger.setLevel(level)
    logger.propagate = verbosity == 0

    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    if verbosity >= 1:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(handler)
