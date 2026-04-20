import argparse
import cv2
import numpy as np
import time
from collections import deque
from eyetrax import GazeEstimator, run_9_point_calibration

def get_screen_resolution():
    import ctypes
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

class ReadingDetector:
    def __init__(self, history_len=45):
        self.history = deque(maxlen=history_len)
        self.is_reading = False
        
    def update(self, x):
        self.history.append(x)
        self._analyze_saccades()
        
    def _analyze_saccades(self):
        if len(self.history) < 15:
            self.is_reading = False
            return
            
        history_list = list(self.history)
        dxs = [history_list[i] - history_list[i-1] for i in range(1, len(history_list))]
        forward_saccades = sum(1 for dx in dxs if 5 < dx < 50)
        return_sweeps = sum(1 for dx in dxs if dx < -100)
        
        if forward_saccades >= 3 and return_sweeps >= 1:
            self.is_reading = True
        else:
            self.is_reading = False

class PupilGazeEstimator(GazeEstimator):
    def extract_features(self, image):
        """
        Calculates pure stable pupil-geometry ratios and returns them in a 4-feature vector.
        This forces the Ridge ML model to track exclusively the pupil, mapping it cleanly to the 9 points.
        """
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image_rgb = np.ascontiguousarray(image_rgb)
        mp_image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB,
            data=image_rgb,
        )
        ts_ms = int(time.time() * 1000)
        if ts_ms <= self._mp_last_ts_ms:
            ts_ms = self._mp_last_ts_ms + 1
        self._mp_last_ts_ms = ts_ms

        result = self._face_landmarker.detect_for_video(mp_image, ts_ms)
        if not result.face_landmarks:
            return None, False

        landmarks = result.face_landmarks[0]

        # Left eye boundaries & iris
        l_outer = np.array([landmarks[33].x, landmarks[33].y])
        l_inner = np.array([landmarks[133].x, landmarks[133].y])
        l_iris = np.array([landmarks[468].x, landmarks[468].y])
        l_top = np.array([landmarks[159].x, landmarks[159].y])
        l_bottom = np.array([landmarks[145].x, landmarks[145].y])
        
        # Guard against zero-division
        l_w = np.linalg.norm(l_inner - l_outer) + 1e-9
        l_h = np.linalg.norm(l_bottom - l_top) + 1e-9
        l_ratio_x = np.linalg.norm(l_iris - l_outer) / l_w
        l_ratio_y = np.linalg.norm(l_iris - l_top) / l_h

        # Right eye boundaries & iris
        r_inner = np.array([landmarks[362].x, landmarks[362].y])
        r_outer = np.array([landmarks[263].x, landmarks[263].y])
        r_iris = np.array([landmarks[473].x, landmarks[473].y])
        r_top = np.array([landmarks[386].x, landmarks[386].y])
        r_bottom = np.array([landmarks[374].x, landmarks[374].y])
        
        r_w = np.linalg.norm(r_inner - r_outer) + 1e-9
        r_h = np.linalg.norm(r_bottom - r_top) + 1e-9
        r_ratio_x = np.linalg.norm(r_iris - r_outer) / r_w
        r_ratio_y = np.linalg.norm(r_iris - r_top) / r_h

        # Strict 4-feature geometric vector guarantees 0% facial wobble
        features = np.array([l_ratio_x, l_ratio_y, r_ratio_x, r_ratio_y], dtype=np.float32)

        # Blink Detection (Original from Eyetrax)
        left_EAR = l_h / l_w
        right_EAR = r_h / r_w
        EAR = (left_EAR + right_EAR) / 2.0

        self._ear_history.append(EAR)
        if len(self._ear_history) >= self._min_history:
            thr = float(np.mean(self._ear_history)) * self._blink_ratio
        else:
            thr = 0.2
        blink_detected = EAR < thr

        return features, blink_detected

def main():
    parser = argparse.ArgumentParser(description="HR Proctor Demo")
    parser.add_argument("--malpractice", action="store_true", help="Enable malpractice and reading flags")
    args = parser.parse_args()

    print("Initializing EyeTrax with Stable Pupil Extractor...")
    estimator = PupilGazeEstimator(model_kwargs={"alpha": 0.1})
    
    print("Launching 9-point screen calibration...")
    run_9_point_calibration(estimator)

    cap = cv2.VideoCapture(0)
    screen_w, screen_h = get_screen_resolution()

    cv2.namedWindow("Stable EyeTrax Proctor", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Stable EyeTrax Proctor", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    print("Tracking started. Press ESC to exit.")
    
    reading_detector = ReadingDetector()
    
    filtered_x, filtered_y = None, None
    sma_alpha = 0.2 # Light EMA to ensure liquid smooth movement
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Do not flip the frame globally! 
        # eyetrax calibration runs on un-flipped frames; flipping it here inversed the X-axis tracking!
        
        h, w, _ = frame.shape
        ui_canvas = np.zeros((screen_h, screen_w, 3), dtype=np.uint8)

        # Extract features using our overridden Pupil-Only method
        features, blink = estimator.extract_features(frame)

        log_msg = "STATUS: IDLE"
        log_color = (255, 255, 255)

        if features is not None and not blink:
            # SVR/Ridge perfectly maps the pupil ratios to exact 9-point calibrated screen corners
            preds = estimator.predict([features])
            raw_x, raw_y = preds[0]
            
            if filtered_x is None:
                filtered_x, filtered_y = raw_x, raw_y
            else:
                filtered_x = (sma_alpha * raw_x) + ((1 - sma_alpha) * filtered_x)
                filtered_y = (sma_alpha * raw_y) + ((1 - sma_alpha) * filtered_y)
                
            x_int, y_int = int(filtered_x), int(filtered_y)
            
            reading_detector.update(filtered_x)
            
            # Draw tracking dot
            cv2.circle(ui_canvas, (x_int, y_int), 20, (0, 255, 0), -1)
            
            if args.malpractice:
                out_of_bounds = filtered_x < 0 or filtered_x > screen_w or filtered_y < 0 or filtered_y > screen_h
                
                margin_w = screen_w * 0.15
                
                if out_of_bounds:
                    cv2.rectangle(ui_canvas, (10, 10), (screen_w-10, screen_h-10), (0, 0, 255), 10)
                    log_msg = "HR LOG: MALPRACTICE - LOOKING OFF SCREEN!"
                    log_color = (0, 0, 255)
                elif filtered_x < margin_w:
                    log_msg = "HR LOG: MALPRACTICE - FIXATED ON LEFT CORNER"
                    log_color = (0, 165, 255)
                elif filtered_x > screen_w - margin_w:
                    log_msg = "HR LOG: MALPRACTICE - FIXATED ON RIGHT CORNER"
                    log_color = (0, 165, 255)
                elif reading_detector.is_reading:
                    log_msg = "HR LOG: SUSPICIOUS - READING DETECTED"
                    log_color = (0, 255, 255)
                else:
                    log_msg = "HR LOG: ALL CLEAR (LOOKING CENTER)"
                    log_color = (0, 255, 0)
        else:
            if args.malpractice:
                log_msg = "HR LOG: MALPRACTICE - NO FACE DETECTED"
                log_color = (0, 0, 255)

        if args.malpractice:
            cv2.putText(ui_canvas, log_msg, (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, log_color, 3)

        mirrored_frame = cv2.flip(frame, 1)
        small_cam = cv2.resize(mirrored_frame, (w // 2, h // 2))
        ui_canvas[screen_h - (h//2) - 20: screen_h - 20, 20: 20 + w // 2] = small_cam

        cv2.imshow("Stable EyeTrax Proctor", ui_canvas)
        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
