"""Tests for logging configuration (``src.log``)."""

import logging

import pytest

from ..src.log import configure, logger
from ..src.run import process


@pytest.fixture(autouse=True)
def _reset_logger():
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    logger.propagate = True
    yield
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    logger.propagate = True


def _write_project(tmp_path):
    files = {
        "jsconfig.json": "{}",
        "src/main.js": "export const ok = 1;\n",
    }
    for rel, content in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return tmp_path / "src" / "main.js"


def test_configure_default_is_warning_level():
    configure(0)
    assert logger.level == logging.WARNING
    assert logger.propagate is True
    assert not logger.handlers


def test_configure_debug_level():
    configure(2)
    assert logger.level == logging.DEBUG
    assert logger.propagate is False
    assert len(logger.handlers) == 1


def test_process_is_silent_by_default(tmp_path, capsys):
    process(_write_project(tmp_path))
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_process_verbose_with_verbosity(tmp_path, capsys):
    process(_write_project(tmp_path), {"verbosity": 2})
    captured = capsys.readouterr()
    assert "[DEBUG-discovery]" in captured.err
