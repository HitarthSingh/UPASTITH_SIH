import cv2
import sys
import os
from enhanced_face_utils import EnhancedFaceRecognitionSystem

def test_liveness_detection():
    """Test the liveness detection system"""
    print("🧪 Testing Liveness Detection System")
    print("=" * 50)
    
    # Initialize the enhanced face recognition system
    try:
        face_system = EnhancedFaceRecognitionSystem()
        print("✅ Enhanced Face Recognition System initialized")
    except Exception as e:
        print(f"❌ Error initializing system: {e}")
        return False
    
    # Check if liveness model is available
    if not face_system.check_liveness_model():
        print("❌ Liveness detection model not available")
        print("Please run: python setup_liveness.py")
        return False
    
    print("✅ Liveness detection model is available")
    
    while True:
        print("\n" + "=" * 50)
        print("Liveness Detection Test Menu:")
        print("1. Test Face Registration with Liveness")
        print("2. Test Face Recognition with Liveness")
        print("3. Test Legacy Face Recognition (no liveness)")
        print("4. View Attendance Records")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            test_registration(face_system)
        elif choice == "2":
            test_recognition(face_system)
        elif choice == "3":
            test_legacy_recognition(face_system)
        elif choice == "4":
            view_attendance_records(face_system)
        elif choice == "5":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

def test_registration(face_system):
    """Test face registration with liveness verification"""
    print("\n🔐 Testing Face Registration with Liveness Verification")
    print("-" * 50)
    
    name = input("Enter name for registration: ").strip()
    if not name:
        print("❌ Name cannot be empty")
        return
    
    email = input("Enter email (optional): ").strip() or None
    
    print(f"\n📸 Starting registration for {name}")
    print("Instructions:")
    print("- Look directly at the camera")
    print("- Blink your eyes naturally (at least 2 times)")
    print("- Move your head slightly left/right or up/down")
    print("- Press 'q' to cancel if needed")
    print("\nPress Enter when ready...")
    input()
    
    result = face_system.register_face_with_liveness(name, email)
    
    if result["success"]:
        print(f"✅ {result['message']}")
        if result.get("liveness_verified"):
            print("🔒 Liveness verification: PASSED")
        else:
            print("⚠️ Liveness verification: NOT PERFORMED")
    else:
        print(f"❌ Registration failed: {result['message']}")

def test_recognition(face_system):
    """Test face recognition with liveness verification"""
    print("\n🔍 Testing Face Recognition with Liveness Verification")
    print("-" * 50)
    
    print("Instructions:")
    print("- Look directly at the camera")
    print("- Blink your eyes naturally (at least 2 times)")
    print("- Move your head slightly left/right or up/down")
    print("- Press 'q' to cancel if needed")
    print("\nPress Enter when ready...")
    input()
    
    result = face_system.recognize_face_with_liveness()
    
    if result["success"]:
        print(f"✅ Face recognized: {result['name']}")
        print(f"🎯 Confidence: {result['confidence']:.2%}")
        if result.get("liveness_verified"):
            print("🔒 Liveness verification: PASSED")
            
            # Mark attendance
            attendance_result = face_system.mark_attendance(
                result['name'], 
                liveness_verified=True,
                verification_method=result.get('verification_method', 'webcam_liveness'),
                confidence=result['confidence']
            )
            
            if attendance_result["success"]:
                print(f"📝 {attendance_result['message']}")
            else:
                print(f"⚠️ Attendance: {attendance_result['message']}")
        else:
            print("⚠️ Liveness verification: NOT PERFORMED")
    else:
        print(f"❌ Recognition failed: {result['message']}")

def test_legacy_recognition(face_system):
    """Test legacy face recognition without liveness"""
    print("\n⚠️ Testing Legacy Face Recognition (NO LIVENESS VERIFICATION)")
    print("-" * 50)
    print("This method is NOT SECURE and can be spoofed with photos!")
    
    confirm = input("Are you sure you want to continue? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Test cancelled.")
        return
    
    # For demo purposes, we'll simulate with a webcam capture
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open webcam")
        return
    
    print("Press SPACE to capture image, or 'q' to quit")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.flip(frame, 1)
        cv2.putText(frame, "Press SPACE to capture (Legacy Mode - NOT SECURE)", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow('Legacy Recognition', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):
            # Convert frame to base64 for legacy method
            _, buffer = cv2.imencode('.jpg', frame)
            import base64
            image_data = base64.b64encode(buffer).decode('utf-8')
            
            result = face_system.recognize_face(f"data:image/jpeg;base64,{image_data}")
            
            if result["success"]:
                print(f"✅ Face recognized: {result['name']}")
                print(f"🎯 Confidence: {result['confidence']:.2%}")
                print("⚠️ WARNING: NO LIVENESS VERIFICATION - INSECURE!")
                
                # Mark attendance without liveness
                attendance_result = face_system.mark_attendance(
                    result['name'], 
                    liveness_verified=False,
                    verification_method='static_image',
                    confidence=result['confidence']
                )
                
                if attendance_result["success"]:
                    print(f"📝 {attendance_result['message']}")
                else:
                    print(f"⚠️ Attendance: {attendance_result['message']}")
            else:
                print(f"❌ Recognition failed: {result['message']}")
            break
        elif key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

def view_attendance_records(face_system):
    """View attendance records"""
    print("\n📊 Attendance Records")
    print("-" * 50)
    
    result = face_system.get_attendance_records()
    
    if result["success"]:
        records = result["records"]
        if not records:
            print("No attendance records found.")
            return
        
        print(f"{'Name':<15} {'Timestamp':<20} {'Liveness':<10} {'Method':<15} {'Confidence':<10}")
        print("-" * 80)
        
        for record in records:
            liveness_status = "✅ YES" if record['liveness_verified'] else "❌ NO"
            confidence = f"{record['confidence']:.2%}" if record['confidence'] else "N/A"
            
            print(f"{record['name']:<15} {record['timestamp']:<20} {liveness_status:<10} "
                  f"{record['verification_method']:<15} {confidence:<10}")
    else:
        print(f"❌ Error fetching records: {result['message']}")

if __name__ == "__main__":
    test_liveness_detection()
