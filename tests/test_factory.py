"""Tests for the processor factory."""

import pytest

from app.processors import ProcessorFactory, ResizeProcessor


def test_factory_creates_resize_processor() -> None:
    processor = ProcessorFactory.create(" RESIZE ")

    assert isinstance(processor, ResizeProcessor)


def test_factory_rejects_unknown_operation() -> None:
    with pytest.raises(ValueError, match="Неизвестная операция"):
        ProcessorFactory.create("unknown")
