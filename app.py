#!/usr/bin/env python3
"""
Face Recognition Backend (Flask)

Endpoints:
- GET  /health
- GET  /ready
- GET  /images
- GET  /images/<filename>
- POST /upload        (multipart/form-data, field 'file') -> saves image in data/images and updates cache
- DELETE /images/<filename>
- POST /reload        -> reloads encodings from disk
- POST /recognize     (multipart/form-data, field 'image', optional 'threshold') -> returns matches for faces found
- POST /compare       (JSON body: { "a": "fileA.jpg", "b": "fileB.jpg", "threshold": 0.6 })
"""

import os
import threading
import logging
import tempfile
import pickle
import json
from datetime import datetime, timezone
from typing import List, Tuple, Optional

from flask import Flask, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename

try:
    from face_store import FaceStore
except Exception:
    FaceStore = None

# Lazy imports (app can start even if face_recognition not installed)
try:
    import face_recognition
    import numpy as np
except Exception:
    face_recognition = None
    np = None

# Config (can be overridden by environment)
IMAGES_DIR = os.environ.get("KNOWN_FACES_DIR", "data/images")
ENC_CACHE_PATH = os.environ.get("ENCODINGS_CACHE_PATH", os.path.join(IMAGES_DIR, "encodings.pkl"))
THRESHOLD_DEFAULT = float(os.environ.get("FACE_MATCH_THRESHOLD", 0.6))
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", 8))
MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
REGISTRY_PATH = os.environ.get("REGISTRY_PATH", "data/registry.json")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Ensure directories exist
os.makedirs(IMAGES_DIR, exist_ok=True)


def _load_registry() -> list:
    if not os.path.exists(REGISTRY_PATH):
        return []
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _append_registry(entry: dict) -> None:
    os.makedirs(os.path.dirname(REGISTRY_PATH) or ".", exist_ok=True)
    items = _load_registry()
    items.insert(0, entry)
    try:
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


@app.route("/", methods=["GET"])
def frontend_index():
    return send_from_directory(FRONTEND_DIR, "tmpl.html")


@app.route("/style.css", methods=["GET"])
def frontend_style():
    return send_from_directory(FRONTEND_DIR, "style.css")


@app.route("/app.js", methods=["GET"])
def frontend_appjs():
    return send_from_directory(FRONTEND_DIR, "app.js")


@app.route("/LOGO FaceCheck.png", methods=["GET"])
def frontend_logo():
    return send_from_directory(BASE_DIR, "LOGO FaceCheck.png")


@app.route("/api/registry", methods=["GET"])
def api_registry():
    return jsonify(items=_load_registry())


@app.route("/api/rebuild", methods=["POST"])
def api_rebuild():
    result = build_cache_from_disk()
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# Logging
logger = logging.getLogger("face_backend")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

# Thread-safe globals for known encodings and names
_lock = threading.RLock()
_known_encodings: List = []
_known_names: List[str] = []
_known_meta: dict = {}  # filename -> metadata (e.g. faces count)

ALLOWED_EXT = {"jpg", "jpeg", "png"}

_store = None
if FaceStore is not None:
    try:
        _store = FaceStore(images_dir=IMAGES_DIR, cache_path=ENC_CACHE_PATH)
        _store.load_cache()
    except Exception:
        _store = None


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def save_cache(path: str) -> None:
    try:
        with open(path, "wb") as f:
            with _lock:
                pickle.dump({"encodings": _known_encodings, "names": _known_names, "meta": _known_meta}, f)
        logger.info("Encodings cache saved to %s", path)
    except Exception as e:
        logger.warning("Failed to save encodings cache: %s", e)


def load_cache(path: str) -> bool:
    if not os.path.exists(path):
        return False
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
        with _lock:
            global _known_encodings, _known_names, _known_meta
            _known_encodings = data.get("encodings", [])
            _known_names = data.get("names", [])
            _known_meta = data.get("meta", {})
        logger.info("Loaded encodings cache from %s", path)
        return True
    except Exception as e:
        logger.warning("Failed to load encodings cache: %s", e)
        return False


def build_cache_from_disk() -> dict:
    """
    Scan IMAGES_DIR, compute encodings (first face per file), populate globals.
    Returns: dict with loaded count or error
    """
    if face_recognition is None:
        return {"error": "face_recognition not available"}

    # Prefer the helper FaceStore (from face-store.py) when available.
    if _store is not None:
        try:
            loaded = _store.build_from_disk()
            with _lock:
                global _known_encodings, _known_names, _known_meta
                _known_encodings = list(_store.encodings)
                _known_names = list(_store.names)
                _known_meta = dict(_store.meta)
            logger.info("Loaded %d known faces (FaceStore)", loaded)
            return {"loaded": int(loaded)}
        except Exception as e:
            logger.warning("FaceStore build failed, falling back: %s", e)

    encs = []
    names = []
    meta = {}
    files = sorted(os.listdir(IMAGES_DIR))
    for fname in files:
        if not allowed_file(fname):
            continue
        path = os.path.join(IMAGES_DIR, fname)
        try:
            image = face_recognition.load_image_file(path)
            face_encodings = face_recognition.face_encodings(image)
            if not face_encodings:
                meta[fname] = {"faces": 0}
                continue
            # default: use the first face found in the file
            encs.append(face_encodings[0])
            names.append(os.path.splitext(fname)[0])
            meta[fname] = {"faces": len(face_encodings)}
        except Exception as e:
            logger.warning("Skipping %s: %s", fname, str(e))
            continue

    with _lock:
        global _known_encodings, _known_names, _known_meta
        _known_encodings = encs
        _known_names = names
        _known_meta = meta

    # persist cache if path provided
    try:
        save_cache(ENC_CACHE_PATH)
    except Exception:
        pass

    logger.info("Loaded %d known faces", len(names))
    return {"loaded": len(names)}


# Try loading cache at startup (best-effort)
load_cache(ENC_CACHE_PATH)
if not _known_encodings:
    # background initial scan on first run (synchronous here for simplicity)
    build_cache_from_disk()


@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok")


@app.route("/ready", methods=["GET"])
def ready():
    ready_state = (face_recognition is not None)
    return jsonify(ready=ready_state)


@app.route("/images", methods=["GET"])
def list_images():
    # return metadata for images discovered in IMAGES_DIR (and in cache meta)
    with _lock:
        meta = dict(_known_meta)  # copy
    # include files that may not be in meta (e.g. new images)
    for fname in sorted(os.listdir(IMAGES_DIR)):
        if not allowed_file(fname):
            continue
        if fname not in meta:
            meta[fname] = {"faces": None}
    images = [{"filename": fname, "faces": int(meta[fname]["faces"]) if meta[fname].get("faces") is not None else None}
              for fname in sorted(meta.keys())]
    return jsonify(images=images)


@app.route("/images/<path:filename>", methods=["GET"])
def get_image(filename):
    # Serve the image file from IMAGES_DIR; frontend can use this to fetch thumbnails/full images
    if not allowed_file(filename):
        abort(404)
    return send_from_directory(IMAGES_DIR, filename, as_attachment=False)


@app.route("/upload", methods=["POST"])
def upload_image():
    """
    Save an uploaded image into IMAGES_DIR and compute its encoding, updating the cache.
    Form field: 'file'
    """
    if face_recognition is None:
        return jsonify({"error": "face_recognition not installed"}), 500

    if "file" not in request.files:
        return jsonify({"error": "no file provided; use form field 'file'"}), 400

    f = request.files["file"]
    if f.filename == "" or not allowed_file(f.filename):
        return jsonify({"error": "invalid file type"}), 400

    safe_name = secure_filename(f.filename)
    # avoid collisions: if exists, append numeric suffix
    base, ext = os.path.splitext(safe_name)
    dest_name = safe_name
    i = 1
    while os.path.exists(os.path.join(IMAGES_DIR, dest_name)):
        dest_name = f"{base}_{i}{ext}"
        i += 1
    dest_path = os.path.join(IMAGES_DIR, dest_name)
    f.save(dest_path)

    # compute encoding for the saved file and update cache
    try:
        image = face_recognition.load_image_file(dest_path)
        encs = face_recognition.face_encodings(image)
        faces_count = len(encs)
        with _lock:
            if encs:
                _known_encodings.append(encs[0])
                _known_names.append(os.path.splitext(dest_name)[0])
            _known_meta[dest_name] = {"faces": faces_count}

        if _store is not None:
            try:
                # Keep FaceStore cache aligned (best-effort).
                _store.encodings = list(_known_encodings)
                _store.names = list(_known_names)
                _store.meta = dict(_known_meta)
                _store.save_cache()
            except Exception:
                pass
        save_cache(ENC_CACHE_PATH)
        return jsonify({"filename": dest_name, "saved": True, "faces": faces_count}), 201
    except Exception as e:
        logger.exception("Failed to process uploaded image")
        return jsonify({"error": "failed to process uploaded image"}), 500


@app.route("/images/<path:filename>", methods=["DELETE"])
def delete_image(filename):
    if not allowed_file(filename):
        return jsonify({"error": "invalid filename"}), 400
    path = os.path.join(IMAGES_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"error": "not found"}), 404

    # remove file and remove from cache if present
    try:
        os.remove(path)
    except Exception as e:
        logger.warning("Failed to remove %s: %s", path, e)
        return jsonify({"error": "failed to delete file"}), 500

    # rebuild cache (safe and simple) — inexpensive for small datasets
    result = build_cache_from_disk()
    return jsonify({"deleted": True, "reloaded": result})


@app.route("/reload", methods=["POST"])
def reload_endpoint():
    result = build_cache_from_disk()
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@app.route("/compare", methods=["POST"])
def compare_endpoint():
    """
    Compare two images existing in IMAGES_DIR.
    JSON body: {"a": "fileA.jpg", "b": "fileB.jpg", "threshold": 0.6}
    """
    if face_recognition is None:
        return jsonify({"error": "face_recognition not installed"}), 500
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "invalid json body"}), 400

    if not data or "a" not in data or "b" not in data:
        return jsonify({"error": "provide 'a' and 'b' filenames"}), 400

    a = data["a"]
    b = data["b"]
    threshold = float(data.get("threshold", THRESHOLD_DEFAULT))

    path_a = os.path.join(IMAGES_DIR, a)
    path_b = os.path.join(IMAGES_DIR, b)
    if not os.path.exists(path_a) or not os.path.exists(path_b):
        return jsonify({"error": "file not found"}), 404

    try:
        if _store is not None:
            dist = float(_store.compare_files(a, b))
        else:
            enc_a = face_recognition.face_encodings(face_recognition.load_image_file(path_a))[0]
            enc_b = face_recognition.face_encodings(face_recognition.load_image_file(path_b))[0]
            dist = float(face_recognition.face_distance([enc_a], enc_b)[0])
    except Exception as e:
        return jsonify({"error": f"cannot encode images: {str(e)}"}), 400

    return jsonify({"a": a, "b": b, "distance": dist, "match": dist <= threshold})


@app.route("/recognize", methods=["POST"])
def recognize():
    """
    Recognize faces in an uploaded image file.
    Form-data:
      - image: file
      - threshold: optional float
    Response: results list with {name, distance, location}
    """
    if face_recognition is None:
        return jsonify({"error": "face_recognition not installed"}), 500

    if "image" not in request.files:
        return jsonify({"error": 'no image file provided, use form field name "image"'}), 400

    file = request.files["image"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "invalid file type"}), 400

    threshold = float(request.form.get("threshold", THRESHOLD_DEFAULT))

    filename = secure_filename(file.filename)
    with tempfile.TemporaryDirectory() as td:
        tmp_path = os.path.join(td, filename)
        file.save(tmp_path)
        try:
            image = face_recognition.load_image_file(tmp_path)
            locations = face_recognition.face_locations(image)
            encodings = face_recognition.face_encodings(image, locations)
        except Exception as e:
            logger.exception("Error processing uploaded image")
            return jsonify({"error": "cannot process image"}), 400

    results = []
    with _lock:
        known_encs = list(_known_encodings)
        known_names = list(_known_names)

    for loc, enc in zip(locations, encodings):
        if known_encs:
            dists = face_recognition.face_distance(known_encs, enc)
            best_idx = int(np.argmin(dists))
            best_dist = float(dists[best_idx])
            name = known_names[best_idx] if best_dist <= threshold else "Unknown"
        else:
            name = "Unknown"
            best_dist = None

        results.append({
            "name": name,
            "distance": best_dist,
            "location": {"top": int(loc[0]), "right": int(loc[1]), "bottom": int(loc[2]), "left": int(loc[3])}
        })

    # Save a lightweight attendance entry for the first face (if any)
    if results:
        first = results[0]
        ts = datetime.now(timezone.utc).isoformat()
        _append_registry({
            "ts": ts,
            "name": None if first.get("name") in (None, "Unknown") else first.get("name"),
            "status": "ok" if first.get("name") not in (None, "Unknown") else "fail",
            "distance": first.get("distance"),
        })

    return jsonify(results=results)


if __name__ == "__main__":
    # Load cache / build cache before serving
    load_cache(ENC_CACHE_PATH)
    if not _known_encodings:
        build_cache_from_disk()
    # Flask dev server (for production use gunicorn)
    app.run(host="0.0.0.0", port=5000)