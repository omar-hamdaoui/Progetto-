from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify(status='ok')

@app.route('/')
def index():
    return 'Face Recognition Service in esecuzione'

if __name__ == '__main__':
    # Avvia il server Flask sulla porta 5000 esposta nel Dockerfile
    app.run(host='0.0.0.0', port=5000)
