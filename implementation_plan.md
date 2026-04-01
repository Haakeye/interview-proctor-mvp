# HRM Interview Proctoring MVP

This plan outlines the approach to building a premium, web-based interview proctoring system that detects candidate malpractice using gaze tracking, environmental light monitoring, and speech analysis.

## User Review Required

> [!IMPORTANT]
> At the end of your original prompt, you asked: "Would you like me to help you refine the 'Voice-to-Text' part of the prompt if you want to use your specific Google API keys for it?". 
> **Yes, please provide any specific instructions or API keys you would like me to use for the Voice-to-Text part.** Otherwise, I will use the browser's built-in `webkitSpeechRecognition` API, which works natively in Chrome without requiring API keys, though it might be less accurate than a paid cloud API.

## Proposed Changes

We will build the MVP using a modern, premium "Glassmorphism" aesthetic with a Dark Mode theme to ensure it looks highly professional and engaging.

### Core Application

#### [MODIFY] [index.html](file:///c:/Users/Haaku/Downloads/hrm-PROCTOR-PROJECT/index.html)
- Will replace the existing basic prototype.
- **Structure**: 
  - **Question Area** (Top): Displays a sample technical question.
  - **Options Area** (Middle): Displays multiple-choice options.
  - **Proctoring Dashboard** (Sidebar/Overlay): A sleek, glass-morphic panel showing real-time logs, camera feed, and current proctor status (e.g., "Monitoring...", "Alert!").
  - Hidden canvas for video processing.

#### [NEW] [style.css](file:///c:/Users/Haaku/Downloads/hrm-PROCTOR-PROJECT/style.css)
- Implement a stunning Dark Mode design.
- Use CSS variables for curated HSL colors (deep blacks, purples, and vibrant accent reds for alerts).
- Smooth transitions, micro-animations for elements, and backdrop-filter for the glassmorphism look on the proctor dashboard.

#### [NEW] [app.js](file:///c:/Users/Haaku/Downloads/hrm-PROCTOR-PROJECT/app.js)
This file will contain all the complex logic:
- **Gaze Tracking (WebGazer)**: Initialize WebGazer. Divide the screen into `Question Area` (0-30% height), `Options Area` (30-70%), and `Danger Zone` (>70%). Track the gaze coordinate. If it remains in the `Danger Zone` or `null` (off-screen) for > 3000ms, trigger a red visual alert and log "Potential Malpractice".
- **Environmental Detection (Blue Light)**: Grab the `<video>` element created by WebGazer. Draw frames to a canvas every few hundred milliseconds. Compute average R, G, B values for the pixels. If the `B` (Blue) channel spikes suddenly relative to historical averages (indicating a phone screen lighting up the face), trigger a log.
- **Voice-Reading Detection (Web Speech API)**: Initialize `webkitSpeechRecognition` to run continuously. Collect transcript chunks. Calculate a text similarity score (e.g., word overlap percentage) between the transcribed speech and the text in the 'Question Area'. If similarity > 80% and the current gaze is in the 'Question Area', log "Candidate is Reading out loud".

## Verification Plan

### Automated/Agentic Tests
- I will spin up the `browser_subagent` to navigate to the locally served `index.html`.
- The subagent will run for a short duration while performing the requested interactions (moving mouse to simulate gaze focus, if possible, or we will mock the inputs to demonstrate the alerts).
- The subagent will produce a 10-second `WebP` video recording demonstrating the UI and the malpractice detection.

### Manual Verification
- You can manually test the eye-tracking and voice detection by opening `index.html` in Chrome, looking down for 3 seconds, or reading the question out loud.
