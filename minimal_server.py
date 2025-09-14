from flask import Flask, request, jsonify, render_template, session, redirect, send_from_directory
from flask_cors import CORS
import os
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import random
import secrets
from datetime import datetime, timedelta
from face_utils import FaceRecognitionSystem
from db_leaves import init_leave_db
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'
CORS(app)

# Initialize face recognition system
face_system = FaceRecognitionSystem()

@app.route("/")
def landing_page():
    return render_template("landingpagefinal1.html")

@app.route("/teacherloginpage")
def teacherlogin():
    return render_template("teacherloginpage.html")


@app.route("/studentdashboard")
def student_dashboard():
    return render_template("studentdashboard.html")

@app.route("/demoleave")
def demo_leave():
    return render_template("demoleave.html")

@app.route("/timetable")
def timetable():
    return render_template("timetable.html")

@app.route("/repository")
def repository():
    return render_template("repository.html")

@app.route("/studentresult")
def student_result():
    return render_template("studentresult.html")
@app.route("/aboutus")
def aboutus():
    return render_template("aboutus.html")

@app.route("/suggestionbox")
def suggestion_box():
    return render_template("suggestionbox.html")

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
    """Create sample classes and student enrollments"""
    try:
        conn = sqlite3.connect('classes.db')
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute('DELETE FROM student_enrollments')
        cursor.execute('DELETE FROM classes')
        
        # Get current day for testing
        from datetime import datetime
        current_day = datetime.now().strftime('%A')
        print(f"Creating classes for current day: {current_day}")
        
        # Insert sample classes for all days of the week
        sample_classes = [
            ('Data Structures', 'Prof. Eleanor', '09:00', '10:00', 'Monday', 'CS-101'),
            ('Operating Systems', 'Prof. Eleanor', '10:15', '11:15', 'Monday', 'CS-102'),
            ('Computer Networks', 'Dr. Smith', '11:30', '12:30', 'Monday', 'CS-103'),
            
            ('Database Systems', 'Prof. Eleanor', '09:00', '10:00', 'Tuesday', 'CS-201'),
            ('Software Engineering', 'Dr. Smith', '10:15', '11:15', 'Tuesday', 'CS-202'),
            ('Web Development', 'Prof. Eleanor', '11:30', '12:30', 'Tuesday', 'CS-203'),
            
            ('Machine Learning', 'Dr. Smith', '09:00', '10:00', 'Wednesday', 'CS-301'),
            ('Artificial Intelligence', 'Prof. Eleanor', '10:15', '11:15', 'Wednesday', 'CS-302'),
            ('Cloud Computing', 'Dr. Smith', '11:30', '12:30', 'Wednesday', 'CS-303'),
            
            ('Mobile Development', 'Prof. Eleanor', '09:00', '10:00', 'Thursday', 'CS-401'),
            ('Cybersecurity', 'Dr. Smith', '10:15', '11:15', 'Thursday', 'CS-402'),
            ('DevOps', 'Prof. Eleanor', '11:30', '12:30', 'Thursday', 'CS-403'),
            
            ('Project Management', 'Dr. Smith', '09:00', '10:00', 'Friday', 'CS-501'),
            ('System Design', 'Prof. Eleanor', '10:15', '11:15', 'Friday', 'CS-502'),
            ('Research Methods', 'Dr. Smith', '11:30', '12:30', 'Friday', 'CS-503'),
            
            ('Data Structures Lab', 'Prof. Eleanor', '09:00', '11:00', 'Saturday', 'CS-Lab1'),
            ('Operating Systems Lab', 'Dr. Smith', '11:15', '13:15', 'Saturday', 'CS-Lab2'),
            ('Project Work', 'Prof. Eleanor', '14:00', '16:00', 'Saturday', 'CS-Lab3'),
            
            # Add classes for Sunday as well
            ('Special Workshop', 'Prof. Eleanor', '10:00', '12:00', 'Sunday', 'CS-Workshop'),
            ('Research Seminar', 'Dr. Smith', '14:00', '16:00', 'Sunday', 'CS-Seminar'),
        ]
        
        for class_data in sample_classes:
            # Map teacher names to teacher IDs
            teacher_id = 'TCH001' if class_data[1] == 'Prof. Eleanor' else 'TCH002'
            cursor.execute('''
                INSERT INTO classes (subject_name, teacher_name, start_time, end_time, day_of_week, room_number, teacher_id, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ''', class_data + (teacher_id,))
        
        # Get all class IDs
        cursor.execute('SELECT id FROM classes')
        class_ids = [row[0] for row in cursor.fetchall()]
        
        # Enroll all students in all classes
        student_ids = ['STU001', 'STU002', 'STU003']
        for student_id in student_ids:
            for class_id in class_ids:
                cursor.execute('''
                    INSERT INTO student_enrollments (student_id, class_id, enrollment_date, is_active)
                    VALUES (?, ?, date('now'), 1)
                ''', (student_id, class_id))
        
        conn.commit()
        
        # Verify data was inserted
        cursor.execute('SELECT COUNT(*) FROM classes')
        class_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM student_enrollments')
        enrollment_count = cursor.fetchone()[0]
        
        conn.close()
        print(f"Sample classes and enrollments created successfully")
        print(f"Total classes: {class_count}, Total enrollments: {enrollment_count}")
        
    except Exception as e:
        print(f"Error creating sample classes: {e}")

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
            attendance_message = f"✅ Face recognized: {name}! Attendance marked successfully."
            return jsonify({
                "success": True,
                "name": name,
                "confidence": confidence,
                "attendance_marked": True,
                "attendance_message": attendance_message,
                "message": attendance_message,
                "received_data": bool(data)
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
                "received_data": bool(data)
            })
        
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
    """Handle logout"""
    if 'user_id' in session:
        # Remove session from database
        conn = sqlite3.connect('authentication.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sessions WHERE user_id = ?', (session['user_id'],))
        conn.commit()
        conn.close()
    
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

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
        
        # Mark attendance in the system
        attendance_result = face_system.mark_attendance(recognized_name)
        
        if not attendance_result['success']:
            return jsonify({
                'success': False,
                'message': attendance_result['message']
            })
        
        # Also record in class-specific attendance if needed
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
            
            # Insert class-specific attendance record
            cursor.execute('''
                INSERT INTO class_attendance (student_name, student_id, subject, recognition_confidence)
                VALUES (?, ?, ?, ?)
            ''', (recognized_name, student_id, subject, confidence))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error recording class attendance: {e}")
            # Don't fail the main operation if class attendance fails
        
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

# Classes API Endpoints
@app.route('/api/student/classes/today', methods=['GET'])
def get_student_classes_today():
    """Get today's classes for the logged-in student"""
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
        
        # Get current day of week
        from datetime import datetime
        current_day = datetime.now().strftime('%A')
        
        # Get enrolled classes for today
        conn = sqlite3.connect('classes.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.id, c.subject_name, c.teacher_name, c.start_time, c.end_time, c.room_number
            FROM classes c
            JOIN student_enrollments se ON c.id = se.class_id
            WHERE se.student_id = ? AND c.day_of_week = ? AND c.is_active = 1 AND se.is_active = 1
            ORDER BY c.start_time
        ''', (student_id, current_day))
        
        classes = cursor.fetchall()
        
        # Debug: Check if no classes found, try to get any classes for this student
        if not classes:
            print(f"No classes found for {student_id} on {current_day}")
            cursor.execute('''
                SELECT c.day_of_week, COUNT(*) 
                FROM classes c
                JOIN student_enrollments se ON c.id = se.class_id
                WHERE se.student_id = ? AND c.is_active = 1 AND se.is_active = 1
                GROUP BY c.day_of_week
            ''', (student_id,))
            debug_classes = cursor.fetchall()
            print(f"Classes by day for student {student_id}: {debug_classes}")
            
            # If it's weekend, show Saturday classes as fallback
            if current_day in ['Saturday', 'Sunday']:
                cursor.execute('''
                    SELECT c.id, c.subject_name, c.teacher_name, c.start_time, c.end_time, c.room_number
                    FROM classes c
                    JOIN student_enrollments se ON c.id = se.class_id
                    WHERE se.student_id = ? AND c.day_of_week = 'Saturday' AND c.is_active = 1 AND se.is_active = 1
                    ORDER BY c.start_time
                ''', (student_id,))
                classes = cursor.fetchall()
                if classes:
                    current_day = 'Saturday'
        
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
                'color': color_options[i % len(color_options)]
            })
        
        return jsonify({
            'success': True,
            'day': current_day,
            'classes': formatted_classes,
            'debug_info': f"Found {len(formatted_classes)} classes for {current_day}"
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
                   SUM(CASE WHEN student_id = ? THEN 1 ELSE 0 END) as attended_classes
            FROM class_attendance
            GROUP BY subject
        ''', (student_id,))
        
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
        
        cursor.execute('''
            INSERT INTO classes (subject_name, teacher_name, start_time, end_time, day_of_week, room_number, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (subject, 'Prof. Eleanor', start_time, end_time, day_of_week, room))
        
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
