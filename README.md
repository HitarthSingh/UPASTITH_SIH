
#Upastith – Automated Attendance System

A modern web-based attendance tracking system leveraging facial recognition, QR codes, and real-time notes upload, built with Flask, OpenCV, and the face_recognition library.

## Features

•⁠Face Registration: Register users with face data via webcam.
•⁠Real-time Face Recognition: Mark attendance instantly when the user is recognized.
•⁠QR Code Attendance: Students can scan a unique QR code to mark attendance as an alternative method.
•⁠Attendance Management: View, filter, and export attendance records.
•⁠Leave Application: Students submit leave requests; teachers can approve/reject them.
•⁠Suggestion Box: Students can submit feedback and suggestions.
•⁠Real-time Notes Upload: Teachers can upload notes/documents for students in real-time.
•⁠Modern UI: Responsive, glassmorphism-inspired design with intuitive navigation.
•⁠SQLite Database: Local storage for users, attendance, leaves, notes, and authentication.
•⁠Statistics Dashboard: Quick access to stats and attendance summaries.
•⁠Export Data: Download attendance records and notes as CSV or PDF.

## Prerequisites

•⁠Python 3.7+
•⁠Webcam or camera access
•⁠QR scanner-enabled smartphone or webcam
•⁠Modern browser with camera permissions

## Installation

1.*Clone the repository*
bash
git clone <your-repo-url>
cd "Automated Attendance"


2.*Create a virtual environment*
bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate


3.*Install dependencies*
bash
pip install -r requirements.txt


If you face issues with face_recognition, ensure you have CMake and Visual Studio Build Tools (Windows), or Homebrew/CMake (macOS/Linux) installed.

4.*Run the application*
bash
python app.py


5.*Access the app*
Open your browser at http://localhost:5000

 ##Usage

•⁠*Dashboard*: /dashboard – View stats, export data, and access notes.
•⁠*Register*: /register – Add new users with face data.
•⁠*Attendance*: /attendance – Mark attendance via webcam or QR scan.
•⁠*Records*: /records – View, filter, and export attendance data.
•⁠*Leave Application*: /leaveapplication – Submit leave requests.
•⁠*Suggestion Box8: /suggestionbox – Share feedback or suggestions.
•⁠*Notes Upload*: /notesupload – Upload notes/documents in real-time for students.
•⁠*QR Attendance*: /qrattendance – Students scan QR to mark attendance instantly.

## API Endpoints

•⁠POST /api/register – Register user with face data
•⁠POST /api/recognize – Recognize face and mark attendance
•⁠GET /api/attendance – Retrieve attendance records
•⁠GET /api/users – List registered users
•⁠GET /api/export/csv – Export attendance data
•⁠POST /api/leave/submit – Submit leave request
•⁠GET /api/leave/requests – Get leave requests
•⁠POST /api/leave/approve/:id – Approve leave request
•⁠POST /api/leave/reject/:id – Reject leave request
•⁠POST /api/qr-attendance – Mark attendance using QR code
•⁠POST /api/notes/upload – Upload notes for students
•⁠GET /api/notes/:id – Fetch notes for a specific class or session

## File Structure
Automated Attendance/
├── app.py
├── face_utils.py
├── db_attendance.py
├── db_leaves.py
├── db_notes.py
├── requirements.txt
├── attendance.db
├── authentication.db
├── classes.db
├── leaves.db
├── notes.db
├── face_encodings/
│   └── *.pkl
├── uploaded_notes/
│   └── *.pdf
├── templates/
│   ├── landingpagefinal1.html
│   ├── teacherloginpage.html
│   ├── teacherdasboardfinal.html
│   ├── leaveapplication.html
│   ├── suggestionbox.html
│   ├── notesupload.html
│   ├── qrattendance.html
│   ├── aboutus.html
│   └── ...
└── static/
    └── ...

##Configuration

•⁠*Face Recognition*: Adjust recognition thresholds and encoding logic in face_utils.py
•⁠*QR Code Settings*: Configure QR generation and validation parameters.
•⁠*Flask Settings*: Update debug mode, host, and port in app.py.
•⁠*Database*: Schema updates and file paths in face_utils.py
 and db_notes.py.

##Troubleshooting

•⁠*Camera Access*: Check browser permissions and close other applications using the camera.
•⁠*Face Recognition*: Ensure proper lighting and that users are registered with clear images.
•⁠*QR Attendance*: Make sure the QR code is correctly generated and readable.
•⁠*Notes Upload*: Verify file types and permissions in the upload directory.
•⁠*Database Issues*: SQLite databases are auto-created; confirm write permissions and directory paths.
•⁠*Performance*: Reduce image resolution or ensure system resources are sufficient.

##Security

•⁠Face encodings are stored locally as pickle files—secure them from unauthorized access.
•⁠Uploaded notes and attendance data contain personal information—implement proper access controls.
•⁠For production, integrate authentication mechanisms and encrypt sensitive data.

##Development

•⁠*Add Features*: Modify app.py
 and face_utils.py
•⁠*UI Customization*: Edit HTML/CSS in templates/
 and static/
•⁠*Database Updates*: Change schemas or paths in the respective DB helper files.
•*⁠API Expansion*: Add new endpoints or extend existing ones in app.py.
•⁠*QR Improvements*: Enhance QR encryption or scanning logic as needed.

## License

This project is licensed under the MIT License.

## Support

•⁠Review troubleshooting steps above.
•⁠Check console logs and error outputs for details.
•⁠Ensure dependencies are installed as specified.
•⁠Confirm camera and browser permissions are enabled.
•⁠Secure sensitive data before deployment.

