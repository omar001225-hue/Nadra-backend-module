"""
NADRA Queue Management System - Live People Detection Client
Uses OpenCV HOG detector to count people and send data to Django backend.
"""

import os
import cv2
import time
import requests
import threading
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ============================================================
# Configuration via Environment Variables
# ============================================================
load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
DETECTION_INTERVAL = int(os.getenv("DETECTION_INTERVAL", "5"))
OFFICE_ID = int(os.getenv("OFFICE_ID", "1"))
WEBCAM_SOURCE = int(os.getenv("WEBCAM_SOURCE", "0"))
FRAME_RESIZE_SCALE = float(os.getenv("FRAME_RESIZE_SCALE", "0.5"))

# Derived URLs
API_ENDPOINT = f"{BACKEND_URL}/api/crowd/detect/"

# ============================================================
# Crowd Classification Logic
# ============================================================
def classify_crowd(people_count):
    """Classify crowd status based on people count."""
    if people_count < 5:
        return "Low"
    elif people_count <= 12:
        return "Moderate"
    else:
        return "Crowded"


# ============================================================
# OpenCV People Detection
# ============================================================
class PeopleDetector:
    """Detects people using HOG descriptor."""

    def __init__(self):
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, frame):
        """
        Detect people in frame.
        Returns: (people_count, boxes)
        """
        # Detect people (returns bounding boxes)
        boxes, weights = self.hog.detectMultiScale(
            frame,
            winStride=(8, 8),
            padding=(16, 16),
            scale=1.05,
        )

        # Group overlapping detections
        boxes = self._group_rectangles(boxes)

        return len(boxes), boxes

    @staticmethod
    def _group_rectangles(boxes):
        """Remove overlapping bounding boxes."""
        if len(boxes) == 0:
            return boxes

        # Convert to tuple format for cv2.groupRectangles
        boxes_tuples = [tuple(box) for box in boxes.tolist()]
        grouped, _ = cv2.groupRectangles(boxes_tuples, groupThreshold=2, eps=0.5)

        return grouped if len(grouped) > 0 else []

    @staticmethod
    def draw_boxes(frame, boxes, people_count, crowd_status, fps):
        """Draw bounding boxes and info on frame."""
        for (x, y, w, h) in boxes:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Display info
        info_text = f"People: {people_count} | Status: {crowd_status} | FPS: {fps:.1f}"
        cv2.putText(
            frame,
            info_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

        return frame


# ============================================================
# API Communication
# ============================================================
class BackendClient:
    """Handles communication with Django backend."""

    def __init__(self, endpoint, office_id):
        self.endpoint = endpoint
        self.office_id = office_id
        self.last_error = None

    def check_for_tokens(office_id):
        # Backend se pucho ke kya is office mein koi active token hai?
        response = requests.get(f"http://localhost:8000/api/active-tokens/{office_id}")
        return response.json().get('has_active_tokens', False)

    def send_data(self, people_count, crowd_status):
        """
        Send detection data to Django backend.
        Returns: (success: bool, response_text: str)
        """
        try:
            payload = {
                "office": self.office_id,
                "people_count": people_count,
                "crowd_status": crowd_status,
            }

            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=5,
            )

            if response.status_code == 201:
                self.last_error = None
                return True, response.json()
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.last_error = error_msg
                return False, error_msg

        except requests.exceptions.ConnectionError:
            error_msg = "Backend not reachable"
            self.last_error = error_msg
            return False, error_msg

        except requests.exceptions.Timeout:
            error_msg = "Backend request timeout"
            self.last_error = error_msg
            return False, error_msg

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.last_error = error_msg
            return False, error_msg


# ============================================================
# Main Detection Loop
# ============================================================
class LiveDetectorClient:
    """Main client for live people detection and API integration."""

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
        """Initialize video capture."""
        try:
            self.cap = cv2.VideoCapture(WEBCAM_SOURCE)

            if not self.cap.isOpened():
                print(f"❌ Cannot open camera (source: {WEBCAM_SOURCE})")
                return False

            # Set camera properties for better performance
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)

            print(f"✅ Camera initialized (source: {WEBCAM_SOURCE})")
            return True

        except Exception as e:
            print(f"❌ Error initializing camera: {e}")
            return False

    def process_frame(self, frame):
        """Process a frame and update detection results."""
        # Resize for performance
        h, w = frame.shape[:2]
        resized = cv2.resize(frame, (int(w * FRAME_RESIZE_SCALE), int(h * FRAME_RESIZE_SCALE)))

        # Detect people
        people_count, boxes = self.detector.detect(resized)

        # Scale boxes back to original size
        scale_factor = 1 / FRAME_RESIZE_SCALE
        boxes = [(int(x * scale_factor), int(y * scale_factor),
                  int(w * scale_factor), int(h * scale_factor))
                 for (x, y, w, h) in boxes]

        # Classify crowd
        crowd_status = classify_crowd(people_count)

        # Update state
        self.current_people_count = people_count
        self.current_crowd_status = crowd_status

        return frame, boxes

    def send_data_async(self):
        """Send data to backend in a separate thread."""
        def _send():
            success, response = self.backend.send_data(
                self.current_people_count,
                self.current_crowd_status,
            )

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if success:
                print(
                    f"[{timestamp}] ✅ API Success | "
                    f"People: {self.current_people_count} | "
                    f"Status: {self.current_crowd_status}"
                )
                print(f"    Response: {response}")
            else:
                print(
                    f"[{timestamp}] ❌ API Error | "
                    f"People: {self.current_people_count} | "
                    f"Status: {self.current_crowd_status} | "
                    f"Reason: {response}"
                )

        thread = threading.Thread(target=_send, daemon=True)
        thread.start()

    def update_fps(self):
        """Update FPS counter."""
        self.frame_count += 1
        elapsed = time.time() - self.start_time
        if elapsed > 1:
            self.fps = self.frame_count / elapsed
            self.frame_count = 0
            self.start_time = time.time()

    def run(self):
        """Main detection loop."""
        if not self.initialize_camera():
            return

        self.running = True
        print("\n" + "=" * 60)
        print("🎥 NADRA Queue Management - Live People Detector")
        print("=" * 60)
        print(f"Backend URL: {BACKEND_URL}")
        print(f"API Endpoint: {API_ENDPOINT}")
        print(f"Office ID: {OFFICE_ID}")
        print(f"Detection Interval: {DETECTION_INTERVAL}s")
        print(f"Webcam Source: {WEBCAM_SOURCE}")
        print("=" * 60)
        print("Press 'Q' to quit\n")

        try:
            while self.running:
                ret, frame = self.cap.read()

                if not ret:
                    print("❌ Failed to read frame from camera")
                    break

                # Process frame
                frame, boxes = self.process_frame(frame)

                # Draw detections
                frame = self.detector.draw_boxes(
                    frame,
                    boxes,
                    self.current_people_count,
                    self.current_crowd_status,
                    self.fps,
                )

                # Update FPS
                self.update_fps()

                # Display frame
                cv2.imshow("People Detector", frame)

                # Check if we should send data to API
                current_time = time.time()
                if current_time - self.last_api_call >= DETECTION_INTERVAL:
                    self.send_data_async()
                    self.last_api_call = current_time

                # Handle key press
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == ord("Q"):
                    print("\n⏹️  Shutting down...")
                    break

        except KeyboardInterrupt:
            print("\n⏹️  Interrupted by user")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        self.running = False
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        print("✅ Cleanup complete")


# ============================================================
# Entry Point
# ============================================================
if __name__ == "__main__":
    client = LiveDetectorClient()
    client.run()
