import cv2
import face_recognition
import numpy as np
import os
import pickle
import sqlite3
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image
from liveness_detection import LivenessDetector, LivenessWebcamDetector
import threading
import time

class EnhancedFaceRecognitionSystem:
    def __init__(self, encodings_path="face_encodings", db_path="attendance.db"):
        self.encodings_path = encodings_path
        self.db_path = db_path
        self.known_face_encodings = []
        self.known_face_names = []
        
        # Initialize liveness detector
        self.liveness_detector = LivenessDetector()
        self.webcam_detector = LivenessWebcamDetector()
        
        # Create directories if they don't exist
        os.makedirs(encodings_path, exist_ok=True)
        
        # Initialize database
        self.init_database()
        
        # Load existing face encodings
        self.load_face_encodings()
    
    def init_database(self):
        """Initialize SQLite database for attendance records"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create attendance table with liveness verification info
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'present',
                liveness_verified BOOLEAN DEFAULT 0,
                verification_method TEXT DEFAULT 'face_recognition',
                confidence REAL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_face_encoding(self, name, encoding):
        """Save face encoding to file"""
        encoding_file = os.path.join(self.encodings_path, f"{name}.pkl")
        with open(encoding_file, 'wb') as f:
            pickle.dump(encoding, f)
    
    def load_face_encodings(self):
        """Load all face encodings from files"""
        self.known_face_encodings = []
        self.known_face_names = []
        
        if not os.path.exists(self.encodings_path):
            return
        
        for filename in os.listdir(self.encodings_path):
            if filename.endswith('.pkl'):
                name = filename[:-4]  # Remove .pkl extension
                encoding_file = os.path.join(self.encodings_path, filename)
                
                try:
                    with open(encoding_file, 'rb') as f:
                        encoding = pickle.load(f)
                        self.known_face_encodings.append(encoding)
                        self.known_face_names.append(name)
                except Exception as e:
                    print(f"Error loading encoding for {name}: {e}")
    
    def register_face_with_liveness(self, name, email=None, use_webcam=True):
        """Register a new face with liveness verification"""
        try:
            if not self.liveness_detector.is_model_available():
                return {
                    "success": False, 
                    "message": "Liveness detection model not available. Please download shape_predictor_68_face_landmarks.dat"
                }
            
            if use_webcam:
                # Use webcam for registration with liveness verification
                print(f"Starting liveness verification for {name}...")
                print("Please look at the camera and follow the instructions:")
                print("1. Blink your eyes naturally (at least 2 times)")
                print("2. Move your head slightly")
                print("3. Press 'q' to quit if needed")
                
                liveness_verified, message = self.webcam_detector.start_detection()
                
                if not liveness_verified:
                    return {"success": False, "message": f"Liveness verification failed: {message}"}
                
                # Capture verified frame
                verified_frame = self.webcam_detector.capture_verified_frame()
                if verified_frame is None:
                    return {"success": False, "message": "Could not capture verified frame"}
                
                # Convert frame to RGB for face_recognition
                rgb_frame = cv2.cvtColor(verified_frame, cv2.COLOR_BGR2RGB)
                
                # Find face encodings
                face_encodings = face_recognition.face_encodings(rgb_frame)
                
                if len(face_encodings) == 0:
                    return {"success": False, "message": "No face detected in verified frame"}
                
                if len(face_encodings) > 1:
                    return {"success": False, "message": "Multiple faces detected. Please ensure only one person is in frame"}
                
                # Get the face encoding
                face_encoding = face_encodings[0]
                
                # Save the encoding
                self.save_face_encoding(name, face_encoding)
                
                # Add to known faces
                self.known_face_encodings.append(face_encoding)
                self.known_face_names.append(name)
                
                # Add user to database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                try:
                    cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
                    conn.commit()
                except sqlite3.IntegrityError:
                    # User already exists, update email if provided
                    if email:
                        cursor.execute("UPDATE users SET email = ? WHERE name = ?", (email, name))
                        conn.commit()
                
                conn.close()
                
                return {
                    "success": True, 
                    "message": f"Face registered successfully for {name} with liveness verification",
                    "liveness_verified": True
                }
            
        except Exception as e:
            return {"success": False, "message": f"Error registering face: {str(e)}"}
    
    def register_face(self, name, image_data, email=None):
        """Register a new face from image data (legacy method without liveness)"""
        try:
            # Decode base64 image
            if isinstance(image_data, str) and image_data.startswith('data:image'):
                # Remove data URL prefix
                image_data = image_data.split(',')[1]
            
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))
            
            # Convert PIL image to numpy array
            image_array = np.array(image)
            
            # Convert RGB to BGR for OpenCV
            if len(image_array.shape) == 3:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            
            # Find face encodings
            face_encodings = face_recognition.face_encodings(image_array)
            
            if len(face_encodings) == 0:
                return {"success": False, "message": "No face detected in the image"}
            
            if len(face_encodings) > 1:
                return {"success": False, "message": "Multiple faces detected. Please use an image with only one face"}
            
            # Get the face encoding
            face_encoding = face_encodings[0]
            
            # Save the encoding
            self.save_face_encoding(name, face_encoding)
            
            # Add to known faces
            self.known_face_encodings.append(face_encoding)
            self.known_face_names.append(name)
            
            # Add user to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
                conn.commit()
            except sqlite3.IntegrityError:
                # User already exists, update email if provided
                if email:
                    cursor.execute("UPDATE users SET email = ? WHERE name = ?", (email, name))
                    conn.commit()
            
            conn.close()
            
            return {
                "success": True, 
                "message": f"Face registered successfully for {name} (WARNING: No liveness verification)",
                "liveness_verified": False
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error registering face: {str(e)}"}
    
    def recognize_face_with_liveness(self, use_webcam=True, timeout=15):
        """Recognize face with liveness verification"""
        try:
            if not self.liveness_detector.is_model_available():
                return {
                    "success": False, 
                    "message": "Liveness detection model not available"
                }
            
            if use_webcam:
                print("Starting face recognition with liveness verification...")
                print("Please look at the camera and follow the instructions:")
                print("1. Blink your eyes naturally (at least 2 times)")
                print("2. Move your head slightly")
                print("3. Press 'q' to quit if needed")
                
                # Start liveness detection
                liveness_verified, message = self.webcam_detector.start_detection()
                
                if not liveness_verified:
                    return {"success": False, "message": f"Liveness verification failed: {message}"}
                
                # Capture verified frame
                verified_frame = self.webcam_detector.capture_verified_frame()
                if verified_frame is None:
                    return {"success": False, "message": "Could not capture verified frame"}
                
                # Convert frame to RGB for face_recognition
                rgb_frame = cv2.cvtColor(verified_frame, cv2.COLOR_BGR2RGB)
                
                # Find face encodings
                face_encodings = face_recognition.face_encodings(rgb_frame)
                
                if len(face_encodings) == 0:
                    return {"success": False, "message": "No face detected in verified frame"}
                
                # Compare with known faces
                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.5)
                    face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    
                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        best_distance = face_distances[best_match_index]
                        
                        if matches[best_match_index]:
                            name = self.known_face_names[best_match_index]
                            confidence = 1 - face_distances[best_match_index]
                            
                            return {
                                "success": True,
                                "name": name,
                                "confidence": float(confidence),
                                "liveness_verified": True,
                                "verification_method": "webcam_liveness"
                            }
                
                return {"success": False, "message": "Face not recognized"}
            
        except Exception as e:
            return {"success": False, "message": f"Error recognizing face: {str(e)}"}
    
    def recognize_face(self, image_data):
        """Recognize face from image data (legacy method without liveness)"""
        try:
            # Decode base64 image
            if isinstance(image_data, str) and image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))
            image_array = np.array(image)
            
            if len(image_array.shape) == 3:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            
            # Find face encodings
            face_encodings = face_recognition.face_encodings(image_array)
            
            if len(face_encodings) == 0:
                return {"success": False, "message": "No face detected"}
            
            # Compare with known faces
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.5)
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                
                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    best_distance = face_distances[best_match_index]
                    
                    if matches[best_match_index]:
                        name = self.known_face_names[best_match_index]
                        confidence = 1 - face_distances[best_match_index]
                        
                        return {
                            "success": True,
                            "name": name,
                            "confidence": float(confidence),
                            "liveness_verified": False,
                            "verification_method": "static_image"
                        }
            
            return {"success": False, "message": "Face not recognized"}
            
        except Exception as e:
            return {"success": False, "message": f"Error recognizing face: {str(e)}"}
    
    def mark_attendance(self, name, liveness_verified=False, verification_method="face_recognition", confidence=0.0):
        """Mark attendance for a person with liveness verification info"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if attendance already marked today
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT COUNT(*) FROM attendance 
                WHERE name = ? AND DATE(timestamp) = ?
            """, (name, today))
            
            count = cursor.fetchone()[0]
            
            if count > 0:
                conn.close()
                return {"success": False, "message": f"Attendance already marked for {name} today"}
            
            # Mark attendance with liveness info
            cursor.execute("""
                INSERT INTO attendance (name, liveness_verified, verification_method, confidence) 
                VALUES (?, ?, ?, ?)
            """, (name, liveness_verified, verification_method, confidence))
            conn.commit()
            conn.close()
            
            verification_status = "with liveness verification" if liveness_verified else "WITHOUT liveness verification"
            return {
                "success": True, 
                "message": f"Attendance marked for {name} {verification_status}",
                "liveness_verified": liveness_verified
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error marking attendance: {str(e)}"}
    
    def get_attendance_records(self, date=None):
        """Get attendance records for a specific date or all records"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if date:
                cursor.execute("""
                    SELECT name, timestamp, status, liveness_verified, verification_method, confidence 
                    FROM attendance 
                    WHERE DATE(timestamp) = ? 
                    ORDER BY timestamp DESC
                """, (date,))
            else:
                cursor.execute("""
                    SELECT name, timestamp, status, liveness_verified, verification_method, confidence 
                    FROM attendance 
                    ORDER BY timestamp DESC
                """)
            
            records = cursor.fetchall()
            conn.close()
            
            return {
                "success": True,
                "records": [{
                    "name": r[0], 
                    "timestamp": r[1], 
                    "status": r[2],
                    "liveness_verified": bool(r[3]),
                    "verification_method": r[4],
                    "confidence": r[5]
                } for r in records]
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error fetching records: {str(e)}"}
    
    def get_registered_users(self):
        """Get list of all registered users"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name, email, created_at FROM users ORDER BY name")
            users = cursor.fetchall()
            conn.close()
            
            return {
                "success": True,
                "users": [{"name": u[0], "email": u[1], "created_at": u[2]} for u in users]
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error fetching users: {str(e)}"}
    
    def check_liveness_model(self):
        """Check if liveness detection model is available"""
        return self.liveness_detector.is_model_available()
