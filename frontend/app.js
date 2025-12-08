// FaceCheck - Applicazione di riconoscimento facciale
// Logica principale dell'applicazione

let stream = null;

// ==================== TEMA ====================

/**
 * Inizializza il tema salvato in localStorage
 */
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
        updateThemeIcon();
    }
}

/**
 * Cambia tra tema chiaro e scuro
 */
function toggleTheme() {
    document.body.classList.toggle('light-theme');
    const isLight = document.body.classList.contains('light-theme');
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
    updateThemeIcon();
}

/**
 * Aggiorna l'icona del tema (luna/sole)
 */
function updateThemeIcon() {
    const btn = document.querySelector('.theme-toggle');
    const isLight = document.body.classList.contains('light-theme');
    btn.textContent = isLight ? '☀️' : '🌙';
}

// ==================== NAVIGAZIONE ====================

/**
 * Cambia la schermata attiva
 * @param {string} screenName - ID della schermata da mostrare
 */
function switchScreen(screenName) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenName).classList.add('active');

    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    event?.target?.classList.add('active');

    if (screenName === 'live-scan') {
        startWebcam();
        simulateScan();
    } else {
        stopWebcam();
    }
}

// ==================== WEBCAM ====================

/**
 * Avvia la webcam e mostra lo stato di caricamento
 */
function startWebcam() {
    // Mostra stato di caricamento
    const loadingDiv = document.getElementById('video-loading');
    loadingDiv.classList.remove('hidden');

    navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user' },
        audio: false
    }).then(s => {
        stream = s;
        const videoElement = document.getElementById('webcam');
        videoElement.srcObject = stream;

        // Nasconde caricamento quando il video è pronto
        videoElement.onloadedmetadata = () => {
            loadingDiv.classList.add('hidden');
        };
    }).catch(e => {
        console.error('Errore:', e);
        loadingDiv.classList.add('hidden');
        alert('Impossibile accedere alla webcam');
    });
}

/**
 * Ferma la webcam e rilascia il stream
 */
function stopWebcam() {
    if (stream) {
        stream.getTracks().forEach(t => t.stop());
        stream = null;
    }
}

// ==================== SCANSIONE ====================

/**
 * Simula il processo di scansione facciale in 3 step
 */
function simulateScan() {
    const status = document.getElementById('scan-status');
    let step = 0;
    const interval = setInterval(() => {
        step++;
        if (step === 1) {
            status.textContent = 'Scansione in corso...';
        } else if (step === 2) {
            status.textContent = 'Volto rilevato, confronto...';
        } else if (step === 3) {
            clearInterval(interval);
            stopWebcam();
            Math.random() > 0.3 ? showSuccessResult() : showErrorResult();
        }
    }, 1500);
}

/**
 * Annulla la scansione in corso
 */
function cancelScan() {
    stopWebcam();
    switchScreen('home');
}

// ==================== RISULTATI ====================

/**
 * Mostra la schermata di successo con data e ora
 */
function showSuccessResult() {
    const now = new Date();
    document.getElementById('result-date').textContent = now.toLocaleDateString('it-IT', {day:'numeric', month:'long'});
    document.getElementById('result-time').textContent = now.toLocaleTimeString('it-IT', {hour:'2-digit', minute:'2-digit'});
    switchScreen('results-success');
    // Scroll ai risultati
    setTimeout(() => {
        document.getElementById('results-success').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
}

/**
 * Mostra la schermata di errore con data e ora
 */
function showErrorResult() {
    const now = new Date();
    document.getElementById('error-date').textContent = now.toLocaleDateString('it-IT', {day:'numeric', month:'long'});
    document.getElementById('error-time').textContent = now.toLocaleTimeString('it-IT', {hour:'2-digit', minute:'2-digit'});
    switchScreen('results-error');
    // Scroll ai risultati
    setTimeout(() => {
        document.getElementById('results-error').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
}

/**
 * Avvia una nuova scansione
 */
function newScan() {
    switchScreen('live-scan');
}

// ==================== INIZIALIZZAZIONE ====================

// Inizializza il tema al caricamento della pagina
document.addEventListener('DOMContentLoaded', initTheme);
