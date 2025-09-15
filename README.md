# Upastith – Automated Attendance System

A modern web-based attendance tracking system using facial recognition, built with Flask, OpenCV, and the face_recognition library.

---

## Features

- **Face Registration**: Register users via webcam.
- **Real-time Face Recognition**: Mark attendance automatically.
- **Attendance Management**: View, filter, and export records.
- **Leave Application**: Students can submit leave requests; teachers can approve/reject.
- **Suggestion Box**: Students can submit suggestions.
- **Modern UI**: Responsive, glassmorphism-based interface.
- **SQLite Database**: Local storage for users, attendance, leaves, and authentication.
- **Statistics Dashboard**: Quick stats and navigation.
- **Export Data**: Download attendance as CSV.

---

## Prerequisites

- Python 3.7+
- Webcam/camera access
- Modern browser with camera permissions

---

## Installation

1. **Clone the repository**
   ```sh
   git clone <your-repo-url>
   cd "Automated Attendance"
   ```

2. **Create a virtual environment**
   ```sh
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```

   If you have issues with `face_recognition`, install CMake and Visual Studio Build Tools (Windows), or use Homebrew/CMake (macOS/Linux).

4. **Run the application**
   ```sh
   python app.py
   ```

5. **Access the app**
   Open your browser at [http://localhost:5000](http://localhost:5000)

---

## Usage

- **Dashboard**: `/dashboard` – View stats, export data.
- **Register**: `/register` – Add new users with face data.
- **Attendance**: `/attendance` – Mark attendance via webcam.
- **Records**: `/records` – View and export attendance.
- **Leave Application**: `/leaveapplication` – Submit leave requests.
- **Suggestion Box**: `/suggestionbox` – Submit suggestions.

---

## API Endpoints

- `POST /api/register` – Register user with face data
- `POST /api/recognize` – Recognize face and mark attendance
- `GET /api/attendance` – Get attendance records
- `GET /api/users` – List registered users
- `GET /api/export/csv` – Export attendance data
- `POST /api/leave/submit` – Submit leave application
- `GET /api/leave/requests` – Get leave requests
- `POST /api/leave/approve/:id` – Approve leave
- `POST /api/leave/reject/:id` – Reject leave

---

## File Structure

```
Automated Attendance/
├── app.py
├── face_utils.py
├── db_attendance.py
├── db_leaves.py
├── requirements.txt
├── attendance.db
├── authentication.db
├── classes.db
├── leaves.db
├── face_encodings/
│   └── *.pkl
├── templates/
│   ├── landingpagefinal1.html
│   ├── teacherloginpage.html
│   ├── teacherdasboardfinal.html
│   ├── leaveapplication.html
│   ├── suggestionbox.html
│   ├── repository.html
│   ├── aboutus.html
│   └── ...
└── static/
    └── ...
```

---

## Configuration

- **Face Recognition**: Adjust parameters in [`face_utils.py`](face_utils.py)
- **Flask Settings**: Change debug/host/port in `app.py`
- **Database**: Schema and paths in [`face_utils.py`](face_utils.py)

---

## Troubleshooting

- **Camera Issues**: Check browser permissions and close other apps using the camera.
- **Face Recognition**: Ensure good lighting and user registration.
- **Database**: SQLite DBs are created automatically; check file permissions.
- **Performance**: Reduce image quality or check system resources if slow.

---

## Security

- Face encodings stored locally in pickle files.
- Database contains personal info; secure appropriately.
- Consider authentication for production use.

---

## Development

- **Add Features**: Edit [`app.py`](app.py) and [`face_utils.py`](face_utils.py)
- **UI Changes**: Edit HTML in [`templates/`](templates/)
- **Database**: Update schema in [`face_utils.py`](face_utils.py)
- **API**: Add endpoints in [`app.py`](app.py)

---

## License

MIT License

---

## Support

- Check troubleshooting above
- Review logs and error messages
- Ensure dependencies are installed
- Verify camera/browser permissions
