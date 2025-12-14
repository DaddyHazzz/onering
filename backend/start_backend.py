#!/usr/bin/env python3
"""
Backend startup wrapper - properly handles process lifecycle
"""
import sys
import os
import signal

# Add workspace to path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_root)

# Prevent exit on reload
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

print("[Backend] Starting OneRing Backend")
print("[Backend] Server: http://localhost:8000")
print("[Backend] Press CTRL+C to stop")
print()

if __name__ == "__main__":
    try:
        import uvicorn
        # Use the app from backend.main
        uvicorn.run(
            "backend.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n[Backend] Shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
