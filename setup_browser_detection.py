#!/usr/bin/env python3
"""
Setup script for browser-based community detection

This script installs the necessary dependencies and sets up
the environment for real DOM-based community detection.
"""

import subprocess
import sys
import os

def install_requirements():
    """Install required packages"""
    try:
        print("🔧 Installing browser detection requirements...")
        
        # Install selenium and related packages
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "selenium>=4.15.0", 
            "webdriver-manager>=4.0.0"
        ], check=True)
        
        print("✅ Browser detection dependencies installed successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False
    
    return True

def check_chrome():
    """Check if Chrome is installed"""
    try:
        # Try to find Chrome executable
        chrome_paths = [
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
        
        chrome_found = False
        for path in chrome_paths:
            if os.path.exists(path):
                print(f"✅ Chrome found at: {path}")
                chrome_found = True
                break
        
        if not chrome_found:
            print("⚠️ Chrome not found in common locations")
            print("💡 Please install Google Chrome for browser-based detection")
            print("💡 Download from: https://www.google.com/chrome/")
        
        return chrome_found
        
    except Exception as e:
        print(f"Error checking Chrome: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Browser-Based Community Detection")
    print("=" * 50)
    
    # Install requirements
    if not install_requirements():
        print("❌ Setup failed - could not install requirements")
        return
    
    # Check Chrome
    check_chrome()
    
    print("\n" + "=" * 50)
    print("✅ Setup completed!")
    print("\n📖 Usage:")
    print("  python quick_browser_test.py  # Test browser detection")
    print("\n🎯 Features:")
    print("  • Real DOM community metadata extraction")
    print("  • Inherits authentication from cookie manager")
    print("  • Only detects NEW communities (smart comparison)")
    print("  • Automatic notifications for new detections")
    print("  • Fast execution with intelligent caching")
    
if __name__ == "__main__":
    main() 