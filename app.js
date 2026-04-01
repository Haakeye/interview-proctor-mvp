// ====== STATE & CONFIG ======
const CONFIG = {
    gazeDangerThresholdMs: 3000, 
    speechSimilarityThreshold: 0.6, // lowered slightly to be more robust
};

const STATE = {
    isProctoring: false,
    offScreenTimer: null,
    inDangerTimer: null,
    lastGazeArea: null,
    baselineBlue: null,
    baselineBrightness: null,
    speechTranscript: '',
    malpracticeFlags: 0,
    isDisqualified: false,
    lastLogTime: 0
};

// ====== DOM ELEMENTS ======
const els = {
    startBtn: document.getElementById('start-btn'),
    statusIndicator: document.getElementById('status-indicator'),
    activityLogs: document.getElementById('activity-logs'),
    alertOverlay: document.getElementById('alert-overlay'),
    alertReason: document.getElementById('alert-reason'),
    dismissBtn: document.getElementById('dismiss-btn'),
    questionArea: document.getElementById('question-area'),
    optionsArea: document.getElementById('options-area'),
    dangerArea: document.getElementById('danger-area'),
    questionText: document.getElementById('question-text'),
    envCanvas: document.getElementById('env-canvas')
};

// ====== LOGGING SYSTEM ======
function logEvent(message, isAlert = false) {
    const li = document.createElement('li');
    if (isAlert) li.className = 'malpractice';
    const now = new Date();
    const timeStr = now.getHours().toString().padStart(2, '0') + ':' + 
                    now.getMinutes().toString().padStart(2, '0') + ':' + 
                    now.getSeconds().toString().padStart(2, '0');
    
    li.innerHTML = `<span class="timestamp">${timeStr}</span> ${message}`;
    els.activityLogs.prepend(li);
    if (els.activityLogs.children.length > 20) {
        els.activityLogs.removeChild(els.activityLogs.lastChild);
    }
}

function triggerAlert(reason) {
    if (!STATE.isProctoring || STATE.isDisqualified) return;
    
    STATE.malpracticeFlags++;
    document.getElementById('flag-counter').innerText = STATE.malpracticeFlags;
    
    if (STATE.malpracticeFlags >= 10) {
        logEvent(`FINAL ALERT: Candidate Disqualified!`, true);
        els.statusIndicator.className = 'status alert';
        els.statusIndicator.innerText = 'DISQUALIFIED';
        document.body.classList.add('alert-mode');
        
        document.getElementById('alert-title').innerText = "🚫 CANDIDATE DISQUALIFIED 🚫";
        els.alertReason.innerText = "Exceeded 10 malpractice infractions. The session is terminated.";
        els.alertOverlay.classList.remove('hidden');
        els.dismissBtn.style.display = 'none'; // Cannot dismiss
        STATE.isDisqualified = true;
        STATE.isProctoring = false;
        return;
    }
    
    logEvent(`ALERT: ${reason}`, true);
    els.statusIndicator.className = 'status alert';
    els.statusIndicator.innerText = 'Malpractice Detected';
    document.body.classList.add('alert-mode');
    
    els.alertReason.innerText = reason;
    els.alertOverlay.classList.remove('hidden');
}

function resetAlert() {
    els.statusIndicator.className = 'status safe';
    els.statusIndicator.innerText = 'Monitoring';
    document.body.classList.remove('alert-mode');
    els.alertOverlay.classList.add('hidden');
    clearTimeout(STATE.offScreenTimer);
    clearTimeout(STATE.inDangerTimer);
    STATE.offScreenTimer = null;
    STATE.inDangerTimer = null;
}

// ====== GAZE TRACKING (WEBGAZER) ======
function initWebGazer() {
    logEvent("Initializing Eye Tracking...");
    
    const gazeDot = document.getElementById('gaze-dot');

    webgazer.setGazeListener(function(data, elapsedTime) {
        if (!STATE.isProctoring) {
            gazeDot.style.opacity = '0';
            return;
        }
        
        if (data == null) {
            if (!STATE.offScreenTimer) {
                STATE.offScreenTimer = setTimeout(() => {
                    triggerAlert("Candidate looking completely off-screen!");
                }, CONFIG.gazeDangerThresholdMs);
            }
            gazeDot.style.opacity = '0';
            return;
        }

        if (STATE.offScreenTimer) {
            clearTimeout(STATE.offScreenTimer);
            STATE.offScreenTimer = null;
        }

        const x = Math.round(data.x);
        const y = Math.round(data.y);
        
        gazeDot.style.opacity = '1';
        gazeDot.style.transform = `translate(${x - 15}px, ${y - 15}px)`; // -15 for 30px dot center

        const questionRect = els.questionArea.getBoundingClientRect();
        const optionsRect = els.optionsArea.getBoundingClientRect();
        const dangerRect = Math.min(els.dangerArea.getBoundingClientRect().top, window.innerHeight * 0.7);

        let currentArea = 'Unknown';

        if (y >= dangerRect) {
            currentArea = 'Danger Zone';
            if (!STATE.inDangerTimer) {
                STATE.inDangerTimer = setTimeout(() => {
                    triggerAlert("Candidate looking in Danger Zone (Lap/Phone Area)!");
                }, CONFIG.gazeDangerThresholdMs);
            }
        } else {
            if (STATE.inDangerTimer) {
                clearTimeout(STATE.inDangerTimer);
                STATE.inDangerTimer = null;
            }
            if (y >= questionRect.top && y <= questionRect.bottom) {
                currentArea = 'Question';
            } else if (y >= optionsRect.top && y <= optionsRect.bottom) {
                currentArea = 'Options';
            } else {
                currentArea = 'Neutral';
            }
        }
        
        // Live UI Update
        document.getElementById('live-gaze-data').innerText = `X: ${x}, Y: ${y} | ${currentArea}`;
        
        if (currentArea !== STATE.lastGazeArea) {
            if (STATE.lastGazeArea !== null) {
                // Log all gaze area transitions continuously
                logEvent(`Gaze moved to: ${currentArea}`);
            }
            STATE.lastGazeArea = currentArea;
        }

    }).begin();

    webgazer.showVideoPreview(true).showPredictionPoints(false);
    
    const checkVideoInterval = setInterval(() => {
        const wgVideoContainer = document.getElementById('webgazerVideoContainer');
        if (wgVideoContainer) {
            const videoContainer = document.querySelector('.video-container');
            videoContainer.innerHTML = ''; 
            videoContainer.appendChild(wgVideoContainer);
            wgVideoContainer.style.position = 'absolute';
            wgVideoContainer.style.top = '0px';
            wgVideoContainer.style.left = '0px';
            wgVideoContainer.style.width = '100%';
            wgVideoContainer.style.height = '100%';
            wgVideoContainer.style.margin = '0';
            
            const videoElement = document.getElementById('webgazerVideoFeed');
            if(videoElement) {
                videoElement.style.width = '100%';
                videoElement.style.height = '100%';
                videoElement.style.objectFit = 'cover';
            }
            
            logEvent("Eye Tracking Ready. Click on screen to calibrate.");
            clearInterval(checkVideoInterval);
        }
    }, 500);
}

// ====== ENVIRONMENTAL DETECTION ======
function processVideoFrame() {
    if (!STATE.isProctoring) return;

    const videoElement = document.getElementById('webgazerVideoFeed');
    if (!videoElement || videoElement.videoWidth === 0) {
        setTimeout(processVideoFrame, 1000);
        return;
    }

    const canvas = els.envCanvas;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    
    canvas.width = 64; 
    canvas.height = 48;
    
    try {
        ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const data = imageData.data;

        let rSum = 0, gSum = 0, bSum = 0;
        const pixelCount = data.length / 4;

        for (let i = 0; i < data.length; i += 4) {
            rSum += data[i];
            gSum += data[i+1];
            bSum += data[i+2];
        }

        const rAvg = rSum / pixelCount;
        const gAvg = gSum / pixelCount;
        const bAvg = bSum / pixelCount;
        
        const brightness = (rAvg + gAvg + bAvg) / 3;

        if (STATE.baselineBlue === null) {
            STATE.baselineBlue = bAvg;
            STATE.baselineBrightness = brightness;
        } else {
            const minBrightnessCheck = 20; // Ignore completely dark rooms
            if (brightness > minBrightnessCheck) {
                const blueRatio = bAvg / (brightness + 1);
                const baselineBlueRatio = STATE.baselineBlue / (STATE.baselineBrightness + 1);

                if (brightness > STATE.baselineBrightness + 10 && blueRatio > baselineBlueRatio * 1.25) {
                    triggerAlert("Sudden blue-light increase! Possible phone screen.");
                    STATE.baselineBlue = bAvg;
                    STATE.baselineBrightness = brightness;
                }
            }
            
            // Adjust rolling average
            STATE.baselineBlue = STATE.baselineBlue * 0.95 + bAvg * 0.05;
            STATE.baselineBrightness = STATE.baselineBrightness * 0.95 + brightness * 0.05;
        }
    } catch (e) {
        // Tainted canvas sometimes on startup if video stream not fully ready
    }

    setTimeout(processVideoFrame, 500);
}

// ====== SPEECH RECOGNITION ======
function calculateSimilarity(str1, str2) {
    const w1 = str1.toLowerCase().replace(/[^a-z\s]/g, '').trim().split(/\s+/);
    const w2 = str2.toLowerCase().replace(/[^a-z\s]/g, '').trim().split(/\s+/);
    if(w1.length === 0 || w2.length === 0) return 0;
    
    let matches = 0;
    w1.forEach(word => {
        if (word.length > 2 && w2.includes(word)) matches++;
    });
    
    return matches / Math.min(w1.length, w2.length);
}

function initSpeechRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
        logEvent("Speech Recognition not supported in this browser overlay/agent mode.");
        return;
    }

    const recognition = new SpeechRec();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
        if (!STATE.isProctoring) return;

        let finalTranscriptChunk = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
                finalTranscriptChunk += event.results[i][0].transcript;
            }
        }

        if (finalTranscriptChunk.trim().length > 0) {
            const qText = els.questionText.innerText;
            const sim = calculateSimilarity(finalTranscriptChunk, qText);
            
            if (sim > CONFIG.speechSimilarityThreshold && STATE.lastGazeArea === 'Question') {
                triggerAlert("Candidate is reading the question out loud!");
            } else if (sim > 0 && finalTranscriptChunk.length > 10) {
                 logEvent("Speech detected.");
            }
        }
    };

    recognition.onerror = (e) => console.log("Speech Rec Err:", e.error);
    
    try {
        recognition.start();
        logEvent("Voice activity monitoring started.");
    } catch(e) {}
}

// ====== EVENT LISTENERS ======
els.startBtn.addEventListener('click', () => {
    if (!STATE.isProctoring) {
        STATE.isProctoring = true;
        els.startBtn.innerText = "Stop Proctoring";
        els.startBtn.style.background = "var(--accent-red)";
        els.statusIndicator.className = 'status safe';
        els.statusIndicator.innerText = 'Monitoring';
        logEvent("Proctoring session live.");
        
        if (!window.webgazerInitialized) {
            initWebGazer();
            initSpeechRecognition();
            window.webgazerInitialized = true;
            setTimeout(processVideoFrame, 2000); // Startup delay
        }
    } else {
        STATE.isProctoring = false;
        els.startBtn.innerText = "Start Proctoring";
        els.startBtn.style.background = "var(--accent-blue)";
        els.statusIndicator.className = 'status';
        els.statusIndicator.innerText = 'Offline';
        logEvent("Proctoring session paused.");
        const gazeDot = document.getElementById('gaze-dot');
        if(gazeDot) gazeDot.style.opacity = '0';
    }
});

els.dismissBtn.addEventListener('click', () => {
    resetAlert();
    logEvent("Alert acknowledged by proctor.");
});
