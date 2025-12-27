# OneRing External API — Consumer Implementation Guide

**For:** Third-party integrations using OneRing External API  
**Version:** Phase 10.3  
**Last Updated:** Dec 27, 2025

---

## Quick Start

### 1. Get Your API Key

Contact OneRing support to request an external API key. You'll receive:
```
Key ID: osk_abc123...
Secret: osk_full_secret_shown_only_once...  ← Store securely!
Tier: pro (1000 requests/hour)
```

**Never share your secret!** Rotate it immediately if leaked.

### 2. Make Your First Request

```python
import requests

API_KEY = "osk_your_secret_here"
BASE_URL = "https://api.onering.com"

response = requests.get(
    f"{BASE_URL}/v1/external/me",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
)

print(response.json())
# {
#   "key_id": "osk_abc123",
#   "owner_user_id": "user_xyz",
#   "scopes": ["read:rings", "read:drafts"],
#   "rate_limit_tier": "pro",
#   "canary_enabled": false
# }

print(response.headers["X-RateLimit-Limit"])  # 1000
print(response.headers["X-RateLimit-Remaining"])  # 999
print(response.headers["X-RateLimit-Reset"])  # Unix timestamp
```

---

## Webhook Setup

### 1. Create Webhook Subscription

```python
import requests

API_KEY = "osk_your_secret_here"

response = requests.post(
    "https://api.onering.com/v1/external/webhooks",
    json={
        "url": "https://your-domain.com/webhooks/onering",
        "events": [
            "draft.published",
            "draft.edited",
            "enforcement.failed",
        ],
    },
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
)

webhook = response.json()
# {
#   "id": "wh_xyz123",
#   "url": "https://your-domain.com/webhooks/onering",
#   "secret": "whsec_abc123...",  ← Store this securely!
#   "events": ["draft.published", "draft.edited", "enforcement.failed"],
#   "created_at": "2025-12-27T10:00:00Z",
#   "last_delivered_at": null
# }
```

### 2. Implement Webhook Handler

Your endpoint receives POST requests with webhook events.

**Headers:**
```
X-Webhook-Signature: t=1703673600,e=evt_123abc,v1=abc123def456...
X-Webhook-Timestamp: 1703673600
X-Webhook-Event-ID: evt_123abc
Content-Type: application/json
```

**Body:**
```json
{
  "eventType": "draft.published",
  "eventId": "evt_123abc",
  "timestamp": "2025-12-27T10:00:00Z",
  "data": {
    "draftId": "draft_xyz",
    "userId": "user_123",
    "platform": "x",
    "content": "Check out OneRing..."
  }
}
```

### 3. Verify Webhook Signature

**Python:**
```python
import hmac
import hashlib
import json

WEBHOOK_SECRET = "whsec_your_secret_here"

def verify_webhook(request_body: bytes, headers: dict) -> bool:
    """Verify OneRing webhook signature."""
    signature_header = headers.get("X-Webhook-Signature")
    timestamp = int(headers.get("X-Webhook-Timestamp", 0))
    event_id = headers.get("X-Webhook-Event-ID")
    
    if not all([signature_header, timestamp, event_id]):
        return False
    
    # Reconstruct signed content
    signed = f"{timestamp}.{event_id}.".encode() + request_body
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        signed,
        hashlib.sha256
    ).hexdigest()
    
    # Extract provided signature from header
    provided = None
    for part in signature_header.split(','):
        if part.strip().startswith('v1='):
            provided = part.strip().split('=')[1]
            break
    
    if not provided:
        return False
    
    # Compare (timing-safe)
    return hmac.compare_digest(provided, expected)


# Flask/FastAPI example
from flask import request, jsonify

@app.route("/webhooks/onering", methods=["POST"])
def handle_webhook():
    body = request.get_data()
    
    if not verify_webhook(body, request.headers):
        return jsonify({"error": "Invalid signature"}), 401
    
    event = request.json
    
    # Handle event
    if event["eventType"] == "draft.published":
        print(f"Draft published: {event['data']['draftId']}")
        # Process event...
    
    return jsonify({"status": "ok"}), 200
```

**JavaScript/Node.js:**
```javascript
import crypto from 'crypto';

const WEBHOOK_SECRET = "whsec_your_secret_here";

function verifyWebhook(body, headers) {
  const signature = headers['x-webhook-signature'];
  const timestamp = headers['x-webhook-timestamp'];
  const eventId = headers['x-webhook-event-id'];
  
  if (!signature || !timestamp || !eventId) {
    return false;
  }
  
  // Reconstruct signed content
  const signed = `${timestamp}.${eventId}.` + body;
  const expected = crypto
    .createHmac('sha256', WEBHOOK_SECRET)
    .update(signed)
    .digest('hex');
  
  // Extract provided signature
  const match = signature.match(/v1=([a-f0-9]+)/);
  const provided = match ? match[1] : null;
  
  if (!provided) {
    return false;
  }
  
  // Compare
  return crypto.timingSafeEqual(
    Buffer.from(expected),
    Buffer.from(provided)
  );
}

// Express.js example
app.post('/webhooks/onering', express.raw({ type: 'application/json' }), (req, res) => {
  if (!verifyWebhook(req.body, req.headers)) {
    return res.status(401).json({ error: 'Invalid signature' });
  }
  
  const event = JSON.parse(req.body);
  
  // Handle event
  if (event.eventType === 'draft.published') {
    console.log(`Draft published: ${event.data.draftId}`);
    // Process event...
  }
  
  res.json({ status: 'ok' });
});
```

### 4. Handle Webhook Errors

Your endpoint should:
- **Return 200-299:** Webhook treated as successful
- **Return 4xx:** Webhook won't retry (client error)
- **Return 5xx:** Webhook will retry (server error)
- **Timeout (>10s):** Treated as failure, will retry
- **No response:** After 10 seconds, treated as timeout

**Retry Schedule:**
- Attempt 1: Immediately
- Attempt 2: After 60 seconds
- Attempt 3: After 5 minutes
- Attempt 4: After 15 minutes (dead-lettered if failed)

---

## Rate Limiting

### Understanding Rate Limits

Each request returns rate limit info in headers:

```
X-RateLimit-Limit: 1000        # Max requests per hour
X-RateLimit-Remaining: 987     # Requests left this hour
X-RateLimit-Reset: 1703677200  # Unix timestamp when limit resets
```

### Tier Details

| Tier | Rate Limit | Features |
|------|-----------|----------|
| **free** | 100/hour | Read-only |
| **pro** | 1,000/hour | Webhooks |
| **enterprise** | 10,000/hour | Custom scopes, priority support |

To upgrade, contact OneRing sales.

### Handling Rate Limit Errors

```python
import requests
import time

def make_request_with_retry(url, headers, max_retries=3):
    """Make request, retry on rate limit."""
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:  # Rate limited
            reset_time = int(response.headers["X-RateLimit-Reset"])
            sleep_seconds = max(reset_time - time.time(), 0)
            print(f"Rate limited. Waiting {sleep_seconds} seconds...")
            time.sleep(sleep_seconds + 1)  # Wait slightly past reset
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

---

## Common Endpoints

### Read User Info
```bash
GET /v1/external/me
Authorization: Bearer osk_your_key

Returns:
{
  "key_id": "osk_...",
  "scopes": ["read:rings"],
  "rate_limit_tier": "pro"
}
```

### Query Rings (User)
```bash
GET /v1/external/users/{user_id}/rings
Authorization: Bearer osk_your_key

Returns:
{
  "user_id": "user_xyz",
  "total_ring": 5000,
  "earned_ring": 3200,
  "pending_ring": 0
}
```

### List Webhooks
```bash
GET /v1/external/webhooks
Authorization: Bearer osk_your_key

Returns:
{
  "webhooks": [
    {
      "id": "wh_123",
      "url": "https://...",
      "events": ["draft.published"],
      "last_delivered_at": "2025-12-27T09:30:00Z"
    }
  ]
}
```

### Publish Event (Testing)
```bash
POST /v1/external/events
Authorization: Bearer osk_your_key
Content-Type: application/json

{
  "event_type": "test.event",
  "data": {
    "message": "Testing webhook"
  }
}

Returns:
{
  "event_id": "evt_abc123",
  "queued": true
}
```

---

## Error Codes

| Code | Status | Meaning | Recovery |
|------|--------|---------|----------|
| `INVALID_KEY` | 401 | Key doesn't exist or expired | Check key_id and secret |
| `INSUFFICIENT_SCOPE` | 403 | Key lacks required permission | Request new key with scope |
| `CANARY_ONLY_MODE` | 403 | API in canary-only mode | Wait for public launch |
| `RATE_LIMIT_EXCEEDED` | 429 | Exceeded quota | Wait for reset time |
| `INVALID_SIGNATURE` | 401 | Webhook signature invalid | Verify secret, check clock skew |
| `REPLAY_DETECTED` | 400 | Webhook timestamp too old | Check server clock |
| `INTERNAL_ERROR` | 500 | Server error | Retry after 30 seconds |

---

## Best Practices

### Security
- ✅ **Store secrets in environment variables**, not code
- ✅ **Verify webhook signatures** on every request
- ✅ **Rotate API keys** every 90 days
- ✅ **Use HTTPS** (enforce in production)
- ❌ Don't log API keys or secrets
- ❌ Don't share keys across environments (dev/staging/prod)

### Performance
- ✅ **Implement exponential backoff** for retries
- ✅ **Use concurrent requests** where appropriate
- ✅ **Cache responses** when acceptable
- ✅ **Process webhooks asynchronously** (queue them)
- ❌ Don't poll endpoints repeatedly (use webhooks instead)

### Reliability
- ✅ **Handle idempotency**: same event might arrive twice
- ✅ **Respect rate limits**: don't hammer endpoints
- ✅ **Check X-RateLimit headers** to avoid 429 errors
- ✅ **Return 200 quickly** from webhook handler, process async
- ❌ Don't assume webhook ordering is guaranteed

---

## Monitoring Your Integration

### Health Check
```bash
curl -s https://api.onering.com/v1/external/me \
  -H "Authorization: Bearer osk_your_key" | jq .
```

### Check Webhook Status
```bash
curl -s https://api.onering.com/v1/external/webhooks \
  -H "Authorization: Bearer osk_your_key" | jq '.webhooks | .[] | {id, last_delivered_at}'
```

### Monitor Rate Limits
```bash
# Run hourly
curl -s https://api.onering.com/v1/external/me \
  -H "Authorization: Bearer osk_your_key" \
  -w "\nRate Limit: %{http_code}\n" \
  | grep -E "X-RateLimit|Rate Limit"
```

---

## Support

- **Documentation:** https://docs.onering.com/external-api
- **Status Page:** https://status.onering.com
- **Issues:** support@onering.com
- **Slack:** #external-api-partners (invite-only)

---

**Next:** [API Reference](.ai/API_REFERENCE.md)
