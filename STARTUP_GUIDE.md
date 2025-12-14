# OneRing Startup Guide

**Updated:** December 14, 2025 - All services streamlined and tested ✅

## Quick Start (3 Minutes)

### Prerequisites
- Node.js 18+ and pnpm installed
- Python 3.10+ installed
- Docker Desktop running
- `.env.local` file with all required secrets (copy from `.env.example`)

### Option A: Automated Startup (One Command)
```bash
# From project root (c:\Users\hazar\onering)
.\start_all.ps1

# This starts all services in parallel:
# ✅ Docker (Redis + PostgreSQL)
# ✅ Backend (FastAPI on port 8000)
# ✅ Frontend (Next.js on port 3000)
# ✅ RQ Worker (background jobs)
# ✅ Stripe CLI (webhook forwarding) - optional
```

### Option B: Manual Startup (Separate Terminals)

**Terminal 1 - Infrastructure:**
```bash
docker-compose -f infra/docker-compose.yml up -d

# Verify Redis and PostgreSQL running:
docker ps | grep redis  # Should show container
docker ps | grep postgres  # Should show container
```

**Terminal 2 - Backend (FastAPI):**
```bash
# From c:\Users\hazar\onering (NOT from backend/ directory!)
python -m uvicorn backend.main:app --port 8000

# Expected output:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# 2025-12-14 ... INFO [onering] Starting OneRing backend...
# INFO:     Application startup complete.
```

**Terminal 3 - Frontend (Next.js):**
```bash
# From c:\Users\hazar\onering
pnpm dev

# Expected output:
# ▲ Next.js 16.0.7
#   Local: http://localhost:3000
# ✓ Starting...
# ✓ Ready in XXXms
```

**Terminal 4 - RQ Worker (Optional, for background jobs):**
```bash
# From c:\Users\hazar\onering
rq worker -u redis://localhost:6379 default

# Expected output:
# Worker started, PID: ...
# Looking for work...
```

**Terminal 5 - Stripe Webhooks (Optional, for payment testing):**
```bash
stripe listen --forward-to localhost:3000/api/stripe/webhook

# Copy the webhook secret and add to .env.local:
# STRIPE_WEBHOOK_SECRET=whsec_...
```

### Step 3: Access Application
```
http://localhost:3000
```

Sign in with Clerk → Dashboard loads with generation features

---

## Verification Checklist

After startup, verify all services:

✅ **Backend Running:**
```bash
curl http://localhost:8000/v1/health
# Should respond with JSON health status
```

✅ **Frontend Accessible:**
```bash
curl http://localhost:3000
# Should respond with HTML
```

✅ **Redis Connected:**
```bash
redis-cli ping
# Should respond: PONG
```

✅ **PostgreSQL Running:**
```bash
psql postgresql://user:pass@localhost:5432/onering -c "SELECT 1;"
# Should respond: 1
```

✅ **Services in Windows:**
- Backend window: Shows "Uvicorn running on http://127.0.0.1:8000"
- Frontend window: Shows "Ready in XXXms"
- RQ Worker window: Shows "Looking for work..."

---

## Important: Directory Structure

### Correct Structure (After Dec 14 Cleanup)
```
c:\Users\hazar\onering/
├── backend/           ← All backend code here
│   ├── main.py
│   ├── agents/
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── services/
│   ├── workers/
│   └── requirements.txt
├── src/               ← All frontend code here
│   └── app/
├── infra/
├── prisma/
├── docs/
├── .env.local         ← Frontend env vars
└── backend/.env       ← Backend env vars
```

### Key Point: Run Commands from Project Root
```bash
# ✅ CORRECT - Run from c:\Users\hazar\onering
python -m uvicorn backend.main:app --port 8000

# ❌ WRONG - Don't cd into backend/
# cd backend
# python -m uvicorn main:app --port 8000  # This breaks imports!
```
If you get import errors or port binding errors at startup:
```
ModuleNotFoundError: No module named 'workers.post_worker'
error while attempting to bind on address ('127.0.0.1', 8000)
```

### Troubleshooting

#### Port 8000 Already in Use
```bash
# Kill any existing Python processes
Get-Process python | Where-Object { $_.CommandLine -match "uvicorn" } | Stop-Process -Force

# Or kill specific port:
netstat -ano | Select-String ":8000"
taskkill /PID <PID> /F
```

#### Import Errors
- **Make sure you run commands from project root:** `c:\Users\hazar\onering`
- **NOT** from `c:\Users\hazar\onering\backend`
- The import paths use `backend.*` which requires workspace root context

#### pnpm not found
- **Solution:** `npm install -g pnpm`
- **Verify:** `pnpm --version`

#### Docker containers won't start
- **Ensure Docker Desktop is running** (not just installed)
- **Check:** `docker ps` - should list running containers
- **If error:** `docker-compose -f infra/docker-compose.yml logs` to see what failed

---

## Quick Troubleshooting Reference

| Issue | Check | Solution |
|-------|-------|----------|
| Backend won't start | Port 8000 in use | `Get-Process python \| Stop-Process -Force` |
| "ModuleNotFoundError" | Running from wrong dir | Ensure you're in `c:\Users\hazar\onering` |
| Frontend not loading | Next.js not running | Check terminal 3 for pnpm errors |
| Cannot connect to Redis | Redis not running | `docker-compose -f infra/docker-compose.yml up -d` |
| Stripe payments fail | Webhook secret wrong | Copy from `stripe listen` output to `.env.local` |
| Twitter posting 403 error | Invalid credentials | Update `.env.local` with fresh API keys |

---

## Environment Variables

### Frontend (.env.local)
```bash
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...
CLERK_SECRET_KEY=sk_...

# Groq LLM
GROQ_API_KEY=gsk_...

# Twitter/X API (Optional - required for posting)
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...

# Stripe Payment
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_... # From 'stripe listen' command

# Database & Cache
DATABASE_URL=postgresql://user:pass@localhost:5432/onering
REDIS_URL=redis://localhost:6379

# Backend Connection (optional, defaults to localhost:8000)
BACKEND_URL=http://localhost:8000
```

### Backend (backend/.env)
```bash
# Groq LLM
GROQ_API_KEY=gsk_...

# Twitter/X API (Optional - required for posting)
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...

# Stripe Payment
STRIPE_SECRET_KEY=sk_test_...

# Database & Cache
DATABASE_URL=postgresql://user:pass@localhost:5432/onering
REDIS_URL=redis://localhost:6379

# Clerk Authentication
CLERK_SECRET_KEY=sk_...

# Optional: Enable logging
LOG_LEVEL=INFO
```

---

## Next Steps

1. **Run startup:** `.\start_all.ps1`
2. **Sign in:** http://localhost:3000
3. **Generate content:** `/dashboard` → "Generate with Groq"
4. **Post to X:** Fill in Twitter credentials (optional)
5. **Complete verification:** See TESTING_GUIDE.md
6. **Monitor:** `http://localhost:3000/monitoring` for system health

---

## Files & Locations

| Component | Location | Start Command |
|-----------|----------|----------------|
| Frontend | `src/app` | `pnpm dev` |
| Backend | `backend/` | `python -m uvicorn backend.main:app --port 8000` |
| Database | PostgreSQL | Via Docker Compose |
| Cache | Redis | Via Docker Compose |
| Worker | `backend/workers/` | `rq worker` |
| Config | `.env.local`, `backend/.env` | Copy from `.env.example` |

---

**Last Updated:** December 14, 2025  
**Status:** All services working ✅  
**Next Session:** Add caching layer, optimize LLM prompts, mobile app
## Testing the Flow

### Test 1: Backend Health
```bash
curl http://localhost:8000/v1/health
# Expected: {"status":"healthy","uptime":...,"routes":...}
```

### Test 2: Frontend Loads
```bash
curl http://localhost:3000
# Expected: HTML response (Next.js page)
```

### Test 3: Content Generation
1. Go to `http://localhost:3000`
2. Sign in with Clerk
3. Go to `/dashboard`
4. Type a prompt in "Generate with Groq" tab
5. Click "Generate"
6. Content should stream character-by-character

### Test 4: Posting to X/Twitter (Optional)
1. Ensure Twitter API credentials are in `.env.local`
2. Generate content (or paste custom)
3. Click "Post to X Now"
4. Tweet should appear on your Twitter timeline

### Test 5: Monitoring Dashboard
1. Go to `http://localhost:3000/monitoring`
2. See system stats: active users, RING circulated, success rate
3. Stats auto-refresh every 5 seconds

---

## Troubleshooting

### Backend Won't Start
**Problem:** `python run_backend.py` doesn't output anything

**Solution:**
```bash
# Check Python is installed
python --version

# Run backend with verbose output
python -u run_backend.py

# If still stuck, kill any existing processes on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Backend 404 Errors
**Problem:** `[generate] backend error: 404`

**Solution:**
```bash
# WRONG - Don't do this
cd c:\Users\hazar\onering
uvicorn main:app --port 8000

# CORRECT - Do this
python run_backend.py
```

### Frontend Can't Reach Backend
**Problem:** `POST http://localhost:8000/v1/generate/content` → Connection refused

**Solution:**
1. Verify backend is running: `curl http://localhost:8000/v1/health`
2. If no response, backend isn't running. Start it: `python run_backend.py`
3. Wait 5 seconds for backend to fully start
4. Try again

### Redis Connection Error
**Problem:** `redis.exceptions.ConnectionError: Connection refused`

**Solution:**
```bash
# Check Docker is running
docker-compose -f infra/docker-compose.yml ps

# Should show redis running on port 6379
# If not, start it:
docker-compose -f infra/docker-compose.yml up -d
```

### PostgreSQL Connection Error
**Problem:** `psycopg2.OperationalError: could not connect to server`

**Solution:**
```bash
# Check Docker is running
docker-compose -f infra/docker-compose.yml ps

# Should show postgres running on port 5432
# If not, start it:
docker-compose -f infra/docker-compose.yml up -d
```

### Stripe Webhook Not Receiving Events
**Problem:** Payment webhook test doesn't show "Webhook received"

**Solution:**
```bash
# In a new terminal, start webhook listener
stripe listen --forward-to localhost:3000/api/stripe/webhook

# Copy the STRIPE_WEBHOOK_SECRET from output
# Add it to .env.local:
# STRIPE_WEBHOOK_SECRET=whsec_...

# Restart frontend for env var to take effect
# Press Ctrl+C on 'pnpm dev' and restart
```

---

## Stopping All Services

### Using PowerShell Script
```bash
.\stop_all.ps1
```

### Manual Cleanup
```bash
# Stop frontend (Ctrl+C in its terminal)
# Stop backend (Ctrl+C in its terminal)
# Stop RQ worker (Ctrl+C in its terminal)

# Stop Docker services
docker-compose -f infra/docker-compose.yml down

# Optional: Remove all data
docker-compose -f infra/docker-compose.yml down -v
```

---

## Development Tips

### Useful Commands
```bash
# Check all ports in use
netstat -ano | findstr LISTENING

# Kill process on specific port
taskkill /PID <PID> /F

# View backend logs in real-time
# Terminal where backend is running shows logs automatically

# View frontend build errors
# Terminal where 'pnpm dev' runs shows TypeScript errors

# Check Redis keys
redis-cli KEYS "*"
redis-cli GET "key_name"

# Check PostgreSQL
psql -U postgres -d onering -h localhost
```

### Code Changes
- **Backend changes:** Stop backend, update code, restart with `python run_backend.py`
- **Frontend changes:** Will auto-reload with `pnpm dev`
- **Environment variables:** Restart affected service

### Testing New Features
1. Make code changes
2. Restart affected service
3. Test in browser or with curl
4. Check logs for errors
5. Repeat

---

## Performance Notes

### Default Limits
- **Rate Limiting:** 5 posts per 15 minutes per user (configurable)
- **Content Generation:** Groq API defaults (streaming enabled)
- **Database:** PostgreSQL with pgvector for embeddings
- **Cache:** Redis for rate limits, sessions, job queues

### Optimization
- Increase RQ worker threads: `rq worker -c 4 default`
- Monitor backend performance: `http://localhost:3000/monitoring`
- Check database performance: Connect with DBeaver
- Monitor Redis: `redis-cli INFO stats`

---

## Next Steps

1. ✅ Backend running with `python run_backend.py`
2. ✅ All services started
3. ⏳ Sign in with Clerk
4. ⏳ Generate content
5. ⏳ Post to X/Instagram
6. ⏳ Check RING rewards
7. ⏳ Monitor system health

---

**Last Updated:** December 13, 2025
**Status:** Ready to Use ✅

For more details, see:
- `README.md` - Full testing guide
- `BACKEND_FIX_SUMMARY.md` - Backend 404 issue details
- `SESSION_SUMMARY.md` - Complete session history
- `.github/copilot-instructions.md` - Architecture details for AI agents
