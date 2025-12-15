"""Import-friendly wrapper for the FaceStore implementation.

The original file is named `face-store.py` (with a hyphen), which cannot be
imported as a normal Python module. This wrapper loads it via importlib and
re-exports `FaceStore`.
"""

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
