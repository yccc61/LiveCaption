#!/usr/bin/env python3
"""
Setup script for LiveCaption
"""

import subprocess
import sys
import os
from pathlib import Path

def install_requirements():
    """Install required packages"""
    print("Installing required packages...")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ])
        print("Requirements installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install requirements: {e}")
        return False

def check_system_requirements():
    """Check system requirements"""
    print("Checking system requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("ERROR: Python 3.8 or higher is required")
        return False
    
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check for system audio capabilities
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        print(f"✓ Found {len(devices)} audio devices")
    except ImportError:
        print("⚠ sounddevice not yet installed (will be installed with requirements)")
    except Exception as e:
        print(f"⚠ Audio system check failed: {e}")
    
    return True

def setup_permissions():
    """Setup necessary permissions (Linux/Mac)"""
    if os.name != 'posix':
        return True
    
    print("Setting up permissions...")
    
    # Make main script executable
    main_script = Path(__file__).parent / "live_caption.py"
    try:
        os.chmod(main_script, 0o755)
        print("✓ Made live_caption.py executable")
    except Exception as e:
        print(f"⚠ Could not make script executable: {e}")
    
    return True

def main():
    """Main setup function"""
    print("=== LiveCaption Setup ===")
    print()
    
    if not check_system_requirements():
        print("System requirements check failed!")
        return 1
    
    print()
    
    if not install_requirements():
        print("Failed to install requirements!")
        return 1
    
    print()
    
    if not setup_permissions():
        print("Failed to setup permissions!")
        return 1
    
    print()
    print("=== Setup Complete ===")
    print()
    print("To run LiveCaption:")
    print("  python live_caption.py")
    print()
    print("To test the UI:")
    print("  python live_caption.py --test-ui")
    print()
    print("To list audio devices:")
    print("  python live_caption.py --list-devices")
    print()
    print("For help:")
    print("  python live_caption.py --help")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
