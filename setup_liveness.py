import os
import urllib.request
import bz2
import shutil
from pathlib import Path

def download_dlib_model():
    """Download the dlib facial landmark predictor model"""
    model_url = "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
    model_file = "shape_predictor_68_face_landmarks.dat"
    compressed_file = "shape_predictor_68_face_landmarks.dat.bz2"
    
    # Check if model already exists
    if os.path.exists(model_file):
        print(f"✅ {model_file} already exists")
        return True
    
    try:
        print("📥 Downloading dlib facial landmark predictor model...")
        print("This may take a few minutes depending on your internet connection...")
        
        # Download the compressed file
        urllib.request.urlretrieve(model_url, compressed_file)
        print("✅ Download completed")
        
        # Extract the compressed file
        print("📦 Extracting model file...")
        with bz2.BZ2File(compressed_file, 'rb') as f_in:
            with open(model_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove the compressed file
        os.remove(compressed_file)
        
        print(f"✅ Model extracted successfully: {model_file}")
        print(f"📊 Model file size: {os.path.getsize(model_file) / (1024*1024):.1f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        # Clean up any partial files
        for file in [compressed_file, model_file]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass
        return False

def install_dependencies():
    """Install required Python packages"""
    import subprocess
    import sys
    
    packages = ["dlib", "scipy"]
    
    for package in packages:
        try:
            print(f"📦 Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error installing {package}: {e}")
            return False
    
    return True

def verify_installation():
    """Verify that all components are working"""
    try:
        print("🔍 Verifying installation...")
        
        # Test dlib import
        import dlib
        print("✅ dlib imported successfully")
        
        # Test scipy import
        import scipy
        print("✅ scipy imported successfully")
        
        # Test model file
        if os.path.exists("shape_predictor_68_face_landmarks.dat"):
            predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
            print("✅ Dlib model loaded successfully")
        else:
            print("❌ Model file not found")
            return False
        
        # Test liveness detection import
        from liveness_detection import LivenessDetector
        detector = LivenessDetector()
        if detector.is_model_available():
            print("✅ Liveness detection system ready")
        else:
            print("❌ Liveness detection system not ready")
            return False
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Liveness Detection System")
    print("=" * 50)
    
    # Step 1: Install dependencies
    print("\n📦 Step 1: Installing dependencies...")
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        return False
    
    # Step 2: Download model
    print("\n📥 Step 2: Downloading dlib model...")
    if not download_dlib_model():
        print("❌ Failed to download model")
        return False
    
    # Step 3: Verify installation
    print("\n🔍 Step 3: Verifying installation...")
    if not verify_installation():
        print("❌ Installation verification failed")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Liveness Detection System setup completed successfully!")
    print("\nYou can now use the enhanced face recognition system with:")
    print("- Eye blink detection")
    print("- Head movement detection")
    print("- Real-time liveness verification")
    print("\nTo test the system, run:")
    print("python test_liveness.py")
    
    return True

if __name__ == "__main__":
    main()
