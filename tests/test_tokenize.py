"""Tests for the JavaScript tokenizer (``src.tokenize_js.tokenize``)."""

import pytest

from .helpers import TokenizeError, tokenize
from .cases.tokenize import TOKENIZE_CASES
from .cases.exports import EXPORT_CASES
from .cases.imports import IMPORT_CASES


def _as_params(cases):
    return [pytest.param(c, id=c.id) for c in cases]


@pytest.mark.parametrize("case", _as_params(TOKENIZE_CASES))
def test_tokenize(case):
    if case.error:
        with pytest.raises(TokenizeError):
            tokenize(case.source)
        return

    tokens = tokenize(case.source)

    # The tokenizer must be lossless: token values re-join to the source.
    assert "".join(t.value for t in tokens) == case.source

    if case.expected:
        assert [(t.kind, t.value) for t in tokens] == list(case.expected)


# Every valid JS snippet used anywhere in the suite must round-trip losslessly.
_LOSSLESS_SOURCES = (
    [c.source for c in EXPORT_CASES]
    + [c.source for c in IMPORT_CASES]
    + [c.source for c in TOKENIZE_CASES if not c.error]
)


@pytest.mark.parametrize(
    "source",
    _LOSSLESS_SOURCES,
    ids=[f"lossless_{i}" for i in range(len(_LOSSLESS_SOURCES))],
)
def test_tokenize_lossless(source):
    tokens = tokenize(source)
    assert "".join(t.value for t in tokens) == source
