#!/usr/bin/env python3
"""
Minimal backend test - just import and start FastAPI
"""
import sys
import os

# Add workspace to path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_root)

print(f"Python {sys.version}")
print(f"Working from: {os.getcwd()}")
print(f"Script location: {__file__}")
print()

# Try importing step by step
print("[1] Importing FastAPI...")
from fastapi import FastAPI

print("[2] Importing uvicorn...")
import uvicorn

print("[3] Importing backend.main...")
from backend.main import app

print("[4] App imported successfully!")
print(f"    App routes: {len(app.routes)}")
print()

print("[5] Starting uvicorn server...")
print("    Server: http://localhost:8000")
print("    Press CTRL+C to stop")
print()

# Run it
if __name__ == "__main__":
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n[Server] Shutting down...")
        sys.exit(0)
