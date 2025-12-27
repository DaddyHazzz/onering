"""
Webhook Sink - A simple local server for testing webhook delivery.

Receives webhooks, verifies signatures, and logs events.

Usage:
    python tools/webhook_sink.py --port 9090 --secret whsec_test123
    
Then point your webhook subscription to http://localhost:9090/webhook
"""
import sys
import argparse
import json
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Optional

try:
    from fastapi import FastAPI, Request, Response, HTTPException
    from uvicorn import run as uvicorn_run
except ImportError:
    print("ERROR: FastAPI and uvicorn required. Install with:")
    print("  pip install fastapi uvicorn")
    sys.exit(1)


app = FastAPI(title="Webhook Sink", version="1.0.0")
WEBHOOK_SECRET: Optional[str] = None
DELIVERIES = []  # In-memory log


def verify_webhook_signature(
    secret: str,
    signature_header: str,
    timestamp: int,
    event_id: str,
    body_bytes: bytes,
) -> bool:
    """Verify webhook signature (HMAC-SHA256)."""
    # Extract v1 signature from header
    provided = None
    for part in signature_header.split(','):
        part = part.strip()
        if part.startswith('v1='):
            provided = part.split('=', 1)[1]
            break
    
    if not provided:
        return False
    
    # Reconstruct expected signature
    signed_content = f"{timestamp}.{event_id}.".encode() + body_bytes
    expected = hmac.new(secret.encode(), signed_content, hashlib.sha256).hexdigest()
    
    return hmac.compare_digest(provided, expected)


@app.post("/webhook")
async def receive_webhook(request: Request):
    """Receive and verify webhook delivery."""
    if not WEBHOOK_SECRET:
        raise HTTPException(status_code=400, detail="Webhook secret not configured")
    
    body_bytes = await request.body()
    
    # Extract headers
    signature_header = request.headers.get("X-Webhook-Signature")
    timestamp_header = request.headers.get("X-Webhook-Timestamp")
    event_id_header = request.headers.get("X-Webhook-Event-ID")
    
    if not all([signature_header, timestamp_header, event_id_header]):
        print("❌ Missing webhook headers")
        raise HTTPException(status_code=400, detail="Missing webhook headers")
    
    try:
        timestamp = int(timestamp_header)
    except ValueError:
        print("❌ Invalid timestamp")
        raise HTTPException(status_code=400, detail="Invalid timestamp")
    
    # Verify signature
    if not verify_webhook_signature(WEBHOOK_SECRET, signature_header, timestamp, event_id_header, body_bytes):
        print(f"❌ Invalid signature for event {event_id_header}")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse body
    try:
        body = json.loads(body_bytes)
    except json.JSONDecodeError:
        body = {"raw": body_bytes.decode('utf-8', errors='replace')}
    
    # Log delivery
    delivery = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_id": event_id_header,
        "event_type": body.get("eventType"),
        "signature_verified": True,
        "body": body,
    }
    DELIVERIES.append(delivery)
    
    print(f"✅ Webhook delivered: {event_id_header} ({body.get('eventType', 'unknown')})")
    print(f"   Body: {json.dumps(body, indent=2)}")
    
    return {"status": "ok", "event_id": event_id_header}


@app.get("/")
async def status():
    """Health check and status."""
    return {
        "status": "running",
        "deliveries_received": len(DELIVERIES),
        "webhook_secret_configured": WEBHOOK_SECRET is not None,
    }


@app.get("/deliveries")
async def list_deliveries():
    """List all received deliveries."""
    return {"deliveries": DELIVERIES}


@app.delete("/deliveries")
async def clear_deliveries():
    """Clear delivery history."""
    global DELIVERIES
    count = len(DELIVERIES)
    DELIVERIES = []
    return {"cleared": count}


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Webhook Sink for testing")
    parser.add_argument("--port", type=int, default=9090, help="Port to listen on (default: 9090)")
    parser.add_argument("--secret", type=str, help="Webhook secret (set before starting)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    
    args = parser.parse_args()
    
    global WEBHOOK_SECRET
    WEBHOOK_SECRET = args.secret or "whsec_test_default"
    
    print(f"🚀 Webhook Sink starting on {args.host}:{args.port}")
    print(f"📝 Webhook secret: {WEBHOOK_SECRET}")
    print(f"🔗 Webhook endpoint: http://{args.host}:{args.port}/webhook")
    print(f"📊 Status/deliveries: http://{args.host}:{args.port}/deliveries")
    print()
    
    uvicorn_run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
