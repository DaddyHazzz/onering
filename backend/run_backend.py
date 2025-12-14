#!/usr/bin/env python
"""
Persistent backend runner for OneRing.
Keeps uvicorn running even if it crashes.
"""
import subprocess
import time
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

while True:
    print("\n[INFO] Starting backend server on port 8000...")
    try:
        subprocess.run([sys.executable, "-m", "uvicorn", "main:app", "--port", "8000"], check=False)
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down backend...")
        break
    except Exception as e:
        print(f"[ERROR] {e}")
    
    print("[INFO] Backend stopped, will restart in 2 seconds...")
    time.sleep(2)
