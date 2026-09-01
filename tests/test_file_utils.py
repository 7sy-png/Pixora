"""Tests for human-readable file-size formatting."""

import pytest

from app.utils.file_utils import format_file_size


@pytest.mark.parametrize(
    ("size_bytes", "expected"),
    [
        (0, "0 B"),
        (1023, "1023 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1024**2, "1.0 MB"),
        (1024**3, "1.0 GB"),
    ],
)
def test_format_file_size_uses_binary_units(
    size_bytes: int,
    expected: str,
) -> None:
    assert format_file_size(size_bytes) == expected
