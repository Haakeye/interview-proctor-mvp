# GazeGuard: AI Interview Proctoring Platform

![GazeGuard Banner](https://img.shields.io/badge/Security-AI%20Proctoring-blue?style=for-the-badge) ![MediaPipe](https://img.shields.io/badge/AI-MediaPipe-orange?style=for-the-badge) ![Client Side](https://img.shields.io/badge/Architecture-100%25%20Client--Side-brightgreen?style=for-the-badge)

<br/>
<p align="center">
  <img src="demo.gif" alt="GazeGuard Demo UI in Action" width="800">
</p>
<br/>
**GazeGuard** is an advanced, privacy-first interview proctoring Minimum Viable Product (MVP). Built entirely on client-side technologies, it leverages Google's **MediaPipe Face Mesh** and geometric pupil-tracking regression to detect behavioral malpractice in real-time—at zero cloud computing cost.

## 🚀 Key Features

*   **Stable Iris Tracking:** Utilizing a pure 4-feature geometric vector to map pupil ratios to screen coordinates, eliminating facial landmark "wobble" over time.
*   **Zero-Latency Client-Side Inference:** All AI models compile directly in the browser via WebAssembly, guaranteeing user privacy (no video is transmitted) and removing server ML costs.
*   **Environmental Context Analysis:** Captures and evaluates ambient light to detect sudden luminance shifts (e.g., hidden mobile screens or unauthorized digital surfaces).
*   **Suspicious Speech Detection:** Uses the native Web Speech API to compute fuzzy text similarities and cross-reference candidate speech with the on-screen examination question.
*   **Glassmorphic UI Engine:** Features a modern, non-intrusive Dark Mode dashboard that alerts proctors in real-time.

## 🧠 The 10-Strike Malpractice Mechanism

To ensure an ethical candidate experience, GazeGuard enforces strict strike mechanisms rather than immediate automated failure.
*   **Danger Zones:** Automatically flags candidates staring at off-screen laps/desk areas longer than 3 continuous seconds.
*   **Visual Displacement:** Identifies when the candidate's focus is fully off-screen.
*   **Disqualification State:** If a session breaches 10 cumulative strikes, the system issues a final lockdown, alerting human proctors.

## 🛠 Tech Stack
*   **Frontend GUI:** HTML5, Vanilla JavaScript, CSS3
*   **Gaze AI Engine:** MediaPipe Face Mesh, WebGazer.js
*   **Environment Compute:** HTML5 Canvas Context (willReadFrequently channel tracking)

## 🏁 Getting Started

1. Clone the repository.
2. Launch a local web server (e.g. `python -m http.server 8000`).
3. Allow camera permissions and follow the 9-point calibration.
4. Experience real-time tracking!

---
> *Developed as an Enterprise-ready MVP to modernize and secure remote talent acquisition.*
