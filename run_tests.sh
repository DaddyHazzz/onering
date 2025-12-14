#!/bin/bash
# OneRing Critical Test Suite - December 14, 2025
# Run this to verify all fixes are working correctly

echo "=========================================="
echo "OneRing Final Hardening Session - Test Suite"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0

# Helper function to run a test
run_test() {
    local test_num=$1
    local test_name=$2
    local test_cmd=$3
    
    echo -e "${YELLOW}[Test $test_num] $test_name${NC}"
    
    # This is a template - actual execution would depend on your setup
    # For now, we just print what should be tested
    echo "  → Command: $test_cmd"
    echo "  → See FINAL_SESSION_SUMMARY.md for detailed verification steps"
    echo ""
}

echo "PHASE 1: AUTH & BASELINE TESTS"
echo "=============================="
run_test 1 "Sign in with Clerk" "Navigate to http://localhost:3000 and click Sign In"
run_test 2 "Verify dashboard tabs load" "Check that all 5 tabs are visible (Generate, Post, Schedule, Leaderboard)"

echo ""
echo "PHASE 2: VIRAL THREAD TESTS (CRITICAL FIX #1)"
echo "=============================================="
run_test 3 "Viral thread generation - NO numbering" "POST /api/generate with type='viral_thread' - verify output has ZERO '1/6', '1.', etc."
run_test 4 "Harmful content keyword detection" "POST /api/generate with prompt='I'm worthless' - verify motivational redirection"
run_test 5 "Custom content copy function" "Paste content → click Copy → verify clipboard exact"

echo ""
echo "PHASE 3: TWITTER POSTING TESTS (CRITICAL FIX #2)"
echo "================================================"
run_test 6 "Twitter 403 credential validation" "Set invalid TWITTER_API_KEY in .env.local → POST /api/post-to-x → verify error includes troubleshooting steps"
run_test 7 "Twitter posting - success path" "Set valid credentials → generate thread → POST /api/post-to-x → verify URLs returned + RING awarded"
run_test 8 "Rate limiting (5 posts/15min)" "Post 5 threads → attempt 6th → verify rate limit error"

echo ""
echo "PHASE 4: MULTI-PLATFORM TESTS"
echo "============================="
run_test 9 "Instagram mock posting" "Click Post to IG → verify success response"
run_test 10 "TikTok/YouTube stub endpoints" "Click Post to TikTok → verify endpoint exists (stub)"

echo ""
echo "PHASE 5: PAYMENT & RING TESTS"
echo "============================"
run_test 11 "Stripe payment flow" "Click Buy RING → test card 4242... → verify +500 RING awarded + verified=true"
run_test 12 "RING staking" "Stake 100 RING for 30 days → verify position created + yield accrues"

echo ""
echo "PHASE 6: ERROR HANDLING TESTS"
echo "============================="
run_test 13 "Missing Groq API key error" "Remove GROQ_API_KEY → try generate → verify clear error"
run_test 14 "Network timeout graceful handling" "Mock timeout → verify error shown + no RING deducted"

echo ""
echo "PHASE 7: MONITORING TESTS"
echo "========================="
run_test 15 "Monitoring dashboard" "Navigate to http://localhost:3000/monitoring → verify stats + auto-refresh"

echo ""
echo "=========================================="
echo "TEST SUITE REFERENCE"
echo "=========================================="
echo ""
echo "Quick Smoke Test (10 min):"
echo "  - Test 1-2 (auth)"
echo "  - Test 3 (viral thread no numbering) [CRITICAL]"
echo "  - Test 6 (Twitter 403 handling) [CRITICAL]"
echo "  - Test 4 (harmful content filter)"
echo ""
echo "Full E2E Test (30 min):"
echo "  - Tests 1-15 (all tests above)"
echo ""
echo "Regression Test (15 min):"
echo "  - Test 5 (copy function)"
echo "  - Test 8 (rate limiting)"
echo "  - Test 12 (RING staking)"
echo ""
echo "=========================================="
echo "HOW TO RUN LOCALLY"
echo "=========================================="
echo ""
echo "1. Start infrastructure (Terminal 1):"
echo "   docker-compose -f infra/docker-compose.yml up -d"
echo ""
echo "2. Start backend (Terminal 2):"
echo "   cd backend"
echo "   python -m uvicorn main:app --reload --port 8000"
echo ""
echo "3. Start RQ worker (Terminal 3):"
echo "   rq worker -u redis://localhost:6379 default"
echo ""
echo "4. Start frontend (Terminal 4):"
echo "   pnpm dev"
echo ""
echo "5. (Optional) Start Stripe webhooks (Terminal 5):"
echo "   stripe listen --forward-to localhost:3000/api/stripe/webhook"
echo ""
echo "Then manually run through the tests, or:"
echo ""
echo "6. Reference FINAL_SESSION_SUMMARY.md for detailed steps"
echo ""
echo "=========================================="
echo "SUCCESS CRITERIA"
echo "=========================================="
echo ""
echo "✅ All 15 tests pass"
echo "✅ Viral thread generation: ZERO numbering"
echo "✅ Twitter posting: Actionable 403 errors, successful posts with RING"
echo "✅ No crashes, timeouts, or missing features"
echo ""
echo "=========================================="
