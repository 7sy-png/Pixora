"""Utilities for displaying file information."""


def format_file_size(size_bytes: int) -> str:
    """Format a byte count with a compact binary unit."""
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024

    raise AssertionError("Unreachable file-size unit")
