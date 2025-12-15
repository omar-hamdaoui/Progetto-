import os
import face_recognition
import cv2
import numpy as np
import pickle

# Configurazioni
IMAGES_DIR = os.path.join(".", "data", "images")
ENC_CACHE_PATH = os.path.join(IMAGES_DIR, "encodings.pkl")
THRESHOLD_DEFAULT = 0.6

# Variabili globali per memorizzare le codifiche e i nomi
_known_encodings = []
_known_names = []

def load_images_from_directory():
    """
    Carica le immagini dalla directory e calcola le codifiche dei volti.
    """
    global _known_encodings, _known_names
    _known_encodings = []
    _known_names = []

    for filename in os.listdir(IMAGES_DIR):
        if filename.endswith((".jpg", ".jpeg", ".png")):
            path = os.path.join(IMAGES_DIR, filename)
            image = face_recognition.load_image_file(path)
            face_encodings = face_recognition.face_encodings(image)

            if face_encodings:
                # Usa solo il primo volto trovato nell'immagine
                _known_encodings.append(face_encodings[0])
                _known_names.append(os.path.splitext(filename)[0])

    # Salva le codifiche in cache (opzionale)
    try:
        with open(ENC_CACHE_PATH, "wb") as f:
            pickle.dump({"encodings": _known_encodings, "names": _known_names}, f)
    except Exception as e:
        print(f"Errore durante il salvataggio della cache: {e}")


def recognize_from_webcam():
    """
    Riconosce i volti dalla webcam e li confronta con quelli memorizzati.
    """
    # Carica le immagini dalla directory
    load_images_from_directory()

    # Crea un'istanza della webcam
    cap = cv2.VideoCapture(0)

    while True:
        # Cattura un frame dalla webcam
        ret, frame = cap.read()

        if not ret:
            print("Errore durante la cattura del frame")
            break

        # Converti il frame in RGB (face_recognition lavora con immagini RGB)
        rgb_frame = frame[:, :, ::-1]

        # Trova le posizioni dei volti nel frame
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        # Confronta i volti trovati con quelli memorizzati
        results = []
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(_known_encodings, face_encoding)
            name = "Unknown"

            # Se c'è una corrispondenza, usa il nome dell'immagine corrispondente
            if True in matches:
                first_match_index = matches.index(True)
                name = _known_names[first_match_index]

            results.append(name)

        # Mostra i risultati sullo schermo
        for (top, right, bottom, left), name in zip(face_locations, results):
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Mostra il frame con i risultati
        cv2.imshow('Webcam Face Recognition', frame)

        # Interrompi il ciclo se l'utente preme 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Rilascia la webcam e chiudi tutte le finestre
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    # Avvia il riconoscimento facciale dalla webcam
    recognize_from_webcam()
