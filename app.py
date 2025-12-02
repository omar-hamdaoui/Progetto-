from flask import Flask, request, jsonify
import os
import tempfile

app = Flask(__name__)

# Lazy import face_recognition and numpy so the app can start even if deps fail to install
try:
    import face_recognition
    import numpy as np
except Exception as e:
    face_recognition = None
    np = None

KNOWN_FACES_DIR = os.environ.get('KNOWN_FACES_DIR', 'data/images')
THRESHOLD_DEFAULT = float(os.environ.get('FACE_MATCH_THRESHOLD', 0.6))

known_encodings = []
known_names = []


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg', 'png'}


def load_known_faces():
    """Scan KNOWN_FACES_DIR and compute face encodings for each image file.
    Filenames (without extension) are used as names.
    """
    global known_encodings, known_names
    known_encodings = []
    known_names = []

    if face_recognition is None:
        return {'error': 'face_recognition not available'}

    if not os.path.isdir(KNOWN_FACES_DIR):
        return {'error': f'Known faces directory not found: {KNOWN_FACES_DIR}'}

    for fname in os.listdir(KNOWN_FACES_DIR):
        if not allowed_file(fname):
            continue
        path = os.path.join(KNOWN_FACES_DIR, fname)
        try:
            image = face_recognition.load_image_file(path)
            encs = face_recognition.face_encodings(image)
            if not encs:
                # no face found in this image
                continue
            # use the first face encoding in the file
            known_encodings.append(encs[0])
            name = os.path.splitext(fname)[0]
            known_names.append(name)
        except Exception:
            # skip files that cannot be processed
            continue

    return {'loaded': len(known_names)}


@app.route('/health')
def health():
    return jsonify(status='ok')


@app.route('/')
def index():
    return 'Face Recognition Service in esecuzione'


@app.route('/faces', methods=['GET'])
def list_faces():
    return jsonify(names=known_names)


@app.route('/reload', methods=['POST'])
def reload_faces():
    result = load_known_faces()
    return jsonify(result)


@app.route('/recognize', methods=['POST'])
def recognize():
    if face_recognition is None:
        return jsonify({'error': 'face_recognition library not installed'}), 500

    if 'image' not in request.files:
        return jsonify({'error': 'no image file provided, use form field name "image"'}), 400

    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'invalid file type'}), 400

    threshold = float(request.form.get('threshold', THRESHOLD_DEFAULT))

    # Save to a temporary file and process
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1])
    try:
        file.save(tmp.name)
        image = face_recognition.load_image_file(tmp.name)
        locations = face_recognition.face_locations(image)
        encodings = face_recognition.face_encodings(image, locations)

        results = []
        for loc, enc in zip(locations, encodings):
            if known_encodings:
                dists = face_recognition.face_distance(known_encodings, enc)
                best_idx = int(np.argmin(dists))
                best_dist = float(dists[best_idx])
                if best_dist <= threshold:
                    name = known_names[best_idx]
                else:
                    name = 'Unknown'
            else:
                name = 'Unknown'
                best_dist = None

            results.append({
                'name': name,
                'distance': best_dist,
                'location': {'top': int(loc[0]), 'right': int(loc[1]), 'bottom': int(loc[2]), 'left': int(loc[3])}
            })

        return jsonify(results=results)
    finally:
        try:
            tmp.close()
            os.unlink(tmp.name)
        except Exception:
            pass


if __name__ == '__main__':
    # load known faces at startup
    load_known_faces()
    app.run(host='0.0.0.0', port=5000)
