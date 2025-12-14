# OneRing Testing & Verification Guide

Complete end-to-end testing checklist for OneRing. Run through these tests to verify all features are working correctly.

---

## Prerequisites
- All services running: Backend (8000), Frontend (3000), Redis, Postgres
- `.env.local` configured with all required credentials
- Clerk account with test user
- Stripe in test mode

---

## Phase 1: Authentication & Setup

### Test 1.1: Sign In with Clerk
- [ ] Visit http://localhost:3000
- [ ] Click "Sign in"
- [ ] Create test account or sign in with existing
- [ ] Verify dashboard loads at `/dashboard`
- [ ] Verify "OneRing" title and RING balance visible
- [ ] Verify UserButton (top right) shows user name and sign-out option

### Test 1.2: Daily Login Bonus
- [ ] New user should see alert about daily login bonus
- [ ] RING balance should include 10 RING daily bonus
- [ ] Refresh page and verify bonus only awarded once per day

### Test 1.3: Environment Verification
- [ ] Check browser console (F12) - no critical errors
- [ ] Check backend logs - no import or startup errors
- [ ] Check `next dev` logs - build successful

---

## Phase 2: Content Generation

### Test 2.1: Simple Generation (Groq Direct)
- [ ] Go to Dashboard
- [ ] Find "Generate with Groq" tab
- [ ] Enter prompt: "I love building AI tools"
- [ ] Click "Generate" button
- [ ] **Verify streaming:** Text appears character by character (NOT blocking all at once)
- [ ] **Verify "Groq is cooking..." message** disappears as content streams in
- [ ] Content appears in preview below input
- [ ] Copy button works (test with `Ctrl+C`)

### Test 2.2: Simple Generation - Extended Prompt
- [ ] Enter longer prompt (3-5 sentences)
- [ ] Verify streaming works smoothly
- [ ] Verify content is coherent and relevant to prompt
- [ ] No errors in browser console

### Test 2.3: Viral Thread Generation
- [ ] Click "🔥 Generate Full Viral Thread" tab
- [ ] Enter topic: "Why bootstrapped SaaS beats venture funding"
- [ ] Click "Generate Full Thread"
- [ ] **Verify LangGraph pipeline:**
  - Researcher step completes
  - Writer step completes
  - Optimizer step completes
- [ ] **Verify output format:**
  - 4-7 separate tweet boxes displayed
  - Each tweet is standalone (~280 chars max)
  - **NO numbering** (no "1/6", "1.", "(1)", etc.)
  - Tweets have natural separation, not cramped together
- [ ] Each tweet has its own visual box in preview
- [ ] Copy button works for full thread

### Test 2.4: Viral Thread - Personal Story
- [ ] Generate thread with topic: "I'm a felon in a halfway house trying to code my way out"
- [ ] Verify 5-6 tweets generated
- [ ] Verify tweets are emotional, specific, and engaging
- [ ] **Critical:** No numbering in output
- [ ] Verify each tweet is under 280 characters

### Test 2.5: Error Handling - Missing Groq Key
- [ ] Temporarily remove `GROQ_API_KEY` from `.env.local`
- [ ] Try to generate
- [ ] Verify error message displayed instead of crash
- [ ] Restore key and verify generation works again

---

## Phase 3: Social Media Posting

### Test 3.1: Post to X (Twitter) - Single Tweet
- [ ] Generate simple content or enter custom tweet
- [ ] Click "Post to X Now" button
- [ ] Verify success message with tweet URL
- [ ] Visit URL and verify tweet posted correctly
- [ ] Check console logs: `[post-to-x] posted, url: ...`

### Test 3.2: Post Thread to X
- [ ] Generate a viral thread (4-6 tweets)
- [ ] Click "📤 Post Thread to X" button
- [ ] Verify success message
- [ ] Check your Twitter feed
- [ ] Verify all tweets posted as threaded replies (not individual tweets)
- [ ] First tweet should be original, subsequent tweets should be "replying to..."
- [ ] **Critical:** No numbering (1/4, etc.) in the tweets themselves

### Test 3.3: Rate Limiting
- [ ] Post 5 tweets to X
- [ ] Try to post a 6th tweet
- [ ] Verify "Rate limit exceeded" error message
- [ ] Wait 1 hour or check Redis: `redis-cli DEL "rate:post:x:{userId}"`
- [ ] Verify you can post again

### Test 3.4: Error Handling - Invalid Credentials
- [ ] Set `TWITTER_API_KEY` to invalid value
- [ ] Try to post a tweet
- [ ] Verify error message (should show 401/403 with details)
- [ ] Verify no crash, user can retry
- [ ] Restore credentials

### Test 3.5: Post to Instagram (Mock)
- [ ] Generate content or use existing
- [ ] Click "Post to IG Now"
- [ ] Verify success message shows "posted to IG"
- [ ] Verify no errors in console

---

## Phase 4: Payment & Verification

### Test 4.1: Stripe Checkout
- [ ] Dashboard should show "Buy RING" button (if not verified)
- [ ] Click button
- [ ] Redirect to Stripe Checkout
- [ ] Use test card: `4242 4242 4242 4242`
- [ ] Use any future expiration date (e.g., 12/25)
- [ ] Use any 3-digit CVC
- [ ] Complete payment
- [ ] Redirect back to dashboard with `?session_id=...`
- [ ] Alert shows: "Verified! Blue check earned — +500 RING"

### Test 4.2: RING Award & Verification Status
- [ ] After payment, check RING balance
- [ ] Should increase by 500 RING (+ any daily login bonus)
- [ ] Verify Clerk metadata shows `verified: true` and blue check appears
- [ ] Verify "Buy RING" button disappears (user is now verified)

### Test 4.3: Stripe Webhook Verification
- [ ] In terminal running Stripe listen, check for events:
  - `checkout.session.completed`
  - `payment_intent.succeeded`
  - etc.
- [ ] Verify database record created with correct user and amount

### Test 4.4: Stripe Error Handling
- [ ] Temporarily disconnect internet or change webhook secret
- [ ] Try payment flow
- [ ] Verify graceful error message
- [ ] Verify user isn't double-charged if error occurs

---

## Phase 5: RING Economy

### Test 5.1: Mine RING Button
- [ ] Click "Mine RING +100" button
- [ ] Verify RING balance increases by 100
- [ ] Verify success message
- [ ] Click again immediately - should work (no cooldown)
- [ ] Mining should be unlimited for testing

### Test 5.2: RING Display & Persistence
- [ ] Generate and post content
- [ ] RING balance should update with engagement bonuses
- [ ] Refresh page
- [ ] RING balance should persist in Clerk metadata
- [ ] Close and reopen browser - balance still correct

### Test 5.3: RING Spending (if implemented)
- [ ] Check RING Actions section
- [ ] Verify "Boost Latest Post" button (-100 RING)
- [ ] Verify "Lease Premium Name" button (-200 RING)
- [ ] (Optional: Test if spending functionality is enabled)

---

## Phase 6: Family Pool & Referrals (if implemented)

### Test 6.1: Family List
- [ ] Check "Family Members" section
- [ ] Should initially be empty
- [ ] Verify combined RING balance displayed

### Test 6.2: Referral Code Generation (if implemented)
- [ ] Generate referral code
- [ ] Share link with another user
- [ ] Verify referrer is tracked on signup
- [ ] Verify both users get RING bonus

---

## Phase 7: Monitoring & Analytics

### Test 7.1: Monitoring Dashboard
- [ ] Visit http://localhost:3000/monitoring
- [ ] Verify stats load: active users, RING circulated, success rate
- [ ] Stats auto-refresh every 5 seconds
- [ ] View recent agent workflows (if any posts made)

### Test 7.2: Analytics Page
- [ ] Visit http://localhost:3000/analytics (if available)
- [ ] Verify stats load correctly
- [ ] Check viewership metrics

---

## Phase 8: Error Recovery & Edge Cases

### Test 8.1: Network Disconnection
- [ ] Stop backend while generation is streaming
- [ ] Verify graceful error message (not cryptic error)
- [ ] Restart backend
- [ ] Verify user can retry generation

### Test 8.2: Session Timeout
- [ ] Generate content
- [ ] Wait for Clerk session to timeout (normally 1 day, can force with dev tools)
- [ ] Try to post or mine RING
- [ ] Verify redirect to sign-in page

### Test 8.3: Concurrent Requests
- [ ] Open dashboard in 2 browser tabs
- [ ] Generate content in both tabs simultaneously
- [ ] Verify both complete without interference
- [ ] Verify RING balances consistent across tabs

### Test 8.4: Very Long Content
- [ ] Try to generate thread with extremely long topic (2000 chars)
- [ ] Verify input validation works
- [ ] Verify error message if too long

### Test 8.5: Special Characters in Content
- [ ] Generate thread with emojis, unicode, quotes, etc.
- [ ] Verify thread displays correctly
- [ ] Verify posts to X with special characters work

---

## Phase 9: Performance & Scaling

### Test 9.1: Generation Speed
- [ ] Time simple generation: should be < 10 seconds
- [ ] Time viral thread: should be < 30 seconds
- [ ] Verify no timeouts or hanging

### Test 9.2: Concurrent Users
- [ ] Open dashboard in 3-5 browser instances
- [ ] Have each generate content simultaneously
- [ ] Verify all complete without errors
- [ ] Check backend logs for proper request handling

### Test 9.3: Database Queries
- [ ] Check database for created records
- [ ] Verify user profiles and posts stored correctly
- [ ] Verify no duplicate records

---

## Phase 10: Browser & Environment Compatibility

### Test 10.1: Browser Compatibility
- [ ] **Chrome:** All tests pass ✅
- [ ] **Firefox:** All tests pass ✅
- [ ] **Safari:** (if macOS available) All tests pass ✅
- [ ] **Edge:** All tests pass ✅

### Test 10.2: Responsive Design
- [ ] Test on mobile viewport (375px width)
- [ ] Test on tablet viewport (768px width)
- [ ] Test on desktop (1920px width)
- [ ] Verify buttons and inputs accessible and functional

### Test 10.3: Light/Dark Mode
- [ ] Verify dark mode is default
- [ ] Text is readable against backgrounds
- [ ] No color contrast issues

---

## Test Results Summary

| Feature | Status | Notes |
|---------|--------|-------|
| Authentication | ✅/❌ | |
| Simple Generation | ✅/❌ | |
| Viral Thread Generation | ✅/❌ | |
| Post to X | ✅/❌ | |
| Post to Instagram | ✅/❌ | |
| Stripe Verification | ✅/❌ | |
| RING Mining | ✅/❌ | |
| Daily Bonus | ✅/❌ | |
| Rate Limiting | ✅/❌ | |
| Error Handling | ✅/❌ | |

---

## Known Issues & Workarounds

### Twitter 403 Error
**Symptom:** "Error: Request failed with code 403" when posting
**Cause:** Invalid or expired Twitter API credentials, or insufficient permissions
**Solution:** 
1. Check `.env.local` has correct Twitter API keys
2. Visit [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
3. Verify app has "Read and Write" permissions
4. Regenerate tokens if expired, update `.env.local`, restart

### Source Map Warnings
**Symptom:** "Invalid source map" messages in console during dev
**Cause:** Next.js development build
**Impact:** Harmless, development only. Disappears in production build

### Stripe Webhook Not Received
**Symptom:** Payment completes but RING not awarded
**Solution:**
1. Ensure `stripe listen` is running
2. Copy correct webhook secret from `stripe listen` output
3. Update `STRIPE_WEBHOOK_SECRET` in `.env.local`
4. Restart Next.js development server

---

## Debugging Tips

### Backend Issues
```bash
# Check backend logs
# Look for [generate], [post-to-x], [stripe/webhook] prefixes
# Verify Groq/Twitter/Stripe credentials are set

# Test backend directly
curl -X POST http://localhost:8000/v1/generate/content \
  -H "Content-Type: application/json" \
  -d '{"prompt":"hello","mode":"simple"}'
```

### Frontend Issues
```bash
# Check browser DevTools
F12 → Console tab for errors
F12 → Network tab to inspect API calls

# Check Next.js logs in terminal
Look for [proxy], [generate], [post-to-x] prefixed messages
```

### Database Issues
```bash
# Connect to Postgres
psql postgresql://user:pass@localhost:5432/onering

# Check user records
SELECT id, "clerkId", ring FROM "User" LIMIT 5;

# Check posts
SELECT id, "userId", content, status FROM "Post" LIMIT 5;
```

### Redis Issues
```bash
# Connect to Redis
redis-cli

# Check rate limit key
GET rate:post:x:{userId}

# Clear rate limit (if needed for testing)
DEL rate:post:x:{userId}
```

---

## Final Verification
- [ ] All 10 phases completed
- [ ] No critical errors in logs
- [ ] All major features working
- [ ] Documentation up to date
- [ ] Ready for production/next phase

---

**Last Updated:** December 14, 2025
**Version:** 1.0
