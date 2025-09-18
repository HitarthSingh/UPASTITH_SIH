
# Automated Attendance System

## Overview
A web-based attendance system using face recognition, QR codes, and digital leave management. Designed for educational institutions to automate and streamline attendance, leave requests, and class/event management for students and teachers.

## Features

### Student
- Face recognition attendance (with QR validation)
- Dashboard: today's classes, events, attendance summary
- Timetable view
- Repository: access shared class notes
- Leave application (with document upload)
- Results and suggestion box

### Teacher
- Dashboard: analytics, class/event management
- Add/remove/view classes and events
- Approve/reject student leave requests
- View attendance records by class/date
- Upload and share class notes
- Generate QR codes for attendance

### Admin
- Sample admin user for demo/testing

## Tech Stack
- **Backend:** Python (Flask, flask-cors)
- **Frontend:** HTML (Jinja2 templates), Tailwind CSS, Chart.js, jsQR, qrcodejs
- **Face Recognition:** face_recognition, OpenCV, dlib, numpy
- **Database:** SQLite (attendance.db, authentication.db, leaves.db, classes.db)
- **QR Code:** qrcode (Python), qrcodejs (JS)
- **Other:** pandas, werkzeug, secrets

## Setup & Usage
1. Clone the repository:
	```sh
	git clone https://github.com/vabbings/SIH.git
	cd SIH
	```
2. Install dependencies:
	```sh
	pip install -r requirements.txt
	```
3. Run the server:
	```sh
	python minimal_server.py
	```
	The app runs on `http://localhost:3000` (or `5000` for debug mode).

5. Sample login credentials:
	- Students: `student1` / `password123`
	- Teachers: `teacher1` / `teacher123`
	- Admin: `admin` / `admin123`

## API Endpoints (Summary)
- `/api/registerfinal1` — Register face
- `/api/recognizefinal1` — Recognize face and mark attendance
- `/api/classes` — Get/add/delete classes
- `/api/events` — Get/add/delete events
- `/api/leave/submit` — Submit leave request
- `/api/leave/requests` — Get pending leave requests
- `/api/attendance/today` — Get today's attendance
- `/api/attendance/date/<date>` — Get attendance by date/class
- `/api/qr/generate` — Generate QR code for attendance
- `/api/upload/notes` — Upload class notes
- `/api/notes/<class_id>` — Get notes for a class

## License
MIT License

---
For issues or contributions, open an issue or pull request on GitHub.
