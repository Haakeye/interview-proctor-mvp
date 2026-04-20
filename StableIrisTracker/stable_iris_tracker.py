import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import time
import urllib.request
from pathlib import Path

class StableIrisTracker:
    def __init__(self):
        # Download MediaPipe face landmarker model if not present
        self.model_path = "face_landmarker.task"
        if not Path(self.model_path).exists():
            print("Downloading Face Landmarker model...")
            url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
            urllib.request.urlretrieve(url, self.model_path)
            
        # Initialize MediaPipe Face Landmarker
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False
        )
        self.face_landmarker = vision.FaceLandmarker.create_from_options(options)
        
        # Calibration state
        self.calibrating = True
        self.calib_start_time = None
        self.CALIB_DURATION = 5.0 # seconds
        self.calib_ratios_x = []
        self.calib_ratios_y = []
        self.baseline_x = 0.5
        self.baseline_y = 0.5
        
        # Tracking sensitivity
        self.SENSITIVITY_X = 2.0
        self.SENSITIVITY_Y = 3.0
        
        # Filtering (EMA)
        self.ema_alpha = 0.15 # Lower is smoother but slower response
        self.filtered_gaze_x = None
        self.filtered_gaze_y = None
        
        # Warning states
        self.out_of_bounds_frames = 0
        self.MAX_OOB_FRAMES = 15 # frames before warning

    def get_iris_ratio(self, landmarks):
        # Left eye: outer 33, inner 133
        # Left iris center: 468
        # Left eye top: 159, bottom: 145
        l_outer = np.array([landmarks[33].x, landmarks[33].y])
        l_inner = np.array([landmarks[133].x, landmarks[133].y])
        l_iris = np.array([landmarks[468].x, landmarks[468].y])
        l_top = np.array([landmarks[159].x, landmarks[159].y])
        l_bottom = np.array([landmarks[145].x, landmarks[145].y])
        
        l_ratio_x = np.linalg.norm(l_iris - l_outer) / (np.linalg.norm(l_inner - l_outer) + 1e-6)
        l_ratio_y = np.linalg.norm(l_iris - l_top) / (np.linalg.norm(l_bottom - l_top) + 1e-6)

        # Right eye: inner 362, outer 263
        # Right iris center: 473
        # Right eye top: 386, bottom: 374
        r_inner = np.array([landmarks[362].x, landmarks[362].y])
        r_outer = np.array([landmarks[263].x, landmarks[263].y])
        r_iris = np.array([landmarks[473].x, landmarks[473].y])
        r_top = np.array([landmarks[386].x, landmarks[386].y])
        r_bottom = np.array([landmarks[374].x, landmarks[374].y])
        
        # Right eye x calculation: outer to inner is from 263 to 362. 
        # But wait, looking from camera, 263 is rightmost on screen, 362 is inner.
        r_ratio_x = np.linalg.norm(r_iris - r_outer) / (np.linalg.norm(r_inner - r_outer) + 1e-6)
        r_ratio_y = np.linalg.norm(r_iris - r_top) / (np.linalg.norm(r_bottom - r_top) + 1e-6)

        # Average ratios
        avg_ratio_x = (l_ratio_x + r_ratio_x) / 2.0
        avg_ratio_y = (l_ratio_y + r_ratio_y) / 2.0
        
        return avg_ratio_x, avg_ratio_y

    def run(self):
        cap = cv2.VideoCapture(0)
        cv2.namedWindow("Proctor Desktop", cv2.WINDOW_NORMAL)
        cv2.setWindowProperty("Proctor Desktop", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        
        # Get actual screen dimensions if possible, or dummy
        screen_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) * 2
        screen_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) * 2

        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame = cv2.flip(frame, 1) # Mirror image
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb_frame))
            results = self.face_landmarker.detect(mp_image)
            
            # Create a blank canvas for proctor UI (or we could overlay on camera)
            # Let's show a clean UI
            ui_canvas = np.zeros((h*2, w*2, 3), dtype=np.uint8)
            ui_h, ui_w, _ = ui_canvas.shape
            
            center_x = ui_w // 2
            center_y = ui_h // 2
            
            if results.face_landmarks:
                landmarks = results.face_landmarks[0]
                ratio_x, ratio_y = self.get_iris_ratio(landmarks)
                
                if self.calibrating:
                    if self.calib_start_time is None:
                        self.calib_start_time = time.time()
                    
                    elapsed = time.time() - self.calib_start_time
                    if elapsed < self.CALIB_DURATION:
                        self.calib_ratios_x.append(ratio_x)
                        self.calib_ratios_y.append(ratio_y)
                        
                        # Draw calibration UI
                        txt = f"Keep looking exactly at the center... {self.CALIB_DURATION - elapsed:.1f}s"
                        cv2.putText(ui_canvas, txt, (center_x - 300, center_y - 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                        
                        # Shrinking calibration circle
                        radius = int(50 * (1 - (elapsed / self.CALIB_DURATION)))
                        if radius < 5: radius = 5
                        cv2.circle(ui_canvas, (center_x, center_y), radius, (0, 0, 255), -1)
                        cv2.circle(ui_canvas, (center_x, center_y), 50, (255, 255, 255), 2)
                    else:
                        self.baseline_x = np.mean(self.calib_ratios_x)
                        self.baseline_y = np.mean(self.calib_ratios_y)
                        self.calibrating = False
                        self.filtered_gaze_x = center_x
                        self.filtered_gaze_y = center_y
                        print("Calibration complete.")
                        print(f"Baseline Ratios: X={self.baseline_x:.4f}, Y={self.baseline_y:.4f}")
                else:
                    # Differential tracking
                    delta_x = ratio_x - self.baseline_x
                    delta_y = ratio_y - self.baseline_y
                    
                    raw_gaze_x = center_x + (delta_x * ui_w * self.SENSITIVITY_X)
                    raw_gaze_y = center_y + (delta_y * ui_h * self.SENSITIVITY_Y)
                    
                    # EMA Filter
                    if self.filtered_gaze_x is None:
                        self.filtered_gaze_x = raw_gaze_x
                        self.filtered_gaze_y = raw_gaze_y
                    else:
                        self.filtered_gaze_x = (self.ema_alpha * raw_gaze_x) + ((1 - self.ema_alpha) * self.filtered_gaze_x)
                        self.filtered_gaze_y = (self.ema_alpha * raw_gaze_y) + ((1 - self.ema_alpha) * self.filtered_gaze_y)
                    
                    gaze_x = int(self.filtered_gaze_x)
                    gaze_y = int(self.filtered_gaze_y)
                    
                    # Draw Gaze point
                    cv2.circle(ui_canvas, (gaze_x, gaze_y), 20, (0, 255, 0), -1)
                    cv2.circle(ui_canvas, (gaze_x, gaze_y), 22, (255, 255, 255), 2)
                    
                    # Out of bounds check
                    if gaze_x < 0 or gaze_x > ui_w or gaze_y < 0 or gaze_y > ui_h:
                        self.out_of_bounds_frames += 1
                    else:
                        self.out_of_bounds_frames = 0
                        
                    if self.out_of_bounds_frames > self.MAX_OOB_FRAMES:
                        cv2.putText(ui_canvas, "WARNING: Looking away from screen!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
                        cv2.rectangle(ui_canvas, (10, 10), (ui_w-10, ui_h-10), (0, 0, 255), 10)
                        
                    # Camera overlay (picture in picture)
                    cam_h, cam_w = h // 2, w // 2
                    small_cam = cv2.resize(frame, (cam_w, cam_h))
                    ui_canvas[ui_h - cam_h - 20: ui_h - 20, 20: 20 + cam_w] = small_cam
                    cv2.putText(ui_canvas, "ESC to Exit", (20, ui_h - cam_h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            else:
                cv2.putText(ui_canvas, "Face not detected", (center_x - 150, center_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                # Reset calib if lost face during calibration
                if self.calibrating:
                    self.calib_start_time = None
                    self.calib_ratios_x = []
                    self.calib_ratios_y = []

            cv2.imshow("Proctor Desktop", ui_canvas)
            if cv2.waitKey(1) == 27: # ESC
                break
                
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    tracker = StableIrisTracker()
    tracker.run()
