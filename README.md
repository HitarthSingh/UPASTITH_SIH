# SIH
# Face Recognition Attendance System

A modern, web-based attendance tracking system using facial recognition technology built with Flask, OpenCV, and face_recognition library.

## Features

- **Face Registration**: Register new users by capturing their face data through webcam
- **Real-time Face Recognition**: Automatic attendance marking using live camera feed
- **Attendance Management**: View, filter, and export attendance records
- **Modern Web Interface**: Responsive Bootstrap-based UI with real-time updates
- **Data Export**: Export attendance data to CSV format
- **SQLite Database**: Local database storage for users and attendance records
- **Statistics Dashboard**: View attendance statistics and user information

## Screenshots

The system includes:
- Dashboard with quick stats and navigation
- User registration with live camera capture
- Real-time attendance marking with face recognition
- Comprehensive records view with filtering and export options

## Prerequisites

- Python 3.7 or higher
- Webcam/Camera access
- Modern web browser with camera permissions

## Installation

1. **Clone or download the project**
   ```bash
   cd "Automated Attendance"
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv .venv
   
   # On Windows
   .venv\Scripts\activate
   
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. **Install required dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   **Note**: If you encounter issues installing `face_recognition`, you may need to install additional dependencies:
   
   **On Windows:**
   - Install Visual Studio Build Tools or Visual Studio Community
   - Install CMake: `pip install cmake`
   
   **On macOS:**
   ```bash
   brew install cmake
   ```
   
   **On Linux (Ubuntu/Debian):**
   ```bash
   sudo apt-get install build-essential cmake
   sudo apt-get install libopenblas-dev liblapack-dev
   sudo apt-get install libx11-dev libgtk-3-dev
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   Open your web browser and navigate to: `http://localhost:5000`

## Usage

### 1. Dashboard
- Access the main dashboard at `http://localhost:5000/dashboard`
- View quick statistics and navigate to different sections
- Export attendance data directly from the dashboard

### 2. Register New Users
1. Click "Register" from the dashboard or navigate to `/register`
2. Enter the user's full name and email (optional)
3. Click "Start Camera" to activate webcam
4. Position the person's face in the camera view
5. Click "Capture Photo" when ready
6. Review the captured image and click "Register User"

**Registration Tips:**
- Ensure good lighting on the face
- Look directly at the camera
- Remove glasses, hats, or face coverings if possible
- Keep a neutral expression
- Only one face should be visible in the frame

### 3. Mark Attendance
1. Navigate to "Mark Attendance" or go to `/attendance`
2. Click "Start Camera" to begin
3. Click "Recognize Face" to start face recognition
4. Position yourself in front of the camera
5. The system will automatically recognize and mark attendance
6. View real-time recognition results and today's attendance list

**Attendance Tips:**
- Ensure the same lighting conditions as during registration
- Look directly at the camera
- Stay still during recognition process
- The system prevents duplicate attendance for the same day

### 4. View Records
1. Go to "View Records" or navigate to `/records`
2. View comprehensive attendance statistics
3. Filter records by date or user
4. Export filtered data to CSV
5. View all registered users

## API Endpoints

The system provides RESTful API endpoints:

- `POST /api/register` - Register a new user with face data
- `POST /api/recognize` - Recognize face and optionally mark attendance
- `GET /api/attendance` - Get attendance records (with optional date filter)
- `GET /api/users` - Get list of registered users
- `GET /api/export/csv` - Export attendance data to CSV

## File Structure

```
Automated Attendance/
├── app.py                 # Main Flask application
├── face_utils.py          # Face recognition utilities
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── attendance.db         # SQLite database (created automatically)
├── face_encodings/       # Directory for face encoding files (created automatically)
├── static/               # Static files and exports (created automatically)
└── templates/            # HTML templates
    ├── dashboard.html    # Main dashboard
    ├── register.html     # User registration
    ├── attendance.html   # Attendance marking
    ├── records.html      # Records viewing
    ├── index.html        # Landing page
    └── home.htm          # Alternative home page
```

## Database Schema

The system uses SQLite with two main tables:

**Users Table:**
- `id` (Primary Key)
- `name` (Unique)
- `email`
- `created_at`

**Attendance Table:**
- `id` (Primary Key)
- `user_id` (Foreign Key)
- `name`
- `timestamp`
- `status`

## Configuration

### Face Recognition Settings
You can modify face recognition parameters in `face_utils.py`:
- `tolerance`: Recognition sensitivity (default: 0.6)
- Image quality and size settings
- Database paths

### Flask Settings
Modify Flask settings in `app.py`:
- Debug mode
- Host and port configuration
- File upload settings

## Troubleshooting

### Common Issues

1. **Camera Access Denied**
   - Ensure browser has camera permissions
   - Check if camera is being used by another application
   - Try refreshing the page and allowing camera access

2. **Face Recognition Not Working**
   - Ensure good lighting conditions
   - Check if the person is registered in the system
   - Verify face is clearly visible and unobstructed

3. **Installation Issues**
   - Make sure you have the correct Python version
   - Install Visual Studio Build Tools on Windows
   - Check that all dependencies are properly installed

4. **Database Issues**
   - The SQLite database is created automatically
   - Check file permissions in the project directory
   - Delete `attendance.db` to reset the database

5. **Performance Issues**
   - Face recognition can be CPU-intensive
   - Consider reducing image quality for better performance
   - Ensure adequate system resources

### Error Messages

- **"No face detected"**: Ensure face is visible and well-lit
- **"Multiple faces detected"**: Only one person should be in the camera view
- **"Face not recognized"**: Person may not be registered or lighting conditions differ
- **"Attendance already marked"**: Attendance can only be marked once per day

## Security Considerations

- Face encoding data is stored locally in pickle files
- Database contains personal information - secure appropriately
- Consider implementing user authentication for production use
- Regularly backup attendance data
- Be mindful of privacy regulations when deploying

## Development

To extend or modify the system:

1. **Adding New Features**: Modify `app.py` for new routes and `face_utils.py` for face recognition logic
2. **UI Changes**: Update HTML templates in the `templates/` directory
3. **Database Changes**: Modify the database schema in `face_utils.py`
4. **API Extensions**: Add new endpoints in `app.py`

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the error messages and logs
3. Ensure all dependencies are properly installed
4. Verify camera and browser permissions

## Version History

- **v1.0.0**: Initial release with core face recognition and attendance features
  - User registration with face capture
  - Real-time face recognition and attendance marking
  - Web-based dashboard and records management
  - CSV export functionality
  - SQLite database integration

---

**Note**: This system is designed for educational and small-scale use. For production deployment, consider additional security measures, user authentication, and scalability improvements.


