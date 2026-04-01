# Advanced Interview Proctoring: Technical Overview

This document provides a comprehensive breakdown of the internal architecture, machine learning logic, and functional workflows of the interview proctoring MVP. It is structured to help management understand the security, efficiency, and capabilities of the platform.

## 1. Core Technologies & ML Agents Used

The proctoring system is entirely **client-side**, meaning all machine learning models execute directly within the candidate's browser rather than requiring expensive cloud GPUs.

We utilize three distinct monitoring layers:

### A. Gaze Tracking (WebGazer & MediaPipe)
*   **What we use:** We implemented **WebGazer.js**, backed by Google's **MediaPipe Face Mesh**.
*   **How it works:** Under the hood, it loads a highly optimized WebAssembly (WASM) computer vision model. This model rapidly detects 468 3D facial landmarks on the candidate's face via the webcam.
*   **Calibration:** The system maps the physical location of the candidate's pupils to specific X/Y coordinate pixels on the screen. By clicking on various screen points during setup, the AI trains a real-time regression model unique to that candidate's eyes and monitor size.

### B. Environmental Analysis (Canvas Pixel Processing)
*   **What we use:** HTML5 `<canvas>` and raw pixel manipulation.
*   **How it works:** The system secretly captures frames from the webcam feed multiple times a second. It calculates the rolling average of room brightness and specifically isolates the "Blue" light channel. If a candidate suddenly looks down and their face is illuminated by a sharp spike in blue light, the system flags it as a potential unauthorized mobile device.

### C. Voice Malpractice (Web Speech API)
*   **What we use:** The native browser `SpeechRecognition` API.
*   **How it works:** The system actively listens for spoken words. It takes the transcribed audio and runs a **Similarity Index Score** against the text of the actual interview question on screen. If the candidate is reading the exact question out loud (often done to feed text to a hidden recording device or person), it triggers an infraction.

---

## 2. Why This is Highly Efficient

*   **Zero Server Costs for ML:** Because MediaPipe is compiled to WebAssembly, the heavy AI processing happens on the candidate's own CPU/GPU. We do not have to pay cloud computing costs (like AWS or Azure) to run computer vision models.
*   **Privacy-First Architecture:** Since the processing happens in the browser, no video feeds or audio recordings need to be transmitted over the internet or saved to our servers. This heavily mitigates GDPR and data privacy compliance risks!
*   **Ultra-Low Latency:** Real-time feedback happens in milliseconds without network delay.

---

## 3. Candidate Evaluation & Disqualification Rules

We enforce a **10-Strike Rule** to ensure fairness and prevent false positives from disqualifying honest candidates.

**What triggers flags:**
1.  **Look-Away Times:** Looking entirely off-screen for more than 3 continuous seconds.
2.  **Danger Zones:** Looking downward (lap/phone area) for more than 3 continuous seconds.
3.  **Blue Light Spikes:** Rapid illumination indicative of a secondary screen.
4.  **Dictation Detection:** Reading the test question aloud in the vicinity of the microphone.

**The Workflow:**
*   Each detected offense adds a strike to the candidate's active session.
*   If the candidate hits **10 total infractions**, the session strictly executes a `DISQUALIFIED` lock-out state. 
*   The system blurs the test and disables all inputs.

---

## 4. Where are Logs Stored & How are Flags Recorded?

### Currently (MVP Phase)
Right now, the system operates entirely in **volatile memory**. 
*   Every time an infraction occurs, it is pushed to the Javascript state and immediately rendered in the right-hand **Activity Logs** UI panel for the proctor to see live. 
*   It also tracks the exact `X, Y` coordinates in the **Live Gaze Data** UI.
*   When the browser tab is closed, the session is cleared.

### Production Phase Next Steps
To make this enterprise-ready, we must capture these flags to evaluate the candidate retroactively. The immediate next requirement would be to route this data to a database:
1.  **WebSocket Integration:** The client code will emit secure JSON payloads containing the timestamp, infraction type, and severity over WebSockets.
2.  **Database Storage:** A backend (e.g., Node.js with PostgreSQL/MongoDB) will append these flags to the candidate's distinct ID.
3.  **Proctor Review:** When HR or the hiring manager views the candidate's completed test, they will see a timeline log (e.g., `[14:22:01] - Candidate looked at lap for 6s`) to aid in the final hiring decision.
