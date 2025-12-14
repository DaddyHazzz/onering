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
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to close...")

    
except Exception as e:
    print()
    print("=" * 80)
    print("[ERROR] Unexpected Error During Startup")
    print("=" * 80)
    print()
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {e}")
    print()
    print("Full traceback:")
    print("-" * 80)
    traceback.print_exc()
    print("-" * 80)
    print()
    print("Common fixes:")
    print("  1. Check that Redis is running: redis-cli ping")
    print("  2. Check that .env file exists and has correct values")
    print("  3. Check that all required Python packages are installed: pip install -r requirements.txt")
    print("  4. Check backend/core/config.py for any import errors")
    print()
    print("=" * 80)
    input("Press Enter to exit...")
    sys.exit(1)
