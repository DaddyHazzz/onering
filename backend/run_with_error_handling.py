#!/usr/bin/env python3
"""
Simple wrapper to run the backend and show errors.
"""

import sys
import os

# Add workspace to path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_root)

if __name__ == "__main__":
    try:
        import uvicorn
        print("[Backend] Starting on http://localhost:8000")
        print("[Backend] Press CTRL+C to stop")
        print()

        # Run without reload to avoid multiprocessing issues on Windows
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,  # Disable reload to avoid Windows multiprocessing issues
            log_level="info"
        )
    except KeyboardInterrupt:
        print("[Backend] Shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
