# NADRA Queue Management System

A real-time AI-powered crowd monitoring system built for **NADRA offices** to monitor queues and office occupancy remotely.

The system uses a live camera feed with **YOLOv8** to detect and count people in real time, classifies crowd density, and sends the data to a **Django REST API** where staff can monitor office load through an admin dashboard.

---

## Features

* Real-time people detection using **YOLOv8**
* Automatic crowd density classification (`Low`, `Moderate`, `Crowded`)
* Live camera feed with person bounding boxes
* REST API for crowd snapshot ingestion
* Django Admin dashboard for monitoring office traffic
* Supports remote deployment using **ngrok**
* Includes legacy OpenCV HOG-based detector as fallback

---

## Tech Stack

* **Python**
* **Django**
* **Django REST Framework**
* **OpenCV**
* **Ultralytics YOLOv8**
* **SQLite / Django ORM**
* **ngrok** (optional for remote deployment)

---

## System Architecture

```text
Camera Feed
    │
    ▼
live_people_counter.py
(YOLOv8 real-time detection)
    │
    │ POST /api/crowd/detect/
    ▼
Django REST API
    │
    ▼
CrowdSnapshot Model
    │
    ▼
Django Admin Dashboard
```

---

## Project Structure

```bash
project/
├── manage.py
├── crowd_monitoring/
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── services.py
│   ├── urls.py
│   ├── admin.py
│   └── apps.py
│
├── live_people_counter.py
├── live_detector_client.py
└── .env
```

---

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd project
```

### 2. Install dependencies

```bash
pip install django djangorestframework opencv-python ultralytics requests python-dotenv urllib3
```

### 3. Run migrations

```bash
python manage.py migrate
```

### 4. Create admin user

```bash
python manage.py createsuperuser
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
BACKEND_URL=http://127.0.0.1:8000
DETECTION_INTERVAL=5
OFFICE_ID=1
WEBCAM_SOURCE=0
FRAME_RESIZE_SCALE=1.0
```

| Variable           |                   Description |               Default |
| ------------------ | ----------------------------: | --------------------: |
| BACKEND_URL        |            Django backend URL | http://127.0.0.1:8000 |
| DETECTION_INTERVAL |  Seconds between API requests |                     5 |
| OFFICE_ID          | Office identifier in database |                     1 |
| WEBCAM_SOURCE      |                  Webcam index |                     0 |
| FRAME_RESIZE_SCALE |            Frame resize scale |                   1.0 |

---

## Running the Project

### Start Django backend

```bash
python manage.py runserver
```

### Start live detector

Open another terminal:

```bash
python live_people_counter.py
```

The detector will:

* Open the camera feed
* Detect people in real time
* Draw bounding boxes
* Count total people
* Classify crowd density
* Send updates to the backend every few seconds

Press `Q` to close the detector.

---

## Crowd Density Classification

| People Count |   Status |
| -----------: | -------: |
|          0–4 |      Low |
|         5–12 | Moderate |
|          13+ |  Crowded |

---

## API Endpoint

### POST `/api/crowd/detect/`

Save a crowd snapshot from a specific office.

### Request

```json
{
  "office": 1,
  "people_count": 7,
  "crowd_status": "Moderate"
}
```

### Response

```json
{
  "message": "Crowd data saved successfully",
  "snapshot_id": 42,
  "office": "Karachi Main Branch",
  "people_count": 7,
  "crowd_status": "Moderate"
}
```

### Possible Errors

* `400` → Invalid or missing data
* `404` → Office not found
* `500` → Internal server error

---

## Admin Dashboard

Visit:

```bash
http://127.0.0.1:8000/admin/
```

The dashboard allows administrators to:

* View all crowd snapshots
* Filter by office
* Filter by crowd status
* Track timestamps of office activity

Snapshots are ordered newest-first.

---

## Detection Backends

### YOLOv8 Detector (Recommended)

```bash
live_people_counter.py
```

* High detection accuracy
* Works better in crowded scenes
* More reliable at different angles

### HOG + SVM Detector (Legacy)

```bash
live_detector_client.py
```

* Faster
* Lower accuracy
* Included as fallback where YOLO dependencies cannot be installed

---

## Remote Deployment

To run the camera detector from a remote office while hosting Django elsewhere:

```bash
ngrok http 8000
```

Then update:

```env
BACKEND_URL=https://your-ngrok-url.ngrok-free.app
```

The detector will send crowd data to the exposed backend endpoint.

---

## Notes

* Ensure an `Office` record exists before starting detection
* `OFFICE_ID` must match a valid office in the database
* YOLO model (`yolov8n.pt`) downloads automatically on first run
* Each saved snapshot updates office status in the admin panel via Django signals

---

## Future Improvements

* Live analytics dashboard for crowd trends
* Historical peak-hour reporting
* Email/SMS alerts when crowd exceeds threshold
* Multi-camera support across multiple offices
* Heatmap visualization of queue density

---

## Purpose

This project was built to help improve **queue visibility and operational efficiency in NADRA offices** by enabling staff to monitor crowd load remotely and respond faster during peak hours.
