# modules/multimodal/__init__.py
# -*- coding: utf-8 -*-

"""
Multimodal Package.
===================

Exposes lazy wrappers for the main orchestrators to avoid importing heavy
runtime dependencies during lightweight operations (e.g. CLI --help).
"""

from __future__ import annotations

from typing import Any


def build_path_geometry(*args: Any, **kwargs: Any) -> dict:
    from modules.multimodal.builder import build_path_geometry as _build_path_geometry

    return _build_path_geometry(*args, **kwargs)


def evaluate_path(*args: Any, **kwargs: Any) -> dict:
    from modules.multimodal.evaluator import evaluate_path as _evaluate_path

    return _evaluate_path(*args, **kwargs)


__all__ = ["build_path_geometry", "evaluate_path"]
