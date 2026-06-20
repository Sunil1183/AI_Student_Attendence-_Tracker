# Attendance AI – Face Recognition Attendance System

Advanced Django-based attendance system using OpenCV-powered face recognition, designed as a production-style MCA project.

## Tech Stack

- **Backend**: Django, Django REST Framework
- **AI / CV**: OpenCV (LBPH face recognizer), Haar cascades, NumPy, scikit-learn utilities
- **Database**: SQLite (default, easily switchable to PostgreSQL/MySQL)
- **Frontend**: HTML5, modern CSS, vanilla JS + Chart.js for dashboards

## Features

- **Face recognition attendance**
  - Trainable face model per student (LBPH)
  - Webcam-based capture page for marking attendance
  - Simple liveness check: the browser grabs a short burst of frames and the
    server ensures the feed isn’t just a static image before recognizing faces
  - Support for multiple images per student
- **Role-based authentication**
  - Admin, Faculty, Student roles
  - Secure login / logout
- **Admin dashboard**
  - Today’s attendance summary cards
  - Monthly attendance chart
  - Recent sessions table
- **Reports**
  - Per-student attendance history
  - Per-course / per-date reports
  - CSV export stubs (extensible)
- **Student portal**
  - View personal attendance stats
  - Upcoming classes & notices (static placeholders)

## Local setup

```bash
cd "c:\Mcaprojects\Attendence Tracker"

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

django-admin startproject attendance_ai .
python manage.py startapp attendance
python manage.py startapp accounts
```

After cloning or pulling this repo with the generated code, run:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then open `http://127.0.0.1:8000/` in your browser.

## Face recognition workflow (high level)

1. **Student registration**
   - Admin/faculty creates user and student profile.
   - Capture multiple face images via webcam from the UI.
2. **Model training**
   - Management command loads all saved face images and trains an OpenCV LBPH model.
   - Model is stored as `face_model.yml` in a dedicated folder.
3. **Attendance marking**
   - Webcam capture sends a frame to the backend.
   - Backend detects faces, predicts the student ID using the trained model, and records attendance.

Detailed implementation is inside the `attendance` app (views, services, and management commands).

