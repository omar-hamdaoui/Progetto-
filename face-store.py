"""
Optional helper module that encapsulates face store operations.
This file can be imported by tests or other scripts to interact with
the on-disk images and encodings logic without going through HTTP.
Keeps logic modular for easier unit testing.
"""
import os
import pickle
from typing import Tuple, List, Optional

try:
    import face_recognition
    import numpy as np
except Exception:
    face_recognition = None
    np = None

class FaceStore:
    def __init__(self, images_dir: str, cache_path: Optional[str] = None):
        self.images_dir = images_dir
        self.cache_path = cache_path
        self.encodings = []
        self.names = []
        self.meta = {}

    def load_cache(self) -> bool:
        if not self.cache_path or not os.path.exists(self.cache_path):
            return False
        try:
            with open(self.cache_path, "rb") as f:
                data = pickle.load(f)
            self.encodings = data.get("encodings", [])
            self.names = data.get("names", [])
            self.meta = data.get("meta", {})
            return True
        except Exception:
            return False

    def save_cache(self):
        if not self.cache_path:
            return
        try:
            with open(self.cache_path, "wb") as f:
                pickle.dump({"encodings": self.encodings, "names": self.names, "meta": self.meta}, f)
        except Exception:
            pass

    def build_from_disk(self) -> int:
        if face_recognition is None:
            raise RuntimeError("face_recognition missing")
        encs = []
        names = []
        meta = {}
        files = sorted(os.listdir(self.images_dir))
        for fname in files:
            if not ('.' in fname and fname.rsplit('.', 1)[1].lower() in {'jpg','jpeg','png'}):
                continue
            path = os.path.join(self.images_dir, fname)
            image = face_recognition.load_image_file(path)
            face_encs = face_recognition.face_encodings(image)
            if not face_encs:
                meta[fname] = {"faces": 0}
                continue
            encs.append(face_encs[0])
            names.append(os.path.splitext(fname)[0])
            meta[fname] = {"faces": len(face_encs)}
        self.encodings = encs
        self.names = names
        self.meta = meta
        self.save_cache()
        return len(self.names)

    def compare_files(self, a: str, b: str) -> float:
        pa = os.path.join(self.images_dir, a)
        pb = os.path.join(self.images_dir, b)
        enc_a = face_recognition.face_encodings(face_recognition.load_image_file(pa))[0]
        enc_b = face_recognition.face_encodings(face_recognition.load_image_file(pb))[0]
        return float(face_recognition.face_distance([enc_a], enc_b)[0])