#!/usr/bin/env python3
"""
Wrapper to run the backend with proper error handling and debugging.
Shows actual errors instead of closing terminal immediately.
"""

import sys
import os
import traceback

# Add the workspace root to path so imports work correctly
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_root)

print(f"[Backend Startup] Python: {sys.version}")
print(f"[Backend Startup] Working directory: {os.getcwd()}")
print(f"[Backend Startup] Workspace root: {workspace_root}")
print(f"[Backend Startup] sys.path: {sys.path[:2]}...")
print()

def main():
    try:
        print("[Backend Startup] Attempting to import uvicorn...")
        import uvicorn
        print("[Backend Startup] ✓ uvicorn imported successfully")
        
        print("[Backend Startup] ✓ uvicorn ready")
        
        print("[Backend Startup] Starting uvicorn server...")
        print("[Backend Startup] Listening on http://localhost:8000")
        print("[Backend Startup] Docs available at http://localhost:8000/docs")
        print()
        
        # Use import string format for uvicorn so reload works properly
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=[workspace_root],
            log_level="info"
        )
    
    except ImportError as e:
        print()
        print("=" * 80)
        print("[ERROR] Import Error - Missing Module or Package")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        print()
        print("This usually means a required Python package is not installed.")
        print("Fix: Run this command in the backend directory:")
        print()
        print("  pip install -r requirements.txt")
        print()
        traceback.print_exc()
        print()
        print("=" * 80)
        input("Press Enter to exit...")
        sys.exit(1)
        
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

if __name__ == "__main__":
    main()
    
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
