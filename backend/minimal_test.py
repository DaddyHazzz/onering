#!/usr/bin/env python3
"""
Ultra-minimal backend test - create app step by step
"""
import sys
import os
import logging

# Set up logging first
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("test")

# Add workspace to path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_root)

print(f"[Test] Python {sys.version_info.major}.{sys.version_info.minor}")
print(f"[Test] Working from: {os.getcwd()}")
print()

# Step 1: Import FastAPI
print("[Test] Step 1: Import FastAPI")
from fastapi import FastAPI
app = FastAPI(title="TestApp")

@app.get("/test")
def test():
    return {"status": "ok"}

print("[Test]   ✓ FastAPI imported, basic app created")
print()

# Step 2: Try importing all backend requirements
print("[Test] Step 2: Import backend modules")
try:
    print("[Test]   - Loading dotenv...")
    from dotenv import load_dotenv
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(dotenv_path=os.path.join(backend_dir, '.env'))
    print("[Test]     ✓ dotenv loaded")

    print("[Test]   - Loading backend.core.config...")
    sys.path.insert(0, backend_dir)
    sys.path.insert(0, workspace_root)
    from backend.core.config import settings
    print("[Test]     ✓ config loaded")

    print("[Test]   - Loading backend.core.logging...")
    from backend.core.logging import configure_logging
    configure_logging()
    print("[Test]     ✓ logging configured")

    print("[Test] ✓ All imports successful")
except Exception as e:
    print(f"[Test] ✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("[Test] Step 3: Start uvicorn")
print("[Test]   Server: http://localhost:8000")
print("[Test]   Press CTRL+C to stop")
print()

# Run it
if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n[Test] Shutting down...")
        sys.exit(0)
