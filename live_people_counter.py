"""
NADRA Queue Management System - Live People Counter
Opens camera, counts people, and sends data to Django backend CrowdSnapshot model.
Run: python live_people_counter.py
"""

import os
import cv2
import time
import requests
import threading
import urllib3
from datetime import datetime
from dotenv import load_dotenv

# Import the new YOLO AI
from ultralytics import YOLO

# Suppress the insecure request warning caused by verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
DETECTION_INTERVAL = int(os.getenv("DETECTION_INTERVAL", "5"))
OFFICE_ID = int(os.getenv("OFFICE_ID", "1"))
WEBCAM_SOURCE = int(os.getenv("WEBCAM_SOURCE", "0"))
FRAME_RESIZE_SCALE = float(os.getenv("FRAME_RESIZE_SCALE", "1.0"))

# Safely build the URL to prevent double slashes (e.g., .dev//api/...)
API_ENDPOINT = f"{BACKEND_URL.rstrip('/')}/api/crowd/detect/"


def classify_crowd(people_count):
    if people_count < 5:
        return "Low"
    elif people_count <= 12:
        return "Moderate"
    else:
        return "Crowded"


class PeopleDetector:
    def __init__(self):
        # Loads the YOLOv8 nano model. It will download a small file the first time it runs.
        print("🤖 Loading YOLOv8 AI Model...")
        self.model = YOLO('yolov8n.pt') 

    def detect(self, frame):
        # classes=[0] ensures it ONLY detects humans, ignoring other objects
        results = self.model(frame, classes=[0], verbose=False)
        
        boxes = []
        for r in results:
            for box in r.boxes:
                # Extract coordinates and convert to integers
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                # Convert (x1, y1, x2, y2) to (x, y, width, height) format for drawing
                boxes.append((x1, y1, x2 - x1, y2 - y1))
                
        return len(boxes), boxes

    @staticmethod
    def draw_boxes(frame, boxes, people_count, crowd_status, fps):
        for (x, y, w, h) in boxes:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
        info_text = f"People: {people_count} | Status: {crowd_status} | FPS: {fps:.1f}"
        
        # Draw a background rectangle for the text to make it easy to read
        cv2.rectangle(frame, (5, 5), (450, 45), (0, 0, 0), -1)
        cv2.putText(
            frame, info_text, (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2,
        )
        return frame


class BackendClient:
    def __init__(self, endpoint, office_id):
        self.endpoint = endpoint
        self.office_id = office_id
        self.last_error = None

    def send_data(self, people_count, crowd_status):
        try:
            payload = {
                "office": self.office_id,
                "people_count": people_count,
                "crowd_status": crowd_status,
            }
            # verify=False bypasses the ngrok browser warning block
            response = requests.post(self.endpoint, json=payload, timeout=5, verify=False)
            
            if response.status_code == 201:
                self.last_error = None
                return True, response.json()
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.last_error = error_msg
                return False, error_msg
                
        except requests.exceptions.ConnectionError:
            return False, "Backend not reachable (Check if ngrok/Django is running)"
        except requests.exceptions.Timeout:
            return False, "Backend request timeout"
        except Exception as e:
            return False, f"Error: {str(e)}"


class LivePeopleCounter:
    def __init__(self):
        self.detector = PeopleDetector()
        self.backend = BackendClient(API_ENDPOINT, OFFICE_ID)
        self.cap = None
        self.running = False
        self.last_api_call = 0
        self.current_people_count = 0
        self.current_crowd_status = "Low"
        self.frame_count = 0
        self.fps = 0
        self.start_time = time.time()

    def initialize_camera(self):
        try:
            self.cap = cv2.VideoCapture(WEBCAM_SOURCE)
            if not self.cap.isOpened():
                print(f"❌ Cannot open camera (source: {WEBCAM_SOURCE})")
                return False
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            print(f"✅ Camera initialized (source: {WEBCAM_SOURCE})")
            return True
        except Exception as e:
            print(f"❌ Error initializing camera: {e}")
            return False

    def process_frame(self, frame):
        h, w = frame.shape[:2]
        
        # Only resize if the scale is not 1.0 to save processing power
        if FRAME_RESIZE_SCALE != 1.0:
            frame_to_process = cv2.resize(frame, (int(w * FRAME_RESIZE_SCALE), int(h * FRAME_RESIZE_SCALE)))
        else:
            frame_to_process = frame

        people_count, boxes = self.detector.detect(frame_to_process)
        
        # Scale boxes back to original size if we resized the frame
        if FRAME_RESIZE_SCALE != 1.0:
            scale_factor = 1 / FRAME_RESIZE_SCALE
            boxes = [(int(x * scale_factor), int(y * scale_factor),
                      int(bw * scale_factor), int(bh * scale_factor))
                     for (x, y, bw, bh) in boxes]
                     
        crowd_status = classify_crowd(people_count)
        self.current_people_count = people_count
        self.current_crowd_status = crowd_status
        return frame, boxes

    def send_data_async(self):
        def _send():
            success, response = self.backend.send_data(
                self.current_people_count,
                self.current_crowd_status,
            )
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if success:
                print(f"[{timestamp}] ✅ Sent to DB | People: {self.current_people_count} | Status: {self.current_crowd_status}")
            else:
                print(f"[{timestamp}] ❌ Error | {response}")
                
        thread = threading.Thread(target=_send, daemon=True)
        thread.start()

    def update_fps(self):
        self.frame_count += 1
        elapsed = time.time() - self.start_time
        if elapsed > 1:
            self.fps = self.frame_count / elapsed
            self.frame_count = 0
            self.start_time = time.time()

    def run(self):
        if not self.initialize_camera():
            return
        self.running = True
        print("\n" + "=" * 60)
        print("🎥 Live People Counter - NADRA Queue Management (YOLOv8)")
        print("=" * 60)
        print(f"Backend: {BACKEND_URL}")
        print(f"Endpoint: {API_ENDPOINT}")
        print(f"Office ID: {OFFICE_ID}")
        print(f"Sending data every {DETECTION_INTERVAL}s")
        print("=" * 60)
        print("Press 'Q' to quit\n")

        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    print("❌ Failed to read frame")
                    break

                frame, boxes = self.process_frame(frame)
                frame = self.detector.draw_boxes(
                    frame, boxes,
                    self.current_people_count,
                    self.current_crowd_status,
                    self.fps,
                )
                self.update_fps()
                cv2.imshow("People Counter", frame)

                current_time = time.time()
                if current_time - self.last_api_call >= DETECTION_INTERVAL:
                    self.send_data_async()
                    self.last_api_call = current_time

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == ord("Q"):
                    print("\n⏹️  Shutting down...")
                    break

        except KeyboardInterrupt:
            print("\n⏹️  Interrupted by user")
        finally:
            self.cleanup()

    def cleanup(self):
        self.running = False
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        print("✅ Cleanup complete")


if __name__ == "__main__":
    counter = LivePeopleCounter()
    counter.run()