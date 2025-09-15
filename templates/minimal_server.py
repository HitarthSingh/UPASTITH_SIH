from flask import Flask, request, jsonify, render_template, session, redirect, send_from_directory, make_response
from flask_cors import CORS
import os
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import random
import secrets
from datetime import datetime, timedelta
from face_utils import FaceRecognitionSystem
try:
    from enhanced_face_utils import EnhancedFaceRecognitionSystem
except Exception:
    EnhancedFaceRecognitionSystem = None

from db_leaves import init_leave_db
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Configure Flask session settings for proper session management
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

CORS(app, supports_credentials=True)

# Initialize face recognition systems
face_system = FaceRecognitionSystem()  # Legacy system
if EnhancedFaceRecognitionSystem is not None:
    try:
        enhanced_face_system = EnhancedFaceRecognitionSystem()  # Enhanced with liveness detection
    except Exception:
        # Instantiate stub on error
        class _EnhancedStub:
            def check_liveness_model(self):
                return False
            def get_attendance_records(self, date=None):
                return {"success": True, "records": []}
        enhanced_face_system = _EnhancedStub()
else:
    class _EnhancedStub:
        def check_liveness_model(self):
            return False
        def get_attendance_records(self, date=None):
            return {"success": True, "records": []}
    enhanced_face_system = _EnhancedStub()

# Session validation middleware
def require_login(user_type=None):
    """Decorator to require login for routes"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'success': False, 'message': 'Please log in first'}), 401
            
            # Check if user type matches if specified
            if user_type and session.get('user_type') != user_type:
                return jsonify({'success': False, 'message': f'{user_type.title()} access required'}), 403
            
            # Check if session has expired by checking database
            try:
                conn = sqlite3.connect('authentication.db')
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT expires_at FROM sessions 
                    WHERE user_id = ? AND expires_at > datetime('now')
                ''', (session['user_id'],))
                valid_session = cursor.fetchone()
                conn.close()
                
                if not valid_session:
                    # Session expired or doesn't exist, clear it
                    session.clear()
                    return jsonify({'success': False, 'message': 'Session expired, please log in again'}), 401
                    
            except Exception as e:
                print(f"Error validating session: {e}")
                # If there's an error checking session, require re-login
                session.clear()
                return jsonify({'success': False, 'message': 'Session validation failed, please log in again'}), 401
            
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

# Middleware to check session validity on every request
@app.before_request
def validate_session():
    """Validate session on protected routes"""
    protected_routes = [
        '/studentdashboard', '/teacherdashboard', '/api/student/', '/api/teacher/', 
        '/api/mark_attendance_face', '/api/leave/submit'
    ]
    
    # Skip validation for static files, login routes, public API endpoints, and landing page with any parameters
    if (request.endpoint in ['static', 'landing_page', 'teacherlogin', 'student_login_form', 'teacher_login_form'] or 
        request.path.startswith('/api/login') or 
        request.path.startswith('/api/logout') or
        request.path.startswith('/api/test') or
        request.path.startswith('/api/registerfinal1') or
        request.path.startswith('/api/recognizefinal1') or
        request.path == '/' or
        request.path.startswith('/?') or  # Skip landing page with any query parameters
        request.path.startswith('/login/') or  # Skip form-based login routes
        request.path.startswith('/forgetpassword') or
        request.path.startswith('/aboutus') or
        request.path.startswith('/suggestionbox') or
        request.path.endswith('.css') or
        request.path.endswith('.js') or
        request.path.endswith('.png') or
        request.path.endswith('.jpg') or
        request.path.endswith('.ico') or
        request.path.endswith('.html')):
        return
    
    # Check if this is a protected route
    for route in protected_routes:
        if request.path.startswith(route):
            if 'user_id' not in session:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'message': 'Please log in first'}), 401
                else:
                    return redirect('/?error=login_required')
            
            # Validate session in database
            try:
                conn = sqlite3.connect('authentication.db')
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT expires_at FROM sessions 
                    WHERE user_id = ? AND expires_at > datetime('now')
                ''', (session['user_id'],))
                valid_session = cursor.fetchone()
                conn.close()
                
                if not valid_session:
                    session.clear()
                    if request.path.startswith('/api/'):
                        return jsonify({'success': False, 'message': 'Session expired, please log in again'}), 401
                    else:
                        return redirect('/?error=session_expired')
                        
            except Exception as e:
                print(f"Error validating session in middleware: {e}")
                session.clear()
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'message': 'Session validation failed'}), 401
                else:
                    return redirect('/?error=session_error')
            break

@app.route("/")
def landing_page():
    return render_template("landingpagefinal1.html")

@app.route("/teacherloginpage")
def teacherlogin():
    return render_template("teacherloginpage.html")


@app.route("/studentdashboard")
def student_dashboard():
    response = make_response(render_template("studentdashboard.html"))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/demoleave")
def demo_leave():
    return render_template("demoleave.html")

@app.route("/timetable")
def timetable():
    response = make_response(render_template("timetable.html"))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/repository")
def repository():
    response = make_response(render_template("repository.html"))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/studentresult")
def student_result():
    response = make_response(render_template("studentresult.html"))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/aboutus")
def aboutus():
    return render_template("aboutus.html")

@app.route("/suggestionbox")
def suggestion_box():
    response = make_response(render_template("suggestionbox.html"))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/register_face")
def register_face_page():
    return render_template("register_face.html")

# Route to serve static files (images) from templates directory
@app.route('/<path:filename>')
def serve_static_files(filename):
    # Check if the file exists in templates directory
    templates_path = os.path.join(app.root_path, 'templates')
    if os.path.exists(os.path.join(templates_path, filename)):
        return send_from_directory(templates_path, filename)
    # If not found, return 404
    return "File not found", 404

@app.route("/forgetpassword")
def forget_password():
    return render_template("forgetpassword.html")

@app.route("/forgetpasswordteacher")
def forget_password_teacher():
    return render_template("forgetpassword.html")

@app.route("/teacherdashboard")
def teacher_dashboard():
    # Determine user name and department from session or authentication DB
    user_name = session.get('full_name') or session.get('username')
    user_department = None
    try:
        if 'user_id' in session:
            conn = sqlite3.connect('authentication.db')
            cursor = conn.cursor()
            cursor.execute('SELECT full_name, teacher_id FROM users WHERE id = ?', (session['user_id'],))
            row = cursor.fetchone()
            conn.close()
            if row:
                if not user_name:
                    user_name = row[0]
                teacher_id = row[1]
                dept_map = {
                    'TCH001': 'Computer Science',
                    'TCH002': 'Mathematics'
                }
                if teacher_id and teacher_id in dept_map:
                    user_department = dept_map[teacher_id]
    except Exception as e:
        print(f"Warning: could not fetch user info: {e}")

    user_name = user_name or 'Prof. Eleanor'
    user_department = user_department or 'Computer Science'
    return render_template("teacherdasboardfinal.html", user_name=user_name, user_department=user_department)

# Authentication functions
def init_auth_db():
    """Initialize authentication database"""
    conn = sqlite3.connect('authentication.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            user_type TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            student_id TEXT,
            teacher_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def init_attendance_db():
    """Initialize attendance database"""
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    
    # Create attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'present',
            confidence REAL,
            method TEXT DEFAULT 'face_recognition'
        )
    ''')
    
    # Create class_attendance table for class-specific attendance
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS class_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            class_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'present',
            confidence REAL,
            method TEXT DEFAULT 'face_recognition'
        )
    ''')
    
    conn.commit()
    conn.close()

def create_sample_users():
    """Create sample users if they don't exist"""
    conn = sqlite3.connect('authentication.db')
    cursor = conn.cursor()
    
    # Check if data already exists
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    
    # Create sample users
    users = [
        ('student1', 'password123', 'student', 'Alice Johnson', 'alice@example.com', 'STU001', None),
        ('student2', 'password123', 'student', 'Bob Smith', 'bob@example.com', 'STU002', None),
        ('student3', 'password123', 'student', 'Charlie Brown', 'charlie@example.com', 'STU003', None),
        ('teacher1', 'teacher123', 'teacher', 'Prof. Eleanor', 'eleanor@example.com', None, 'TCH001'),
        ('teacher2', 'teacher123', 'teacher', 'Dr. Smith', 'smith@example.com', None, 'TCH002'),
        ('admin', 'admin123', 'admin', 'Admin User', 'admin@example.com', None, None)
    ]
    
    for username, password, user_type, full_name, email, student_id, teacher_id in users:
        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (username, password_hash, user_type, full_name, email, student_id, teacher_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (username, password_hash, user_type, full_name, email, student_id, teacher_id))
    
    conn.commit()
    conn.close()

# Leave request database functions
def init_leave_db(db_path: str = 'leaves.db') -> None:
    """Ensure leaves.db has the expected leave_applications schema."""
    conn = sqlite3.connect(db_path)
    try:
        c = conn.cursor()

        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leave_applications'")
        exists = c.fetchone() is not None

        desired_columns = [
            ("id", "INTEGER PRIMARY KEY AUTOINCREMENT", 1),
            ("student_name", "TEXT", 1),
            ("student_id", "TEXT", 0),
            ("reason", "TEXT", 1),
            ("start_date", "TEXT", 1),
            ("end_date", "TEXT", 1),
            ("status", "TEXT", 0),
            ("attached_document", "TEXT", 0),
            ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", 0),
            ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", 0),
        ]

        def create_with_desired_schema(table_name: str) -> None:
            c.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_name TEXT NOT NULL,
                    student_id TEXT,
                    reason TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    attached_document TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

        if not exists:
            create_with_desired_schema("leave_applications")
            conn.commit()
            return

        c.execute("PRAGMA table_info(leave_applications)")
        current_info = c.fetchall()
        current_cols = [(row[1], row[2], row[3]) for row in current_info]

        # Check if we need to update schema
        current_col_names = {name for (name, _type, _nn) in current_cols}
        desired_col_names = {name for (name, _type, _nn) in desired_columns}
        
        if not desired_col_names.issubset(current_col_names):
            create_with_desired_schema("leave_applications_new")

            copy_cols = [name for (name, _type, _nn) in desired_columns if name in current_col_names and name != "attached_document"]
            if copy_cols:
                cols_csv = ", ".join(copy_cols)
                c.execute(
                    f"INSERT INTO leave_applications_new ({cols_csv}) SELECT {cols_csv} FROM leave_applications"
                )

            c.execute("DROP TABLE leave_applications")
            c.execute("ALTER TABLE leave_applications_new RENAME TO leave_applications")

        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

def create_sample_leave_requests():
    """Create sample leave requests for testing"""
    conn = sqlite3.connect('leaves.db')
    cursor = conn.cursor()
    
    # Check if data already exists
    cursor.execute('SELECT COUNT(*) FROM leave_applications')
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    
    # Create sample leave requests
    sample_requests = [
        ('Alice Johnson', 'STU001', 'Family function, will be out of station.', '2025-09-15', '2025-09-16', 'pending'),
        ('Bob Williams', 'STU002', 'Not feeling well, have a doctor\'s appointment.', '2025-09-12', '2025-09-12', 'pending'),
        ('Charlie Brown', 'STU003', 'Have to attend a workshop for my internship.', '2025-09-18', '2025-09-19', 'pending'),
    ]
    
    for student_name, student_id, reason, start_date, end_date, status in sample_requests:
        cursor.execute('''
            INSERT INTO leave_applications (student_name, student_id, reason, start_date, end_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (student_name, student_id, reason, start_date, end_date, status))
    
    conn.commit()
    conn.close()

# Attendance database functions
def init_attendance_db(db_path: str = 'attendance.db') -> None:
    """Create the attendance database and required tables if they don't exist."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'present',
                date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )

        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

def create_sample_attendance_users():
    """Create sample users for attendance system"""
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    
    # Check if data already exists
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    
    # Create sample users
    sample_users = [
        ('Alice Johnson', 'alice@example.com'),
        ('Bob Williams', 'bob@example.com'),
        ('Charlie Brown', 'charlie@example.com'),
        ('Diana Prince', 'diana@example.com'),
        ('Edward Nygma', 'edward@example.com'),
        ('Frank Castle', 'frank@example.com'),
        ('Gwen Stacy', 'gwen@example.com'),
        ('Harvey Dent', 'harvey@example.com'),
    ]
    
    for name, email in sample_users:
        cursor.execute('''
            INSERT INTO users (name, email)
            VALUES (?, ?)
        ''', (name, email))
    
    conn.commit()
    conn.close()

# Classes database functions
def init_classes_db(db_path: str = 'classes.db') -> None:
    """Create the classes database and required tables if they don't exist."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Create classes table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_name TEXT NOT NULL,
                teacher_id TEXT NOT NULL,
                teacher_name TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                day_of_week TEXT NOT NULL,
                room_number TEXT,
                semester TEXT DEFAULT 'current',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Create student_enrollments table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS student_enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                class_id INTEGER NOT NULL,
                enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (class_id) REFERENCES classes (id)
            )
            """
        )

        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

def create_sample_classes():
    """Initialize empty classes database - no hardcoded classes"""
    try:
        conn = sqlite3.connect('classes.db')
        cursor = conn.cursor()
        
        # Clear existing data to start fresh
        cursor.execute('DELETE FROM student_enrollments')
        cursor.execute('DELETE FROM classes')
        
        conn.commit()
        conn.close()
        
        print("✅ Classes database initialized - no hardcoded classes")
        print("📝 Teachers can now add classes through the dashboard")
        
    except Exception as e:
        print(f"Error initializing classes database: {e}")

# Notes database functions
def init_notes_db(db_path: str = 'notes.db') -> None:
    """Create the notes database and required tables if they don't exist."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                teacher_id TEXT,
                teacher_name TEXT,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notes_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                student_id TEXT NOT NULL,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(note_id, student_id)
            )
            """
        )

        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

def create_sample_leave_requests():
    """Create sample leave requests for testing"""
    try:
        conn = sqlite3.connect('leaves.db')
        cursor = conn.cursor()
        
        # Check if data already exists
        cursor.execute('SELECT COUNT(*) FROM leave_applications')
        if cursor.fetchone()[0] > 0:
            conn.close()
            return
        
        # Sample leave requests
        sample_requests = [
            ('Alice Johnson', 'STU001', 'Medical appointment', '2024-01-15', '2024-01-15'),
            ('Bob Smith', 'STU002', 'Family emergency', '2024-01-16', '2024-01-17'),
            ('Charlie Brown', 'STU003', 'Personal reasons', '2024-01-18', '2024-01-18'),
        ]
        
        for request_data in sample_requests:
            cursor.execute('''
                INSERT INTO leave_applications (student_name, student_id, reason, start_date, end_date, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            ''', request_data)
        
        conn.commit()
        conn.close()
        print("Sample leave requests created successfully")
        
    except Exception as e:
        print(f"Error creating sample leave requests: {e}")

def create_sample_enrollments():
    """Create sample student enrollments"""
    conn = sqlite3.connect('classes.db')
    cursor = conn.cursor()
    
    # Check if data already exists
    cursor.execute('SELECT COUNT(*) FROM student_enrollments')
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    
    # Get all class IDs
    cursor.execute('SELECT id FROM classes')
    class_ids = [row[0] for row in cursor.fetchall()]
    
    # Enroll all sample students in all classes
    students = ['STU001', 'STU002', 'STU003']
    
    for student_id in students:
        for class_id in class_ids:
            cursor.execute('''
                INSERT INTO student_enrollments (student_id, class_id)
                VALUES (?, ?)
            ''', (student_id, class_id))
    
    conn.commit()
    conn.close()

# Initialize authentication, leave, attendance, and classes systems
init_auth_db()
create_sample_users()
init_leave_db()
create_sample_leave_requests()
init_attendance_db()
create_sample_attendance_users()
init_classes_db()
create_sample_classes()
create_sample_enrollments()
init_notes_db()

@app.route("/api/test", methods=["GET", "POST"])
def test_endpoint():
    return jsonify({
        "success": True, 
        "message": "Server is working", 
        "method": request.method,
        "endpoint": "/api/test"
    })

@app.route("/api/registerfinal1", methods=["POST"])
def register_face_legacy():
    try:
        data = request.get_json()
        
        if not data or 'name' not in data or 'image' not in data:
            return jsonify({
                "success": False,
                "message": "Missing required fields: name and image"
            })
        
        name = data['name']
        image_data = data['image']
        email = data.get('email', None)
        
        # Use the face recognition system to register the face
        result = face_system.register_face(name, image_data, email)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route("/api/recognizefinal1", methods=["POST"])
def recognize_face():
    """Legacy face recognition without liveness detection (INSECURE)"""
    try:
        data = request.get_json()
        
        if not data or 'image' not in data:
            return jsonify({
                "success": False,
                "message": "Missing required field: image"
            })
        
        image_data = data['image']
        
        # Use the face recognition system to recognize the face
        recognition_result = face_system.recognize_face(image_data)
        
        if not recognition_result["success"]:
            return jsonify(recognition_result)
        
        name = recognition_result["name"]
        confidence = recognition_result["confidence"]
        
        # Check if attendance already marked today and mark if not
        attendance_result = face_system.mark_attendance(name)
        
        if attendance_result["success"]:
            attendance_message = f"⚠️ Face recognized: {name}! Attendance marked (NO LIVENESS VERIFICATION - INSECURE)."
            return jsonify({
                "success": True,
                "name": name,
                "confidence": confidence,
                "attendance_marked": True,
                "attendance_message": attendance_message,
                "message": attendance_message,
                "received_data": bool(data),
                "liveness_verified": False,
                "security_warning": "This method can be spoofed with photos. Use /api/recognize_with_liveness for secure authentication."
            })
        else:
            # Attendance already marked
            return jsonify({
                "success": True,
                "name": name,
                "confidence": confidence,
                "attendance_marked": False,
                "attendance_message": attendance_result["message"],
                "message": attendance_result["message"],
                "received_data": bool(data),
                "liveness_verified": False,
                "security_warning": "This method can be spoofed with photos. Use /api/recognize_with_liveness for secure authentication."
            })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

# Enhanced Face Recognition API Endpoints with Liveness Detection

@app.route("/api/register_with_liveness", methods=["POST"])
def register_face_with_liveness():
    """Register a new face with liveness verification (SECURE)"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({
                "success": False,
                "message": "Missing required field: name"
            })
        
        name = data['name']
        email = data.get('email', None)
        
        # Check if liveness detection is available
        if not enhanced_face_system.check_liveness_model():
            return jsonify({
                "success": False,
                "message": "Liveness detection model not available. Please run setup_liveness.py first."
            })
        
        # This endpoint requires webcam access, so it should be called from a desktop application
        # For web applications, you would need to implement a different approach
        return jsonify({
            "success": False,
            "message": "This endpoint requires direct webcam access. Please use the desktop application or test_liveness.py script."
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route("/api/recognize_with_liveness", methods=["POST"])
def recognize_face_with_liveness():
    """Recognize face with liveness verification (SECURE)"""
    try:
        # Check if liveness detection is available
        if not enhanced_face_system.check_liveness_model():
            return jsonify({
                "success": False,
                "message": "Liveness detection model not available. Please run setup_liveness.py first."
            })
        
        # This endpoint requires webcam access, so it should be called from a desktop application
        # For web applications, you would need to implement a different approach
        return jsonify({
            "success": False,
            "message": "This endpoint requires direct webcam access. Please use the desktop application or test_liveness.py script."
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route("/api/liveness_status", methods=["GET"])
def check_liveness_status():
    """Check if liveness detection is available"""
    try:
        model_available = enhanced_face_system.check_liveness_model()
        
        return jsonify({
            "success": True,
            "liveness_available": model_available,
            "message": "Liveness detection is ready" if model_available else "Liveness detection model not found. Run setup_liveness.py to install.",
            "setup_required": not model_available
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route("/api/attendance_records_enhanced", methods=["GET"])
def get_enhanced_attendance_records():
    """Get attendance records with liveness verification info"""
    try:
        date = request.args.get('date')
        result = enhanced_face_system.get_attendance_records(date)
        
        if result["success"]:
            # Add security analysis
            records = result["records"]
            total_records = len(records)
            secure_records = sum(1 for r in records if r.get('liveness_verified', False))
            insecure_records = total_records - secure_records
            
            return jsonify({
                "success": True,
                "records": records,
                "security_summary": {
                    "total_records": total_records,
                    "secure_with_liveness": secure_records,
                    "insecure_without_liveness": insecure_records,
                    "security_percentage": (secure_records / total_records * 100) if total_records > 0 else 0
                }
            })
        else:
            return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

# Authentication routes
@app.route('/api/login', methods=['POST'])
def login():
    """Handle login for both students and teachers"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user_type = data.get('user_type', 'student')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400
    
    conn = sqlite3.connect('authentication.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, username, password_hash, user_type, full_name, email, student_id, teacher_id
        FROM users WHERE username = ? AND user_type = ?
    ''', (username, user_type))
    
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user[2], password):
        # Create session
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['user_type'] = user[3]
        session['full_name'] = user[4]
        
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=24)
        
        conn = sqlite3.connect('authentication.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sessions (user_id, session_token, expires_at)
            VALUES (?, ?, ?)
        ''', (user[0], session_token, expires_at))
        conn.commit()
        conn.close()
        
        # Determine redirect URL
        if user_type == 'student':
            redirect_url = '/studentdashboard'
        elif user_type == 'teacher':
            redirect_url = '/teacherdashboard'
        else:
            redirect_url = '/'
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user[0],
                'username': user[1],
                'user_type': user[3],
                'full_name': user[4],
                'email': user[5],
                'student_id': user[6],
                'teacher_id': user[7]
            },
            'redirect_url': redirect_url
        })
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    """Handle logout - properly clear all session data"""
    try:
        user_id = session.get('user_id')
        username = session.get('username')
        user_type = session.get('user_type')
        
        print(f"🔐 Logout initiated for user: {username} (ID: {user_id}, Type: {user_type})")
        
        if user_id:
            # Remove ALL session tokens from database for this user
            conn = sqlite3.connect('authentication.db')
            cursor = conn.cursor()
            
            # First, check how many sessions exist
            cursor.execute('SELECT COUNT(*) FROM sessions WHERE user_id = ?', (user_id,))
            session_count = cursor.fetchone()[0]
            
            # Delete all sessions for this user
            cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
            deleted_sessions = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            print(f"✅ Removed {deleted_sessions}/{session_count} database sessions for user_id: {user_id}")
        else:
            print("⚠️ No user_id found in session during logout")
        
        # Store session info before clearing for logging
        session_info = dict(session)
        
        # Clear the Flask session completely
        session.clear()
        
        # Create response with comprehensive session termination
        response = jsonify({
            'success': True, 
            'message': 'Session terminated successfully',
            'session_cleared': True,
            'user_logged_out': username or 'Unknown',
            'timestamp': datetime.now().isoformat()
        })
        
        # Explicitly expire ALL possible session cookies
        response.set_cookie('session', '', expires=0, httponly=True, samesite='Lax', path='/')
        response.set_cookie('flask-session', '', expires=0, httponly=True, samesite='Lax', path='/')
        
        # Add cache control headers to prevent caching
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        print(f"✅ Session cleared and logout completed successfully for {username}")
        return response
        
    except Exception as e:
        print(f"❌ Error during logout: {e}")
        # Even if there's an error, clear the session
        session.clear()
        response = jsonify({
            'success': True, 
            'message': 'Session terminated with warnings',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        
        # Still expire cookies even on error
        response.set_cookie('session', '', expires=0, httponly=True, samesite='Lax', path='/')
        response.set_cookie('flask-session', '', expires=0, httponly=True, samesite='Lax', path='/')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response

@app.route('/login/student', methods=['POST'])
def student_login_form():
    """Handle student login from form"""
    username = request.form.get('student_id')
    password = request.form.get('password')
    
    if not username or not password:
        return redirect('/?error=missing_fields')
    
    conn = sqlite3.connect('authentication.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, username, password_hash, user_type, full_name, email, student_id, teacher_id
        FROM users WHERE username = ? AND user_type = 'student'
    ''', (username,))
    
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user[2], password):
        # Create session
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['user_type'] = user[3]
        session['full_name'] = user[4]
        
        # Generate session token for database
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=24)
        
        conn = sqlite3.connect('authentication.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sessions (user_id, session_token, expires_at)
            VALUES (?, ?, ?)
        ''', (user[0], session_token, expires_at))
        conn.commit()
        conn.close()
        
        return redirect('/studentdashboard')
    else:
        return redirect('/?error=invalid_credentials')

@app.route('/login/teacher', methods=['POST'])
def teacher_login_form():
    """Handle teacher login from form"""
    username = request.form.get('teacher_id')
    password = request.form.get('password')
    
    print(f"Teacher login attempt - Username: {username}, Password provided: {bool(password)}")
    
    if not username or not password:
        print("Missing username or password")
        return redirect('/teacherloginpage?error=missing_fields')
    
    conn = sqlite3.connect('authentication.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, username, password_hash, user_type, full_name, email, student_id, teacher_id
        FROM users WHERE username = ? AND user_type = 'teacher'
    ''', (username,))
    
    user = cursor.fetchone()
    print(f"User found in database: {bool(user)}")
    
    if user:
        print(f"User details - ID: {user[0]}, Username: {user[1]}, Type: {user[3]}")
        password_valid = check_password_hash(user[2], password)
        print(f"Password valid: {password_valid}")
    
    conn.close()
    
    if user and check_password_hash(user[2], password):
        # Create session
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['user_type'] = user[3]
        session['full_name'] = user[4]
        
        # Generate session token for database
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=24)
        
        conn = sqlite3.connect('authentication.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sessions (user_id, session_token, expires_at)
            VALUES (?, ?, ?)
        ''', (user[0], session_token, expires_at))
        conn.commit()
        conn.close()
        
        print(f"Login successful, redirecting to /teacherdashboard")
        return redirect('/teacherdashboard')
    else:
        print("Login failed - invalid credentials")
        return redirect('/teacherloginpage?error=invalid_credentials')

# Leave Request API Endpoints
@app.route('/api/leave/submit', methods=['POST'])
def submit_leave_request():
    """Submit a new leave request"""
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            student_name = data.get('student_name')
            student_id = data.get('student_id')
            reason = data.get('reason')
            start_date = data.get('start_date')
            end_date = data.get('end_date')
        else:
            # Handle form data (multipart/form-data)
            if 'user_id' not in session:
                return jsonify({'success': False, 'message': 'Please log in first'}), 401
            
            # Get student information from session
            conn = sqlite3.connect('authentication.db')
            cursor = conn.cursor()
            cursor.execute('SELECT student_id, full_name FROM users WHERE id = ?', (session['user_id'],))
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            student_id = user[0] or f"student_{session['user_id']}"
            student_name = user[1]
            reason = request.form.get('reason')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
        
        if not all([student_name, reason, start_date, end_date]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        conn = sqlite3.connect('leaves.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO leave_applications (student_name, student_id, reason, start_date, end_date, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        ''', (student_name, student_id, reason, start_date, end_date))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Leave request submitted successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/leave/requests', methods=['GET'])
def get_leave_requests():
    """Get all pending leave requests for teachers"""
    try:
        conn = sqlite3.connect('leaves.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, student_name, student_id, reason, start_date, end_date, status, created_at
            FROM leave_applications
            WHERE status = 'pending'
            ORDER BY created_at DESC
        ''')
        
        requests = cursor.fetchall()
        conn.close()
        
        leave_requests = []
        for req in requests:
            leave_requests.append({
                'id': req[0],
                'student_name': req[1],
                'student_id': req[2],
                'reason': req[3],
                'start_date': req[4],
                'end_date': req[5],
                'status': req[6],
                'created_at': req[7]
            })
        
        return jsonify({
            'success': True,
            'requests': leave_requests
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/leave/approve/<int:request_id>', methods=['POST'])
def approve_leave_request(request_id):
    """Approve a leave request"""
    try:
        conn = sqlite3.connect('leaves.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE leave_applications 
            SET status = 'approved', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (request_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'message': 'Leave request not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Leave request approved successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/leave/reject/<int:request_id>', methods=['POST'])
def reject_leave_request(request_id):
    """Reject a leave request"""
    try:
        conn = sqlite3.connect('leaves.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE leave_applications 
            SET status = 'rejected', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (request_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'message': 'Leave request not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Leave request rejected successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/teacher/me', methods=['GET'])
def get_current_teacher():
    """Get current logged-in teacher information"""
    try:
        if 'user_id' not in session or session.get('user_type') != 'teacher':
            return jsonify({'success': False, 'message': 'Please log in as a teacher first'}), 401
        
        conn = sqlite3.connect('authentication.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, full_name, email, teacher_id
            FROM users 
            WHERE id = ? AND user_type = 'teacher'
        ''', (session['user_id'],))
        
        teacher = cursor.fetchone()
        conn.close()
        
        if not teacher:
            return jsonify({'success': False, 'message': 'Teacher not found'}), 404
        
        # Generate avatar URL based on teacher name
        initials = ''.join([word[0].upper() for word in teacher[2].split()[:2]]) if teacher[2] else 'T'
        avatar_url = f'https://placehold.co/40x40/d8ccf2/02020a?text={initials}'
        
        return jsonify({
            'success': True,
            'teacher': {
                'id': teacher[0],
                'username': teacher[1],
                'name': teacher[2] or teacher[1],
                'email': teacher[3],
                'teacher_id': teacher[4],
                'department': 'Computer Science',  # Default department
                'avatarUrl': avatar_url
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# ========= Notes API =========

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
if not os.path.isdir(UPLOAD_DIR):
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    except Exception as _e:
        print(f"Warning: could not create uploads directory: {_e}")

def _get_student_identity_from_session():
    conn = sqlite3.connect('authentication.db')
    try:
        cur = conn.cursor()
        cur.execute('SELECT student_id, full_name FROM users WHERE id = ?', (session['user_id'],))
        row = cur.fetchone()
        if row:
            return row[0], row[1]
        return None, None
    finally:
        conn.close()

@app.route('/api/notes/upload', methods=['POST'])
def upload_notes():
    """Teacher uploads a file for a class/subject."""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Please log in first'}), 401
        # Fetch teacher info
        conn = sqlite3.connect('authentication.db')
        cur = conn.cursor()
        cur.execute('SELECT teacher_id, full_name, username FROM users WHERE id = ? AND user_type = "teacher"', (session['user_id'],))
        teacher = cur.fetchone()
        conn.close()
        if not teacher:
            return jsonify({'success': False, 'message': 'Teacher access required'}), 403

        subject = request.form.get('subject') or request.form.get('class_id') or ''
        class_id = request.form.get('class_id') or subject
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'success': False, 'message': 'Empty filename'}), 400

        safe_name = secure_filename(file.filename)
        saved_path = os.path.join(UPLOAD_DIR, safe_name)
        # Ensure unique filename
        base, ext = os.path.splitext(safe_name)
        counter = 1
        while os.path.exists(saved_path):
            safe_name = f"{base}_{counter}{ext}"
            saved_path = os.path.join(UPLOAD_DIR, safe_name)
            counter += 1
        file.save(saved_path)

        # Insert record
        conn = sqlite3.connect('notes.db')
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO notes (class_id, subject, teacher_id, teacher_name, file_name, file_path) VALUES (?, ?, ?, ?, ?, ?)',
            (class_id, subject or class_id, teacher[0] or '', teacher[1] or '', safe_name, saved_path)
        )
        note_id = cur.lastrowid
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'File uploaded', 'note_id': note_id, 'file_name': safe_name})
    except Exception as e:
        print(f"Error in upload_notes: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/notes/unseen', methods=['GET'])
def get_unseen_notes():
    """Get notes not yet viewed by the logged-in student. Optional filter by subject/class_id."""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Please log in first'}), 401
        student_id, student_name = _get_student_identity_from_session()
        if not student_id:
            return jsonify({'success': False, 'message': 'Student not found'}), 404
        subject = request.args.get('subject')
        class_id = request.args.get('class_id')

        conn = sqlite3.connect('notes.db')
        cur = conn.cursor()
        query = (
            "SELECT id, class_id, subject, teacher_name, file_name, uploaded_at FROM notes "
            "WHERE id NOT IN (SELECT note_id FROM notes_views WHERE student_id = ?)"
        )
        params = [student_id]
        if subject:
            query += " AND subject = ?"
            params.append(subject)
        if class_id:
            query += " AND class_id = ?"
            params.append(class_id)
        query += " ORDER BY uploaded_at DESC"
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        conn.close()

        notes = [
            {
                'id': r[0],
                'class_id': r[1],
                'subject': r[2],
                'teacher_name': r[3],
                'file_name': r[4],
                'uploaded_at': r[5]
            } for r in rows
        ]
        return jsonify({'success': True, 'notes': notes})
    except Exception as e:
        print(f"Error in get_unseen_notes: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/notes/list', methods=['GET'])
def list_notes():
    """List notes, optionally filtered by class_id/subject. If mine=true and user is teacher, only their uploads."""
    try:
        class_id = request.args.get('class_id')
        subject = request.args.get('subject')
        mine = request.args.get('mine') in ['1', 'true', 'True']

        teacher_id = None
        if mine and 'user_id' in session and session.get('user_type') == 'teacher':
            conn_auth = sqlite3.connect('authentication.db')
            cur_auth = conn_auth.cursor()
            cur_auth.execute('SELECT teacher_id, username FROM users WHERE id = ?', (session['user_id'],))
            t = cur_auth.fetchone()
            conn_auth.close()
            if t:
                teacher_id = t[0] if t[0] else ('TCH001' if t[1] == 'teacher1' else 'TCH002' if t[1] == 'teacher2' else None)

        conn = sqlite3.connect('notes.db')
        cur = conn.cursor()
        query = "SELECT id, class_id, subject, teacher_name, teacher_id, file_name, uploaded_at FROM notes WHERE 1=1"
        params = []
        if class_id:
            query += " AND class_id = ?"
            params.append(class_id)
        if subject:
            query += " AND subject = ?"
            params.append(subject)
        if teacher_id:
            query += " AND teacher_id = ?"
            params.append(teacher_id)
        query += " ORDER BY uploaded_at DESC"
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        conn.close()

        notes = [
            {
                'id': r[0],
                'class_id': r[1],
                'subject': r[2],
                'teacher_name': r[3],
                'teacher_id': r[4],
                'file_name': r[5],
                'uploaded_at': r[6]
            } for r in rows
        ]
        return jsonify({'success': True, 'notes': notes})
    except Exception as e:
        print(f"Error in list_notes: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/notes/mark_viewed', methods=['POST'])
def mark_notes_viewed():
    """Mark provided note IDs as viewed for the current student."""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Please log in first'}), 401
        data = request.get_json() or {}
        note_ids = data.get('note_ids', [])
        if not note_ids:
            return jsonify({'success': False, 'message': 'note_ids required'}), 400
        student_id, _ = _get_student_identity_from_session()
        if not student_id:
            return jsonify({'success': False, 'message': 'Student not found'}), 404
        conn = sqlite3.connect('notes.db')
        cur = conn.cursor()
        for nid in note_ids:
            try:
                cur.execute('INSERT OR IGNORE INTO notes_views (note_id, student_id) VALUES (?, ?)', (nid, student_id))
            except Exception:
                pass
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'marked': len(note_ids)})
    except Exception as e:
        print(f"Error in mark_notes_viewed: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/notes/file/<int:note_id>', methods=['GET'])
def get_note_file(note_id: int):
    """Serve a previously uploaded note file by id."""
    try:
        conn = sqlite3.connect('notes.db')
        cur = conn.cursor()
        cur.execute('SELECT file_name FROM notes WHERE id = ?', (note_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return jsonify({'success': False, 'message': 'Note not found'}), 404
        file_name = row[0]
        return send_from_directory(UPLOAD_DIR, file_name, as_attachment=False)
    except Exception as e:
        print(f"Error in get_note_file: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/student/me', methods=['GET'])
def get_current_student():
    """Get current logged-in student information"""
    try:
        if 'user_id' not in session or session.get('user_type') != 'student':
            return jsonify({'success': False, 'message': 'Please log in as a student first'}), 401
        
        conn = sqlite3.connect('authentication.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, full_name, email, student_id
            FROM users 
            WHERE id = ? AND user_type = 'student'
        ''', (session['user_id'],))
        
        student = cursor.fetchone()
        conn.close()
        
        if not student:
            return jsonify({'success': False, 'message': 'Student not found'}), 404
        
        return jsonify({
            'success': True,
            'student': {
                'id': student[0],
                'username': student[1],
                'name': student[2] or student[1],
                'email': student[3],
                'student_id': student[4]
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# Attendance API Endpoints
@app.route('/api/attendance/today', methods=['GET'])
def get_today_attendance():
    """Get today's attendance records for teacher dashboard"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        conn = sqlite3.connect('attendance.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, timestamp, status
            FROM attendance
            WHERE date = ?
            ORDER BY timestamp DESC
        ''', (today,))
        
        records = cursor.fetchall()
        conn.close()
        
        attendance_records = []
        for record in records:
            attendance_records.append({
                'name': record[0],
                'timestamp': record[1],
                'status': record[2]
            })
        
        return jsonify({
            'success': True,
            'date': today,
            'records': attendance_records
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/attendance/date/<date>', methods=['GET'])
def get_attendance_by_date(date):
    """Get attendance records for a specific date"""
    try:
        conn = sqlite3.connect('attendance.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, timestamp, status
            FROM attendance
            WHERE date = ?
            ORDER BY timestamp DESC
        ''', (date,))
        
        records = cursor.fetchall()
        conn.close()
        
        attendance_records = []
        for record in records:
            attendance_records.append({
                'name': record[0],
                'timestamp': record[1],
                'status': record[2]
            })
        
        return jsonify({
            'success': True,
            'date': date,
            'records': attendance_records
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# Face Recognition API Endpoints
@app.route('/api/users/registered', methods=['GET'])
def get_registered_users():
    """Get list of all registered users"""
    try:
        result = face_system.get_registered_users()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/register_face', methods=['POST'])
def register_face():
    """Register a new face for recognition"""
    try:
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email', '')
        
        if not name:
            return jsonify({'success': False, 'message': 'Name is required'}), 400
        
        # Get uploaded image
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image provided'}), 400
        
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'success': False, 'message': 'No image selected'}), 400
        
        # Read image data
        image_data = image_file.read()
        
        # Convert to base64 for face recognition system
        import base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # Register face
        result = face_system.register_face(name, image_b64, email)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in register_face: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/mark_attendance_face', methods=['POST'])
def mark_attendance_face():
    """Mark attendance using face recognition"""
    try:
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Please log in first'}), 401
        
        # Get form data
        subject = request.form.get('subject')
        student_id = request.form.get('student_id')
        
        if not subject:
            return jsonify({'success': False, 'message': 'Subject is required'}), 400
        
        # Get uploaded image
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image provided'}), 400
        
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'success': False, 'message': 'No image selected'}), 400
        
        # Read image data
        image_data = image_file.read()
        
        # Convert to base64 for face recognition system
        import base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # Recognize face
        recognition_result = face_system.recognize_face(image_b64)
        
        if not recognition_result['success']:
            return jsonify({
                'success': False, 
                'message': recognition_result['message']
            })
        
        recognized_name = recognition_result['name']
        confidence = recognition_result.get('confidence', 0)
        
        # Check if confidence is high enough
        if confidence < 0.6:  # 60% confidence threshold
            return jsonify({
                'success': False,
                'message': f'Face recognition confidence too low ({confidence:.2%}). Please try again with better lighting.'
            })
        
        # Mark attendance directly in class_attendance table with all required fields
        try:
            conn = sqlite3.connect('attendance.db')
            cursor = conn.cursor()
            
            # Create class_attendance table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS class_attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_name TEXT NOT NULL,
                    student_id TEXT,
                    subject TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    recognition_confidence REAL
                )
            ''')
            
            # Check if attendance already marked for this subject today
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT COUNT(*) FROM class_attendance
                WHERE (student_id = ? OR student_name = ?) AND subject = ? AND DATE(timestamp) = ?
            ''', (student_id, recognized_name, subject, today))
            
            count = cursor.fetchone()[0]
            
            if count > 0:
                conn.close()
                return jsonify({
                    'success': False,
                    'message': f'Attendance already marked for {recognized_name} in {subject} today'
                })
            
            # Insert attendance record with all fields
            cursor.execute('''
                INSERT INTO class_attendance (student_name, student_id, subject, recognition_confidence, timestamp)
                VALUES (?, ?, ?, ?, datetime('now'))
            ''', (recognized_name, student_id, subject, confidence))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error recording class attendance: {e}")
            return jsonify({'success': False, 'message': f'Error recording attendance: {str(e)}'}), 500
        
        return jsonify({
            'success': True,
            'message': f'Attendance marked successfully for {recognized_name} in {subject}',
            'student_name': recognized_name,
            'subject': subject,
            'confidence': f'{confidence:.2%}',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error in mark_attendance_face: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

# QR Code Validation Endpoint
@app.route('/api/validate_qr', methods=['POST'])
def validate_qr():
    """Validate QR code scanned by student"""
    try:
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Please log in first'}), 401
        
        data = request.get_json()
        qr_data = data.get('qr_data')
        
        if not qr_data:
            return jsonify({'success': False, 'message': 'QR data is required'}), 400
        
        # Parse QR data format: classId|classDate|timestamp
        try:
            parts = qr_data.split('|')
            if len(parts) != 3:
                return jsonify({'success': False, 'message': 'Invalid QR code format'}), 400
            
            class_id, class_date, qr_timestamp = parts
            qr_timestamp = int(qr_timestamp)
            
        except (ValueError, IndexError):
            return jsonify({'success': False, 'message': 'Invalid QR code format'}), 400
        
        # Check if QR code is recent (within 6 seconds + 2 second buffer)
        current_timestamp = int(datetime.now().timestamp() * 1000)  # Convert to milliseconds
        time_diff = abs(current_timestamp - qr_timestamp)
        
        # Allow 8 seconds total (6 seconds display + 2 seconds buffer)
        if time_diff > 8000:  # 8000 milliseconds = 8 seconds
            return jsonify({'success': False, 'message': 'QR code has expired. Please scan the current QR code.'}), 400
        
        # Get class information 
        conn = sqlite3.connect('classes.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT subject_name, teacher_name, start_time, end_time, room_number
            FROM classes WHERE id = ? AND is_active = 1
        ''', (class_id,))
        
        class_info = cursor.fetchone()
        conn.close()
        
        if not class_info:
            return jsonify({'success': False, 'message': 'Class not found or inactive'}), 404
        
        return jsonify({
            'success': True,
            'message': 'QR code validated successfully',
            'class_info': {
                'id': class_id,
                'subject': class_info[0],
                'teacher': class_info[1],
                'time': f"{class_info[2]} - {class_info[3]}",
                'room': class_info[4],
                'date': class_date
            }
        })
        
    except Exception as e:
        print(f"Error in validate_qr: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

# Classes API Endpoints
@app.route('/api/student/classes/today', methods=['GET'])
def get_student_classes_today():
    """Get all active classes for the logged-in student (removed day restriction)"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Please log in first'}), 401
        
        # Get student ID from session
        conn = sqlite3.connect('authentication.db')
        cursor = conn.cursor()
        cursor.execute('SELECT student_id FROM users WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        
        if not user or not user[0]:
            return jsonify({'success': False, 'message': 'Student ID not found'}), 404
        
        student_id = user[0]
        
        # Get current day of week for display purposes
        from datetime import datetime
        current_day = datetime.now().strftime('%A')
        print(f"DEBUG: Looking for all classes for student {student_id}")
        
        # Get ALL enrolled classes (removed day restriction)
        conn = sqlite3.connect('classes.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.id, c.subject_name, c.teacher_name, c.start_time, c.end_time, c.room_number, c.day_of_week
            FROM classes c
            JOIN student_enrollments se ON c.id = se.class_id
            WHERE se.student_id = ? AND c.is_active = 1 AND se.is_active = 1
            ORDER BY c.day_of_week, c.start_time
        ''', (student_id,))
        
        classes = cursor.fetchall()
        print(f"DEBUG: Found {len(classes)} total classes for student {student_id}")
        
        conn.close()
        
        # Format classes for frontend
        formatted_classes = []
        color_options = ['blue', 'purple', 'pink', 'green', 'orange', 'teal']
        
        for i, cls in enumerate(classes):
            formatted_classes.append({
                'id': cls[0],
                'time': cls[3],  # start_time
                'subject': cls[1],  # subject_name
                'teacher': cls[2],  # teacher_name
                'room': cls[5],  # room_number
                'day': cls[6],  # day_of_week
                'color': color_options[i % len(color_options)]
            })
        
        return jsonify({
            'success': True,
            'day': current_day,
            'classes': formatted_classes,
            'debug_info': f"Found {len(formatted_classes)} total classes (all days)"
        })
        
    except Exception as e:
        print(f"Error in get_student_classes_today: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/student/attendance/summary', methods=['GET'])
def get_student_attendance_summary():
    """Get attendance summary for the logged-in student"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Please log in first'}), 401
        
        # Get student ID from session
        conn = sqlite3.connect('authentication.db')
        cursor = conn.cursor()
        cursor.execute('SELECT student_id, full_name FROM users WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        
        if not user or not user[0]:
            return jsonify({'success': False, 'message': 'Student ID not found'}), 404
        
        student_id = user[0]
        student_name = user[1]
        
        # Get attendance summary from class_attendance table
        conn = sqlite3.connect('attendance.db')
        cursor = conn.cursor()
        
        # Get total classes and attended classes per subject
        cursor.execute('''
            SELECT subject, COUNT(*) as total_classes,
                   SUM(CASE WHEN (student_id = ? OR student_name = ?) THEN 1 ELSE 0 END) as attended_classes
            FROM class_attendance
            GROUP BY subject
        ''', (student_id, student_name))
        
        attendance_data = cursor.fetchall()
        conn.close()
        
        # Format attendance summary
        formatted_attendance = []
        for subject, total, attended in attendance_data:
            formatted_attendance.append({
                'subject': subject,
                'totalClasses': total,
                'attendedClasses': attended
            })
        
        # If no attendance data, create sample data for enrolled subjects
        if not formatted_attendance:
            conn = sqlite3.connect('classes.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT c.subject_name
                FROM classes c
                JOIN student_enrollments se ON c.id = se.class_id
                WHERE se.student_id = ? AND c.is_active = 1 AND se.is_active = 1
            ''', (student_id,))
            
            subjects = cursor.fetchall()
            conn.close()
            
            for subject in subjects:
                formatted_attendance.append({
                    'subject': subject[0],
                    'totalClasses': 20,  # Default value
                    'attendedClasses': 18  # Default value
                })
        
        return jsonify({
            'success': True,
            'student_name': student_name,
            'student_id': student_id,
            'attendance': formatted_attendance
        })
        
    except Exception as e:
        print(f"Error in get_student_attendance_summary: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/student/attendance/status', methods=['GET'])
def get_attendance_status():
    """Check if attendance has been marked for specific subjects today"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Please log in first'}), 401
        
        # Get student ID from session
        conn = sqlite3.connect('authentication.db')
        cursor = conn.cursor()
        cursor.execute('SELECT student_id, full_name FROM users WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        
        if not user or not user[0]:
            return jsonify({'success': False, 'message': 'Student ID not found'}), 404
        
        student_id = user[0]
        student_name = user[1]
        
        # Get today's date
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Check attendance status for each subject today
        conn = sqlite3.connect('attendance.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT subject, COUNT(*) as marked_today
            FROM class_attendance
            WHERE (student_id = ? OR student_name = ?) AND DATE(timestamp) = ?
            GROUP BY subject
        ''', (student_id, student_name, today))
        
        attendance_status = cursor.fetchall()
        print(f"DEBUG: Found attendance records: {attendance_status}")
        print(f"DEBUG: Looking for student_id={student_id}, student_name={student_name}, date={today}")
        
        # Also check what's actually in the database
        cursor.execute('''
            SELECT student_id, student_name, subject, timestamp
            FROM class_attendance
            WHERE DATE(timestamp) = ?
            ORDER BY timestamp DESC
        ''', (today,))
        
        all_records = cursor.fetchall()
        print(f"DEBUG: All records for today: {all_records}")
        
        conn.close()
        
        # Create a dictionary of subject -> attendance status
        status_dict = {}
        for subject, marked_count in attendance_status:
            status_dict[subject] = marked_count > 0
        
        print(f"DEBUG: Final status_dict: {status_dict}")
        
        # Also get all subjects from today's classes to ensure we check all of them
        conn = sqlite3.connect('classes.db')
        cursor = conn.cursor()
        
        # Get today's classes for this student
        cursor.execute('''
            SELECT DISTINCT c.subject_name
            FROM classes c
            JOIN student_enrollments se ON c.id = se.class_id
            WHERE se.student_id = ? AND c.is_active = 1 AND se.is_active = 1
        ''', (student_id,))
        
        enrolled_subjects = cursor.fetchall()
        conn.close()
        
        print(f"DEBUG: Enrolled subjects: {enrolled_subjects}")
        
        # Ensure all enrolled subjects are in status_dict
        for subject_tuple in enrolled_subjects:
            subject = subject_tuple[0]
            if subject not in status_dict:
                status_dict[subject] = False
                print(f"DEBUG: Added missing subject {subject} with status False")
        
        print(f"DEBUG: Final status_dict after adding missing subjects: {status_dict}")
        
        return jsonify({
            'success': True,
            'attendance_status': status_dict,
            'date': today
        })
        
    except Exception as e:
        print(f"Error in get_attendance_status: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/student/attendance/remove', methods=['POST'])
def remove_attendance():
    """Remove attendance for a specific subject today"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Please log in first'}), 401
        
        data = request.get_json()
        if not data or 'subject' not in data:
            return jsonify({'success': False, 'message': 'Subject is required'}), 400
        
        subject = data['subject']
        
        # Get student ID from session
        conn = sqlite3.connect('authentication.db')
        cursor = conn.cursor()
        cursor.execute('SELECT student_id, full_name FROM users WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        
        if not user or not user[0]:
            return jsonify({'success': False, 'message': 'Student ID not found'}), 404
        
        student_id = user[0]
        student_name = user[1]
        
        # Get today's date
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Remove attendance record
        conn = sqlite3.connect('attendance.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM class_attendance
            WHERE (student_id = ? OR student_name = ?) AND subject = ? AND DATE(timestamp) = ?
        ''', (student_id, student_name, subject, today))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            return jsonify({
                'success': True,
                'message': f'Attendance removed for {subject}',
                'subject': subject
            })
        else:
            return jsonify({
                'success': False,
                'message': f'No attendance found for {subject} today'
            })
        
    except Exception as e:
        print(f"Error in remove_attendance: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/teacher/classes/remove', methods=['POST'])
def remove_class():
    """Remove a class (teacher only)"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Please log in first'}), 401
        
        data = request.get_json()
        if not data or 'class_id' not in data:
            return jsonify({'success': False, 'message': 'Class ID is required'}), 400
        
        class_id = data['class_id']
        
        # Remove class from database
        conn = sqlite3.connect('classes.db')
        cursor = conn.cursor()
        
        # First check if class exists and belongs to this teacher
        cursor.execute('''
            SELECT id, teacher_id FROM classes WHERE id = ?
        ''', (class_id,))
        
        class_info = cursor.fetchone()
        if not class_info:
            conn.close()
            return jsonify({'success': False, 'message': 'Class not found'}), 404
        
        # Get teacher info from session
        conn_auth = sqlite3.connect('authentication.db')
        cursor_auth = conn_auth.cursor()
        cursor_auth.execute('SELECT teacher_id, username FROM users WHERE id = ?', (session['user_id'],))
        teacher = cursor_auth.fetchone()
        conn_auth.close()
        
        # Handle the case where teacher_id might be None in the database
        # Use the same logic as in add_class to determine the effective teacher_id
        if teacher:
            effective_teacher_id = teacher[0] if teacher[0] else ('TCH001' if teacher[1] == 'teacher1' else 'TCH002' if teacher[1] == 'teacher2' else 'TCH001')
        else:
            conn.close()
            return jsonify({'success': False, 'message': 'Teacher not found'}), 404
        
        print(f"DEBUG: Remove class - session user_id: {session['user_id']}")
        print(f"DEBUG: Remove class - teacher from session: {teacher}")
        print(f"DEBUG: Remove class - effective_teacher_id: {effective_teacher_id}")
        print(f"DEBUG: Remove class - class_info: {class_info}")
        print(f"DEBUG: Remove class - comparing {effective_teacher_id} with {class_info[1]}")
        
        if effective_teacher_id != class_info[1]:
            conn.close()
            return jsonify({'success': False, 'message': f'You can only remove your own classes. Your ID: {effective_teacher_id}, Class owner: {class_info[1]}'}), 403
        
        # Remove class (this will also remove enrollments due to foreign key constraints)
        cursor.execute('DELETE FROM classes WHERE id = ?', (class_id,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            return jsonify({
                'success': True,
                'message': 'Class removed successfully',
                'class_id': class_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Class not found or already removed'
            })
        
    except Exception as e:
        print(f"Error in remove_class: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/clear-attendance', methods=['POST'])
def clear_attendance_data():
    """Clear all attendance data for testing purposes"""
    try:
        conn = sqlite3.connect('attendance.db')
        cursor = conn.cursor()
        
        # Clear all attendance records
        cursor.execute('DELETE FROM class_attendance')
        cursor.execute('DELETE FROM attendance')
        
        deleted_class = cursor.rowcount
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Cleared all attendance data. Deleted {deleted_class} records.',
            'deleted_records': deleted_class
        })
        
    except Exception as e:
        print(f"Error clearing attendance: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/teacher/classes/add', methods=['POST'])
def add_class():
    """Add a new class (teacher only)"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Please log in first'}), 401
        
        data = request.get_json()
        subject = data.get('subject')
        time_slot = data.get('time_slot')
        room = data.get('room')
        date = data.get('date')
        
        if not all([subject, time_slot, room, date]):
            return jsonify({'success': False, 'message': 'All fields are required'})
        
        # Convert date to day of week
        from datetime import datetime
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            day_of_week = date_obj.strftime('%A')
        except:
            day_of_week = datetime.now().strftime('%A')
        
        # Parse time slot to get start and end times
        if ' - ' in time_slot:
            start_time, end_time = time_slot.split(' - ')
        else:
            start_time = time_slot
            end_time = time_slot
        
        conn = sqlite3.connect('classes.db')
        cursor = conn.cursor()
        
        # Get teacher info from session
        conn_auth = sqlite3.connect('authentication.db')
        cursor_auth = conn_auth.cursor()
        cursor_auth.execute('SELECT teacher_id, full_name, username FROM users WHERE id = ?', (session['user_id'],))
        teacher = cursor_auth.fetchone()
        conn_auth.close()
        
        if teacher:
            # Use consistent teacher_id mapping logic
            teacher_id = teacher[0] if teacher[0] else ('TCH001' if teacher[2] == 'teacher1' else 'TCH002' if teacher[2] == 'teacher2' else 'TCH001')
            teacher_name = teacher[1] if teacher[1] else 'Prof. Eleanor'
        else:
            teacher_id = 'TCH001'
            teacher_name = 'Prof. Eleanor'
        
        print(f"DEBUG: Add class - session user_id: {session['user_id']}")
        print(f"DEBUG: Add class - teacher from session: {teacher}")
        print(f"DEBUG: Add class - using teacher_id: {teacher_id}")
        
        cursor.execute('''
            INSERT INTO classes (subject_name, teacher_id, teacher_name, start_time, end_time, day_of_week, room_number, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        ''', (subject, teacher_id, teacher_name, start_time, end_time, day_of_week, room))
        
        class_id = cursor.lastrowid
        
        # Automatically enroll all students in the new class
        student_ids = ['STU001', 'STU002', 'STU003']  # Get all student IDs
        print(f"DEBUG: Enrolling students {student_ids} in class {class_id}")
        
        for student_id in student_ids:
            try:
                cursor.execute('''
                    INSERT INTO student_enrollments (student_id, class_id, enrollment_date, is_active)
                    VALUES (?, ?, date('now'), 1)
                ''', (student_id, class_id))
                print(f"DEBUG: Enrolled student {student_id} in class {class_id}")
            except sqlite3.IntegrityError:
                print(f"DEBUG: Student {student_id} already enrolled in class {class_id}")
                # Update existing enrollment to active
                cursor.execute('''
                    UPDATE student_enrollments 
                    SET is_active = 1 
                    WHERE student_id = ? AND class_id = ?
                ''', (student_id, class_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Class added successfully and all students enrolled',
            'class_id': class_id,
            'enrolled_students': student_ids
        })
        
    except Exception as e:
        print(f"Error in add_class: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/teacher/classes/add_old', methods=['POST'])
def add_class_old():
    """Add a new class (teacher only) - old version"""
    try:
        if 'user_id' not in session or session.get('user_type') != 'teacher':
            return jsonify({'success': False, 'message': 'Teacher access required'}), 403
        
        data = request.get_json()
        subject_name = data.get('subject_name')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        day_of_week = data.get('day_of_week')
        room_number = data.get('room_number', '')
        
        if not all([subject_name, start_time, end_time, day_of_week]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Get teacher info
        conn = sqlite3.connect('authentication.db')
        cursor = conn.cursor()
        cursor.execute('SELECT teacher_id, full_name FROM users WHERE id = ?', (session['user_id'],))
        teacher = cursor.fetchone()
        conn.close()
        
        if not teacher:
            return jsonify({'success': False, 'message': 'Teacher not found'}), 404
        
        teacher_id = teacher[0]
        teacher_name = teacher[1]
        
        # Add class to database
        conn = sqlite3.connect('classes.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO classes (subject_name, teacher_id, teacher_name, start_time, end_time, day_of_week, room_number)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (subject_name, teacher_id, teacher_name, start_time, end_time, day_of_week, room_number))
        
        class_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Class added successfully',
            'class_id': class_id
        })
        
    except Exception as e:
        print(f"Error in add_class: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/classes', methods=['GET'])
def get_classes_by_date():
    """Get classes for a specific date (used by teacher dashboard)"""
    try:
        date = request.args.get('date')
        if not date:
            return jsonify({'success': False, 'message': 'Date parameter is required'})
        
        conn = sqlite3.connect('classes.db')
        cursor = conn.cursor()
        
        # Convert date to day of week
        from datetime import datetime
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            day_of_week = date_obj.strftime('%A')
        except:
            # If date format is different, try to parse it
            day_of_week = datetime.now().strftime('%A')
        
        cursor.execute('''
            SELECT id, subject_name, teacher_name, start_time, end_time, room_number
            FROM classes 
            WHERE day_of_week = ? AND is_active = 1
            ORDER BY start_time
        ''', (day_of_week,))
        
        classes = []
        for row in cursor.fetchall():
            classes.append({
                'id': row[0],
                'subject': row[1],
                'teacher': row[2],
                'time_slot': f"{row[3]} - {row[4]}",
                'room': row[5],
                'date': date
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'classes': classes,
            'count': len(classes),
            'date': date,
            'day_of_week': day_of_week
        })
        
    except Exception as e:
        print(f"Error fetching classes by date: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch classes'}), 500


if __name__ == "__main__":
    print("="*50)
    print("MINIMAL SERVER WITH AUTHENTICATION")
    print("="*50)
    
    # Initialize all databases
    print("Initializing databases...")
    init_auth_db()
    init_attendance_db()
    init_leave_db('leaves.db')
    init_classes_db()
    init_notes_db()
    
    # Create sample data
    print("Creating sample data...")
    create_sample_users()
    create_sample_leave_requests()
    create_sample_classes()
    
    print("Database: authentication.db, attendance.db, leaves.db, classes.db")
    print("\nSample users created:")
    print("Students: student1, student2, student3 (password: password123)")
    print("Teachers: teacher1, teacher2 (password: teacher123)")
    print("Admin: admin (password: admin123)")
    print("\nStarting minimal Flask server...")
    print("Available routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.endpoint}: {rule.rule} [{', '.join(rule.methods)}]")
    print("="*50)
    
    app.run(debug=True, host='127.0.0.1', port=5000)
