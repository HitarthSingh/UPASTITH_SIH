import cv2
import numpy as np
import dlib
from scipy.spatial import distance as dist
from collections import deque
import time
import threading

class LivenessDetector:
    def __init__(self):
        # Initialize dlib's face detector and facial landmark predictor
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        
        # Eye aspect ratio (EAR) constants
        self.EAR_THRESHOLD = 0.25
        self.EAR_CONSEC_FRAMES = 3
        
        # Head movement constants
        self.HEAD_MOVEMENT_THRESHOLD = 15
        self.MOVEMENT_FRAMES = 10
        
        # Tracking variables
        self.blink_counter = 0
        self.total_blinks = 0
        self.ear_history = deque(maxlen=self.EAR_CONSEC_FRAMES)
        self.head_positions = deque(maxlen=self.MOVEMENT_FRAMES)
        
        # Liveness verification state
        self.liveness_verified = False
        self.verification_start_time = None
        self.max_verification_time = 10  # seconds
        
        # Required actions for liveness
        self.required_blinks = 2
        self.required_head_movement = True
        
    def calculate_ear(self, eye):
        """Calculate Eye Aspect Ratio (EAR)"""
        # Compute euclidean distances between vertical eye landmarks
        A = dist.euclidean(eye[1], eye[5])
        B = dist.euclidean(eye[2], eye[4])
        
        # Compute euclidean distance between horizontal eye landmarks
        C = dist.euclidean(eye[0], eye[3])
        
        # Calculate EAR
        ear = (A + B) / (2.0 * C)
        return ear
    
    def extract_eye_landmarks(self, landmarks):
        """Extract left and right eye landmarks"""
        # Define the indices for left and right eye landmarks
        left_eye_indices = list(range(36, 42))
        right_eye_indices = list(range(42, 48))
        
        left_eye = []
        right_eye = []
        
        for i in left_eye_indices:
            left_eye.append([landmarks.part(i).x, landmarks.part(i).y])
        
        for i in right_eye_indices:
            right_eye.append([landmarks.part(i).x, landmarks.part(i).y])
        
        return np.array(left_eye), np.array(right_eye)
    
    def detect_blink(self, frame):
        """Detect eye blinks in the frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector(gray)
        
        blink_detected = False
        
        for face in faces:
            landmarks = self.predictor(gray, face)
            left_eye, right_eye = self.extract_eye_landmarks(landmarks)
            
            # Calculate EAR for both eyes
            left_ear = self.calculate_ear(left_eye)
            right_ear = self.calculate_ear(right_eye)
            
            # Average EAR for both eyes
            ear = (left_ear + right_ear) / 2.0
            self.ear_history.append(ear)
            
            # Check if EAR is below threshold (eyes closed)
            if ear < self.EAR_THRESHOLD:
                self.blink_counter += 1
            else:
                # If eyes were closed for sufficient frames, count as blink
                if self.blink_counter >= self.EAR_CONSEC_FRAMES:
                    self.total_blinks += 1
                    blink_detected = True
                self.blink_counter = 0
            
            # Draw eye contours for visualization
            cv2.drawContours(frame, [left_eye], -1, (0, 255, 0), 1)
            cv2.drawContours(frame, [right_eye], -1, (0, 255, 0), 1)
            
            # Display EAR and blink count
            cv2.putText(frame, f"EAR: {ear:.2f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Blinks: {self.total_blinks}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return blink_detected, frame
    
    def detect_head_movement(self, frame):
        """Detect head movement by tracking face position"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector(gray)
        
        movement_detected = False
        
        for face in faces:
            # Get face center
            face_center = ((face.left() + face.right()) // 2, 
                          (face.top() + face.bottom()) // 2)
            
            self.head_positions.append(face_center)
            
            # Check for significant movement
            if len(self.head_positions) >= 2:
                current_pos = self.head_positions[-1]
                previous_pos = self.head_positions[-2]
                
                movement = dist.euclidean(current_pos, previous_pos)
                
                if movement > self.HEAD_MOVEMENT_THRESHOLD:
                    movement_detected = True
            
            # Draw face rectangle and center point
            cv2.rectangle(frame, (face.left(), face.top()), 
                         (face.right(), face.bottom()), (255, 0, 0), 2)
            cv2.circle(frame, face_center, 5, (255, 0, 0), -1)
            
            # Display movement status
            if len(self.head_positions) >= 2:
                recent_movement = max([dist.euclidean(self.head_positions[i], self.head_positions[i-1]) 
                                     for i in range(1, len(self.head_positions))])
                cv2.putText(frame, f"Movement: {recent_movement:.1f}", (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        return movement_detected, frame
    
    def check_liveness(self, frame):
        """Main liveness detection function"""
        if self.verification_start_time is None:
            self.verification_start_time = time.time()
        
        # Check if verification time has exceeded limit
        elapsed_time = time.time() - self.verification_start_time
        if elapsed_time > self.max_verification_time:
            return False, frame, "Verification timeout"
        
        # Detect blinks and head movement
        blink_detected, frame = self.detect_blink(frame)
        movement_detected, frame = self.detect_head_movement(frame)
        
        # Check liveness criteria
        blinks_satisfied = self.total_blinks >= self.required_blinks
        movement_satisfied = len(self.head_positions) > 5  # Basic movement check
        
        # Display verification status
        status_y = 120
        cv2.putText(frame, f"Blinks Required: {self.required_blinks} | Current: {self.total_blinks}", 
                   (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        cv2.putText(frame, f"Movement: {'OK' if movement_satisfied else 'NEEDED'}", 
                   (10, status_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        cv2.putText(frame, f"Time: {elapsed_time:.1f}s / {self.max_verification_time}s", 
                   (10, status_y + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Check if liveness is verified
        if blinks_satisfied and movement_satisfied:
            self.liveness_verified = True
            cv2.putText(frame, "LIVENESS VERIFIED!", (10, status_y + 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 3)
            return True, frame, "Liveness verified successfully"
        
        # Display instructions
        instructions = []
        if not blinks_satisfied:
            instructions.append(f"Please blink {self.required_blinks - self.total_blinks} more times")
        if not movement_satisfied:
            instructions.append("Please move your head slightly")
        
        instruction_text = " | ".join(instructions)
        cv2.putText(frame, instruction_text, (10, frame.shape[0] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        return False, frame, instruction_text
    
    def reset_verification(self):
        """Reset liveness verification state"""
        self.blink_counter = 0
        self.total_blinks = 0
        self.ear_history.clear()
        self.head_positions.clear()
        self.liveness_verified = False
        self.verification_start_time = None
    
    def is_model_available(self):
        """Check if the required dlib model file is available"""
        try:
            # Try to create a predictor to check if model file exists
            test_predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
            return True
        except:
            return False

class LivenessWebcamDetector:
    """Real-time liveness detection using webcam"""
    
    def __init__(self):
        self.detector = LivenessDetector()
        self.cap = None
        self.is_running = False
        
    def start_detection(self, callback=None):
        """Start real-time liveness detection"""
        if not self.detector.is_model_available():
            return False, "Dlib model file not found. Please download shape_predictor_68_face_landmarks.dat"
        
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            # Try different camera indices
            for i in range(1, 4):
                self.cap = cv2.VideoCapture(i)
                if self.cap.isOpened():
                    break
            else:
                return False, "Could not open webcam. Please check camera permissions and ensure no other application is using the camera."
        
        # Set camera properties for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        self.is_running = True
        self.detector.reset_verification()
        
        # Store the last valid frame for capture
        self.last_valid_frame = None
        
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                print("Warning: Could not read frame from camera")
                continue
            
            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            self.last_valid_frame = frame.copy()
            
            # Check liveness
            liveness_verified, processed_frame, message = self.detector.check_liveness(frame)
            
            # Display the frame
            cv2.imshow('Liveness Detection', processed_frame)
            
            # Call callback if provided
            if callback:
                callback(liveness_verified, processed_frame, message)
            
            # Break on 'q' key or if liveness is verified
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or liveness_verified:
                break
        
        result = liveness_verified, "Liveness verification completed" if liveness_verified else "Verification failed"
        
        # Don't close camera immediately if liveness was verified (for frame capture)
        if not liveness_verified:
            self.stop_detection()
        
        return result
    
    def stop_detection(self):
        """Stop liveness detection"""
        self.is_running = False
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
    
    def capture_verified_frame(self):
        """Capture a frame after liveness verification"""
        if self.detector.liveness_verified:
            # First try to get current frame from camera
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    return cv2.flip(frame, 1)
            
            # Fallback to last valid frame if camera read fails
            if hasattr(self, 'last_valid_frame') and self.last_valid_frame is not None:
                return self.last_valid_frame.copy()
        
        return None
    
    def get_current_frame(self):
        """Get current frame from webcam"""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None:
                return cv2.flip(frame, 1)
        return None
