"""Import-friendly wrapper for the FaceStore implementation."""

from __future__ import annotations

import importlib.util
import os
from types import ModuleType
from typing import Type


def _load_face_store_module() -> ModuleType:
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "face-store.py")

    spec = importlib.util.spec_from_file_location("face_store_impl", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load FaceStore module from {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_impl = _load_face_store_module()

FaceStore: Type = getattr(_impl, "FaceStore")

