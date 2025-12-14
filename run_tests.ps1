# OneRing Critical Test Suite - December 14, 2025
# Run this to verify all fixes are working correctly

# For Windows PowerShell users

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "OneRing Final Hardening Session - Test Suite" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$testCount = 0

function Run-Test {
    param(
        [int]$TestNum,
        [string]$TestName,
        [string]$TestCmd
    )
    
    $global:testCount++
    Write-Host "[Test $TestNum] $TestName" -ForegroundColor Yellow
    Write-Host "  → $TestCmd" -ForegroundColor Gray
    Write-Host "  → See FINAL_SESSION_SUMMARY.md for detailed verification steps" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "PHASE 1: AUTH & BASELINE TESTS" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Run-Test 1 "Sign in with Clerk" "Navigate to http://localhost:3000 and click Sign In"
Run-Test 2 "Verify dashboard tabs load" "Check that all 5 tabs are visible"

Write-Host "PHASE 2: VIRAL THREAD TESTS (CRITICAL FIX #1)" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Run-Test 3 "Viral thread generation - NO numbering" "Verify output has ZERO '1/6', '1.', etc."
Run-Test 4 "Harmful content keyword detection" "Prompt with 'I'm worthless' - verify motivational redirection"
Run-Test 5 "Custom content copy function" "Paste content → click Copy → verify clipboard exact"

Write-Host "PHASE 3: TWITTER POSTING TESTS (CRITICAL FIX #2)" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Run-Test 6 "Twitter 403 credential validation" "Invalid credentials → verify error includes troubleshooting steps"
Run-Test 7 "Twitter posting - success path" "Valid credentials → post thread → verify URLs + RING awarded"
Run-Test 8 "Rate limiting (5 posts/15min)" "Post 5 threads → attempt 6th → verify error"

Write-Host "PHASE 4: MULTI-PLATFORM TESTS" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
Run-Test 9 "Instagram mock posting" "Click Post to IG → verify success"
Run-Test 10 "TikTok/YouTube stub endpoints" "Click endpoints → verify they exist"

Write-Host "PHASE 5: PAYMENT & RING TESTS" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
Run-Test 11 "Stripe payment flow" "Test card 4242... → verify +500 RING + verified=true"
Run-Test 12 "RING staking" "Stake 100 RING → verify position created"

Write-Host "PHASE 6: ERROR HANDLING TESTS" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
Run-Test 13 "Missing Groq API key error" "Remove key → try generate → verify clear error"
Run-Test 14 "Network timeout graceful handling" "Mock timeout → verify error + no RING deducted"

Write-Host "PHASE 7: MONITORING TESTS" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan
Run-Test 15 "Monitoring dashboard" "Navigate to /monitoring → verify stats auto-refresh"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TEST SUITE REFERENCE" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Quick Smoke Test (10 min):" -ForegroundColor Green
Write-Host "  - Test 1-2 (auth)"
Write-Host "  - Test 3 (viral thread no numbering) [CRITICAL]"
Write-Host "  - Test 6 (Twitter 403 handling) [CRITICAL]"
Write-Host "  - Test 4 (harmful content filter)"
Write-Host ""

Write-Host "Full E2E Test (30 min):" -ForegroundColor Green
Write-Host "  - Tests 1-15 (all tests above)"
Write-Host ""

Write-Host "Regression Test (15 min):" -ForegroundColor Green
Write-Host "  - Test 5 (copy function)"
Write-Host "  - Test 8 (rate limiting)"
Write-Host "  - Test 12 (RING staking)"
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "HOW TO RUN LOCALLY (Windows)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Option A: Use start_all.ps1" -ForegroundColor Yellow
Write-Host "  1. Open PowerShell in c:\Users\hazar\onering"
Write-Host "  2. Run: .\start_all.ps1"
Write-Host "  3. Wait for all services to start"
Write-Host ""

Write-Host "Option B: Manual start" -ForegroundColor Yellow
Write-Host ""

Write-Host "Terminal 1: Start infrastructure" -ForegroundColor Cyan
Write-Host "  docker-compose -f infra/docker-compose.yml up -d" -ForegroundColor Gray
Write-Host ""

Write-Host "Terminal 2: Start backend" -ForegroundColor Cyan
Write-Host "  cd backend" -ForegroundColor Gray
Write-Host "  python -m uvicorn main:app --reload --port 8000" -ForegroundColor Gray
Write-Host ""

Write-Host "Terminal 3: Start RQ worker" -ForegroundColor Cyan
Write-Host "  rq worker -u redis://localhost:6379 default" -ForegroundColor Gray
Write-Host ""

Write-Host "Terminal 4: Start frontend" -ForegroundColor Cyan
Write-Host "  pnpm dev" -ForegroundColor Gray
Write-Host ""

Write-Host "Terminal 5: (Optional) Stripe webhooks" -ForegroundColor Cyan
Write-Host "  stripe listen --forward-to localhost:3000/api/stripe/webhook" -ForegroundColor Gray
Write-Host ""

Write-Host "Then:" -ForegroundColor Cyan
Write-Host "  6. Reference FINAL_SESSION_SUMMARY.md for detailed test steps"
Write-Host "  7. Manually run through Tests 1-15"
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "SUCCESS CRITERIA" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "✅ All 15 tests pass" -ForegroundColor Green
Write-Host "✅ Viral thread generation: ZERO numbering" -ForegroundColor Green
Write-Host "✅ Twitter posting: Actionable 403 errors, successful posts with RING" -ForegroundColor Green
Write-Host "✅ No crashes, timeouts, or missing features" -ForegroundColor Green
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "DOCUMENTATION" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Read these files for complete context:" -ForegroundColor Yellow
Write-Host "  - SESSION_COMPLETE.md (quick reference)" -ForegroundColor Gray
Write-Host "  - FINAL_SESSION_SUMMARY.md (detailed testing)" -ForegroundColor Gray
Write-Host "  - TECHNICAL_DEEP_DIVE.md (implementation details)" -ForegroundColor Gray
Write-Host "  - README.md (updated troubleshooting)" -ForegroundColor Gray
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "READY FOR TESTING!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
