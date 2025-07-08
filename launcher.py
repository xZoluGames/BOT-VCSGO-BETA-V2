#!/usr/bin/env python3
"""
CS:GO Arbitrage Bot GUI Launcher
Launches the new modern GUI with automatic environment detection and optimization
"""

import sys
import os
import subprocess
import platform

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 7):
        print("❌ Error: Python 3.7 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'customtkinter',
        'requests',
        'orjson'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Install them with: pip install customtkinter requests orjson")
        return False
    
    return True

def detect_environment():
    """Detect if running in WSL or native environment"""
    system = platform.system()
    
    if system == "Linux":
        # Check if running in WSL
        try:
            with open('/proc/version', 'r') as f:
                version_info = f.read().lower()
                if 'microsoft' in version_info or 'wsl' in version_info:
                    return "WSL"
        except:
            pass
        return "Linux"
    elif system == "Windows":
        return "Windows"
    elif system == "Darwin":
        return "macOS"
    else:
        return "Unknown"

def setup_wsl_display():
    """Setup display for WSL environment"""
    try:
        # Try to set DISPLAY environment variable
        if not os.environ.get('DISPLAY'):
            # Common WSL display setups
            possible_displays = [
                ':0.0',
                'localhost:10.0',
                'host.docker.internal:0.0'
            ]
            
            for display in possible_displays:
                os.environ['DISPLAY'] = display
                print(f"🔧 Set DISPLAY to {display}")
                break
        
        print(f"📺 Using DISPLAY: {os.environ.get('DISPLAY', 'Not set')}")
        
    except Exception as e:
        print(f"⚠️ Warning: Could not setup WSL display: {e}")

def optimize_performance():
    """Apply performance optimizations"""
    try:
        # Set threading optimizations
        os.environ['PYTHONUNBUFFERED'] = '1'
        
        # Disable some CTk animations for better performance in WSL
        os.environ['CTK_DISABLE_ANIMATIONS'] = '0'  # Keep animations for now
        
    except Exception as e:
        print(f"⚠️ Warning: Could not apply optimizations: {e}")

def main():
    """Main launcher function"""
    print("🚀 CS:GO Arbitrage Bot GUI Launcher")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Detect environment
    env = detect_environment()
    print(f"🖥️ Environment: {env}")
    
    # Apply environment-specific optimizations
    if env == "WSL":
        print("🐧 WSL detected - applying optimizations...")
        setup_wsl_display()
    
    optimize_performance()
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    gui_path = os.path.join(script_dir, 'gui', 'main.py')
    
    # Check if GUI exists
    if not os.path.exists(gui_path):
        print(f"❌ Error: GUI not found at {gui_path}")
        return 1
    
    print(f"📁 GUI path: {gui_path}")
    print("🎯 Starting GUI application...")
    print("-" * 50)
    
    try:
        # Add current directory to Python path
        sys.path.insert(0, script_dir)
        
        # Import and run GUI
        from gui.main import main as gui_main
        gui_main()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("🔧 Trying alternative launch method...")
        
        # Alternative: subprocess launch
        try:
            subprocess.run([sys.executable, gui_path], cwd=script_dir)
        except Exception as e2:
            print(f"❌ Failed to launch GUI: {e2}")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️ Application interrupted by user")
        return 0
        
    except Exception as e:
        print(f"❌ Error launching GUI: {e}")
        print(f"🐛 Exception type: {type(e).__name__}")
        return 1
    
    print("👋 GUI application closed")
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)