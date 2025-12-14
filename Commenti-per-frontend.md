- List images: GET /images  -> returns [{filename, faces}]
- Serve image: GET /images/<filename>
- Recognize (file): POST /recognize (form-data, 'image' -> File, optional 'threshold')
- Upload persistent image: POST /upload (form-data, 'file' -> File) -> returns filename to use for later
- Compare files: POST /compare (json: {a:"a.jpg", b:"b.jpg"})
- Reload DB: POST /reload
- Error handling: check HTTP status & JSON 'error' field
- CORS: enable if frontend served on different origin (add flask-cors in dev if needed)

CANCELLA QUESTO FILE QUANDO HAI TERMINATO IL LAVORO