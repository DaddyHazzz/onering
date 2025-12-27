# Phase 10.3 Enablement Checklist

**Last Updated:** Dec 27, 2025  
**Rollout Date:** TBD  
**Owner:** TPM / Principal Engineer

Copy and use this checklist in production enablement.

---

## Pre-Launch (48 hours before)

### Code & Deployment
- [ ] All Phase 10.3 code merged to main
- [ ] Tests passing: `pnpm gate --mode full` (zero skipped, zero failed)
- [ ] Monitoring endpoints tested: `/v1/monitoring/external/metrics`, `/v1/monitoring/webhooks/metrics`
- [ ] Smoke script verified: `python backend/scripts/external_smoke.py --help`
- [ ] Webhook sink tool verified: `python tools/webhook_sink.py --help`
- [ ] Database migrations staged: `npx prisma migrate deploy` (test in staging first)

### Infrastructure
- [ ] Redis running and accessible
- [ ] PostgreSQL healthy, with pgvector extension
- [ ] Backend service ready for deployment
- [ ] RQ worker ready for deployment
- [ ] Webhook delivery worker script ready: `backend/workers/webhook_delivery.py`
- [ ] Alerting configured for monitoring endpoints

### Documentation & Training
- [ ] Team reviewed RUNBOOK_EXTERNAL_ENABLEMENT.md
- [ ] On-call rotation established for Phase 10.3
- [ ] Incident playbook distributed
- [ ] Consumer API docs shared with partners
- [ ] Rate limit tiers documented and communicated

### Monitoring Setup
- [ ] Dashboards configured to scrape `/v1/monitoring/external/metrics`
- [ ] Dashboards configured to scrape `/v1/monitoring/webhooks/metrics`
- [ ] Alert thresholds set:
  - [ ] Dead-letter > 10/24h
  - [ ] Auth failures > 50/24h
  - [ ] Rate limit hits > 100/24h
  - [ ] Replay rejections > 20/24h
  - [ ] Latency p90 > 5s
- [ ] Notification channels verified (Slack, PagerDuty, etc.)

---

## Canary Launch (Stage 1)

### Hour 0: Enable External API (Canary-Only)
```bash
# Deploy with these env vars:
export ONERING_EXTERNAL_API_ENABLED=1
export ONERING_EXTERNAL_API_CANARY_ONLY=1  # Only canary keys allowed
export ONERING_WEBHOOKS_ENABLED=0
export ONERING_WEBHOOKS_DELIVERY_ENABLED=0

# No deployment needed if using K8s ConfigMap reload
# Otherwise: restart FastAPI backend
```

- [ ] Check logs: no startup errors
- [ ] Health check: `curl http://localhost:8000/docs`
- [ ] Create canary test key via admin endpoint
- [ ] Verify key has `canary_enabled=true`
- [ ] Test key works: `curl /v1/external/me -H "Authorization: Bearer ..."`
- [ ] Verify rate limit headers in response (should show 10/hr for canary)

### Hour 1: Run Smoke Test (Canary)
```bash
# Terminal 1: Start webhook sink
python tools/webhook_sink.py --port 9090 --secret whsec_test

# Terminal 2: Run smoke test
python backend/scripts/external_smoke.py \
  --backend-url http://localhost:8000 \
  --admin-key <admin_key> \
  --webhook-sink http://localhost:9090/webhook
```

- [ ] All smoke tests pass (Backend Health, API Key Creation, etc.)
- [ ] Canary key works for all endpoints
- [ ] Rate limit enforcement works (10/hr)
- [ ] No errors in logs

### Hour 2-4: Monitor Metrics
```bash
# Continuous monitoring
watch -n 5 'curl http://localhost:8000/v1/monitoring/external/metrics | jq .'
```

- [ ] No auth failures spiking
- [ ] No rate limit hits (we're under limit)
- [ ] Active keys = 1 (our test key)
- [ ] No alerts triggered

### Hours 4-24: Soak Test
Keep canary mode running for 24 hours with:
- Small volume of test traffic
- Monitoring all metrics
- On-call engineer watching alerts

- [ ] No unexpected errors in logs
- [ ] No alert thresholds exceeded
- [ ] Metrics UI stable and accurate

---

## Webhook Launch (Stage 2)

### Hour 24: Enable Webhook Events
```bash
# Deploy with:
export ONERING_WEBHOOKS_ENABLED=1
export ONERING_WEBHOOKS_DELIVERY_ENABLED=0  # Worker not started yet
```

- [ ] Restart FastAPI backend
- [ ] Verify no startup errors
- [ ] Create test webhook subscription pointing to webhook sink
- [ ] Verify subscription created (has ID and secret)

### Hour 25: Start Delivery Worker
```bash
# In separate terminal/container:
python -m backend.workers.webhook_delivery --loop
```

- [ ] Worker starts without errors
- [ ] Check logs: "Webhook delivery worker started"
- [ ] Monitor logs for "processing delivery" messages

### Hour 26: Trigger Test Event
```bash
# Trigger a known event
curl -X POST http://localhost:8000/v1/external/events \
  -H "Authorization: Bearer <canary_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "test.webhook",
    "data": {"test": true}
  }'

# Check webhook sink
curl http://localhost:9090/deliveries | jq .
```

- [ ] Event created in system
- [ ] Delivery worker processes it (logs show "processing delivery")
- [ ] Webhook sink receives delivery
- [ ] Signature verified successfully
- [ ] Metrics show: delivered += 1

### Hours 26-48: Webhook Soak Test
Keep webhooks running with:
- Periodic test events
- Monitor `/v1/monitoring/webhooks/metrics`
- Check for dead-letter accumulation
- Check delivery latency p90

- [ ] Delivery latency p90 < 5s (or your threshold)
- [ ] No dead-letters (or < threshold)
- [ ] No replay rejections (clocks synchronized)
- [ ] On-call engineer watching

---

## Full Production Launch (Stage 3)

### Hour 48: Disable Canary-Only Mode
```bash
# Deploy with:
export ONERING_EXTERNAL_API_ENABLED=1
export ONERING_EXTERNAL_API_CANARY_ONLY=0  # Allow all keys now
export ONERING_WEBHOOKS_ENABLED=1
export ONERING_WEBHOOKS_DELIVERY_ENABLED=1
```

- [ ] Restart FastAPI backend
- [ ] No startup errors
- [ ] Create normal (non-canary) API key
- [ ] Test key works with normal rate limits (tier-based)
- [ ] Verify `/v1/external/me` response: X-RateLimit-Limit matches tier (e.g., 100 for free, 1000 for pro)

### Hour 49: Announce to Partners
```markdown
Subject: OneRing External API is now available

The OneRing External API is live!
- Docs: https://...
- Rate limits: free=100/hr, pro=1000/hr, enterprise=10k/hr
- Contact support for API key

Example:
  curl -H "Authorization: Bearer osk_YOUR_KEY" https://api.onering.com/v1/external/me
```

- [ ] Announcement sent to customer list
- [ ] API docs published
- [ ] Rate limit tiers communicated
- [ ] Support team briefed on common issues

### Hour 50-72: Monitor Full Production
```bash
# Continuous monitoring script
for i in {1..72}; do
  echo "=== Hour $i ==="
  curl http://localhost:8000/v1/monitoring/external/metrics | jq '.alerts'
  curl http://localhost:8000/v1/monitoring/webhooks/metrics | jq '.alerts'
  sleep 3600
done
```

- [ ] Alerts triggering correctly
- [ ] No unexpected errors
- [ ] Dead-letter rate stable
- [ ] Delivery latency stable
- [ ] Rate limiting working as expected

### Day 3: Post-Mortem & Optimization
- [ ] Review monitoring data from first 72 hours
- [ ] Adjust alert thresholds if needed
- [ ] Document any incidents and resolutions
- [ ] Share findings with team

---

## Rollback Plan (If Needed)

### Critical Issue Detected
```bash
# Immediate: Disable everything
export ONERING_EXTERNAL_API_ENABLED=0
export ONERING_WEBHOOKS_ENABLED=0
export ONERING_WEBHOOKS_DELIVERY_ENABLED=0

# Restart FastAPI
# Kill webhook delivery worker
# Alert TPM / SRE
```

### Investigation
1. Review logs from last 1 hour
2. Check metrics spikes: `/v1/monitoring/*/metrics`
3. Check recent webhook deliveries: `/v1/monitoring/webhooks/recent`
4. List API key failures: `/v1/monitoring/external/metrics`

### Fix & Re-Enable
1. Identify root cause
2. Merge fix to main branch
3. Deploy fix
4. Re-enable following Stage 1 → 2 → 3 sequence again

---

## Sign-Off

**Canary Launch (Stage 1):**
- [ ] TPM approval
- [ ] SRE sign-off
- [ ] Initial monitoring passed

**Webhook Launch (Stage 2):**
- [ ] TPM approval
- [ ] Delivery worker testing passed
- [ ] Webhook metrics stable

**Production Launch (Stage 3):**
- [ ] TPM approval
- [ ] SRE final sign-off
- [ ] Customer announcement sent
- [ ] 72-hour soak test passed

---

**Notes:**
Use this section to document any deviations or issues encountered.

```
[Space for notes during rollout]
```
