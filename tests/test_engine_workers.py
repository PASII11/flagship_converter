"""Ограничение параллелизма движка."""
from flagship_converter.core.engine import ConversionEngine


def test_default_unlimited():
    engine = ConversionEngine()
    assert engine._effective_workers(8) == 8


def test_cap_applies():
    engine = ConversionEngine(max_workers=2)
    assert engine._effective_workers(8) == 2
    assert engine._effective_workers(1) == 1


def test_zero_or_negative_means_auto():
    assert ConversionEngine(max_workers=0)._effective_workers(6) == 6
