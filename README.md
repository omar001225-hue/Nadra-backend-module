NADRA Queue Management System
A real-time crowd monitoring system for NADRA offices. A live camera feed detects and counts people using AI (YOLOv8), classifies crowd density, and sends the data to a Django REST backend — enabling staff and admins to monitor office load remotely.
---
System Architecture
```
Camera Feed
    │
    ▼
live_people_counter.py   ← YOLOv8 people detection (runs on-site)
    │
    │  POST /api/crowd/detect/
    ▼
Django REST API (views.py)
    │
    ▼
CrowdSnapshot Model  →  Django Admin Dashboard
```
---
Project Structure
```
project/
├── manage.py
├── crowd_monitoring/
│   ├── models.py          # CrowdSnapshot database model
│   ├── views.py           # REST API endpoint
│   ├── serializers.py     # Request/response validation
│   ├── services.py        # HOG-based people detection (legacy)
│   ├── urls.py            # URL routing
│   ├── admin.py           # Django Admin config
│   └── apps.py
├── live_people_counter.py # ⭐ Main live detector (YOLOv8) — run this on-site
└── live_detector_client.py # Legacy HOG-based detector (older, less accurate)
```
---
Setup
1. Install dependencies
```bash
pip install django djangorestframework opencv-python ultralytics requests python-dotenv urllib3
```
2. Apply migrations
```bash
python manage.py migrate
```
3. Create a superuser (for Django Admin)
```bash
python manage.py createsuperuser
```
4. Configure environment variables
Create a `.env` file in the project root:
```env
BACKEND_URL=http://127.0.0.1:8000
DETECTION_INTERVAL=5
OFFICE_ID=1
WEBCAM_SOURCE=0
FRAME_RESIZE_SCALE=1.0
```
Variable	Description	Default
`BACKEND_URL`	URL of your Django server (or ngrok URL)	`http://127.0.0.1:8000`
`DETECTION_INTERVAL`	Seconds between each API call	`5`
`OFFICE_ID`	The database ID of this office location	`1`
`WEBCAM_SOURCE`	Camera index (`0` = built-in, `1` = external)	`0`
`FRAME_RESIZE_SCALE`	Frame scale before detection (`1.0` = no resize)	`1.0`
---
Running the System
Step 1 — Start the Django server
```bash
python manage.py runserver
```
Step 2 — Start the live detector (separate terminal)
```bash
python live_people_counter.py
```
On first run, YOLOv8 will automatically download the `yolov8n.pt` model (~6MB).
A camera window will open showing the live feed with bounding boxes around detected people. Every `DETECTION_INTERVAL` seconds, the count is sent to the backend and saved to the database.
Press Q to quit the detector.
---
API Reference
`POST /api/crowd/detect/`
Saves a crowd snapshot for an office.
Request body (JSON):
```json
{
  "office": 1,
  "people_count": 7,
  "crowd_status": "Moderate"
}
```
Success response `201`:
```json
{
  "message": "✅ Crowd data saved successfully",
  "snapshot_id": 42,
  "office": "Karachi Main Branch",
  "people_count": 7,
  "crowd_status": "Moderate"
}
```
Error responses:
`400` — Missing fields or invalid values
`404` — Office ID not found in database
`500` — Server error
---
Crowd Status Classification
People Count	Status
0 – 4	Low
5 – 12	Moderate
13+	Crowded
---
Django Admin
Visit `http://127.0.0.1:8000/admin/` to view all crowd snapshots.
Snapshots are listed with office name, people count, crowd status, and timestamp. You can filter by status, office, or date.
---
Detection Backends
The project includes two detection backends:
File	Model	Accuracy	Speed
`live_people_counter.py`	YOLOv8n (AI)	⭐⭐⭐⭐⭐ High	Fast
`live_detector_client.py`	HOG + SVM (OpenCV)	⭐⭐ Low	Very fast
Use `live_people_counter.py` — it is significantly more accurate, especially in crowded scenes and at different angles. The HOG-based client is kept for environments where installing `ultralytics` is not possible.
---
Remote Deployment (ngrok)
To run the detector on-site while the Django server is hosted remotely:
```bash
# On the server machine
ngrok http 8000
```
Copy the ngrok HTTPS URL into your `.env`:
```env
BACKEND_URL=https://your-ngrok-url.ngrok-free.app
```
The live counter uses `verify=False` to bypass ngrok's browser warning for programmatic requests.
---
Notes
Make sure the `Office` record exists in the database before starting the detector. The `OFFICE_ID` in `.env` must match a valid office in the system.
The `CrowdSnapshot` model automatically orders records newest-first.
Every new snapshot triggers a `post_save` signal that refreshes the related `Office` record, keeping the Admin dashboard current.
