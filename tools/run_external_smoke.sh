#!/bin/bash

# Smoke test runner for External API platform
# Usage: ./tools/run_external_smoke.sh

set -e

echo "🔥 SMOKE TEST: External API Platform"
echo "====================================="
echo ""

# Validate prerequisites
echo "📋 Checking prerequisites..."

# Check backend is running
BACKEND_URL="http://localhost:8000"
if curl -s -m 2 "$BACKEND_URL/health" > /dev/null 2>&1; then
    echo "✓ Backend running on $BACKEND_URL"
else
    echo "✗ Backend not responding on $BACKEND_URL"
    echo "  Start with: cd backend && python -m uvicorn main:app --reload --port 8000"
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 not found"
    exit 1
fi
echo "✓ Python 3 available"
echo "✓ Prerequisites checked"
echo ""

# Run external_smoke.py
echo "🚀 Starting smoke tests..."
echo ""

export PYTHONPATH="$PWD/backend"
python3 backend/scripts/external_smoke.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 SMOKE TEST PASSED"
    echo ""
    echo "Next steps:"
    echo "1. Review metrics on http://localhost:3000/monitoring/external"
    echo "2. Test with real API key: curl -X GET http://localhost:8000/v1/external/me -H 'Authorization: Bearer \$KEY'"
    echo "3. Create webhooks on http://localhost:3000/admin/external"
    exit 0
else
    echo ""
    echo "❌ SMOKE TEST FAILED"
    echo "Check logs above for details"
    exit 1
fi
