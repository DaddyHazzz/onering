#!/usr/bin/env python3
"""
External Platform Smoke Test Script (Phase 10.3).

End-to-end verification of external API + webhooks.

Usage:
    python backend/scripts/external_smoke.py \\
        --backend-url http://localhost:8000 \\
        --admin-key <admin_key> \\
        --webhook-sink http://localhost:9090/webhook

Prerequisites:
    - Backend running on --backend-url
    - Admin API key with external:admin scope
    - Webhook sink running on --webhook-sink (run: python tools/webhook_sink.py --port 9090)
    - PostgreSQL migrations applied
"""
import argparse
import json
import time
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import sys

try:
    import requests
except ImportError:
    print("ERROR: requests module required. Install with: pip install requests")
    sys.exit(1)


class ExternalApiSmokeTest:
    """Smoke test runner for external platform."""
    
    def __init__(self, backend_url: str, admin_key: str, webhook_sink_url: str):
        self.backend_url = backend_url.rstrip("/")
        self.admin_key = admin_key
        self.webhook_sink_url = webhook_sink_url
        self.api_key: Optional[str] = None
        self.webhook_id: Optional[str] = None
        self.webhook_secret: Optional[str] = None
        self.results = []
    
    def log(self, step: str, status: str, details: str = ""):
        """Log test step."""
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏳"
        msg = f"{status_icon} {step}: {status}"
        if details:
            msg += f" | {details}"
        print(msg)
        self.results.append({"step": step, "status": status, "details": details})
    
    def verify_webhook_signature(
        self,
        secret: str,
        signature_header: str,
        timestamp: int,
        event_id: str,
        body_bytes: bytes,
    ) -> bool:
        """Verify webhook HMAC-SHA256 signature."""
        provided = None
        for part in signature_header.split(','):
            part = part.strip()
            if part.startswith('v1='):
                provided = part.split('=', 1)[1]
                break
        
        if not provided:
            return False
        
        signed_content = f"{timestamp}.{event_id}.".encode() + body_bytes
        expected = hmac.new(secret.encode(), signed_content, hashlib.sha256).hexdigest()
        return hmac.compare_digest(provided, expected)
    
    def test_admin_health(self) -> bool:
        """Check backend is alive."""
        try:
            resp = requests.get(f"{self.backend_url}/docs", timeout=5)
            ok = resp.status_code == 200
            self.log("Backend Health", "PASS" if ok else "FAIL", f"Status: {resp.status_code}")
            return ok
        except Exception as e:
            self.log("Backend Health", "FAIL", str(e))
            return False
    
    def test_create_api_key(self) -> bool:
        """Create a test API key via admin endpoint."""
        try:
            resp = requests.post(
                f"{self.backend_url}/v1/admin/external/keys",
                json={
                    "tier": "pro",
                    "scopes": ["read:rings", "read:drafts"],
                    "ip_allowlist": [],
                },
                headers={"Authorization": f"Bearer {self.admin_key}"},
                timeout=10,
            )
            if resp.status_code != 201:
                self.log("Create API Key", "FAIL", f"Status {resp.status_code}: {resp.text}")
                return False
            
            data = resp.json()
            self.api_key = data.get("secret")  # Full key returned only on creation
            key_id = data.get("key_id")
            
            if not self.api_key:
                self.log("Create API Key", "FAIL", "No secret in response")
                return False
            
            self.log("Create API Key", "PASS", f"Key: {key_id}, Type: {data.get('tier')}")
            return True
        except Exception as e:
            self.log("Create API Key", "FAIL", str(e))
            return False
    
    def test_external_me(self) -> bool:
        """Call /external/me to verify key works."""
        if not self.api_key:
            self.log("GET /external/me", "SKIP", "No API key created")
            return False
        
        try:
            resp = requests.get(
                f"{self.backend_url}/v1/external/me",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            
            ok = resp.status_code == 200
            if ok:
                data = resp.json()
                rate_limit = resp.headers.get("X-RateLimit-Limit", "?")
                self.log("GET /external/me", "PASS", f"RateLimit: {rate_limit}/hr")
            else:
                self.log("GET /external/me", "FAIL", f"Status {resp.status_code}: {resp.text}")
            
            return ok
        except Exception as e:
            self.log("GET /external/me", "FAIL", str(e))
            return False
    
    def test_create_webhook_subscription(self) -> bool:
        """Create webhook subscription pointing to sink."""
        if not self.api_key:
            self.log("Create Webhook Subscription", "SKIP", "No API key")
            return False
        
        try:
            resp = requests.post(
                f"{self.backend_url}/v1/external/webhooks",
                json={
                    "url": self.webhook_sink_url,
                    "events": ["draft.published", "enforcement.failed"],
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            
            if resp.status_code != 201:
                self.log("Create Webhook Subscription", "FAIL", f"Status {resp.status_code}: {resp.text}")
                return False
            
            data = resp.json()
            self.webhook_id = data.get("id")
            self.webhook_secret = data.get("secret")
            
            if not self.webhook_id or not self.webhook_secret:
                self.log("Create Webhook Subscription", "FAIL", "No webhook ID or secret in response")
                return False
            
            self.log("Create Webhook Subscription", "PASS", f"WebhookID: {self.webhook_id[:8]}...")
            return True
        except Exception as e:
            self.log("Create Webhook Subscription", "FAIL", str(e))
            return False
    
    def test_trigger_webhook_delivery(self) -> bool:
        """Trigger a webhook event and verify delivery to sink."""
        if not self.webhook_id or not self.webhook_secret:
            self.log("Trigger Webhook Event", "SKIP", "No webhook subscription")
            return False
        
        try:
            # Publish a test event
            resp = requests.post(
                f"{self.backend_url}/v1/external/events",
                json={
                    "event_type": "test.smoke",
                    "data": {
                        "test_id": "smoke-test-1",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            
            if resp.status_code not in [200, 202]:
                self.log("Trigger Webhook Event", "FAIL", f"Status {resp.status_code}: {resp.text}")
                return False
            
            event_id = resp.json().get("event_id")
            self.log("Trigger Webhook Event", "PASS", f"EventID: {event_id}")
            
            # Give worker time to deliver
            time.sleep(2)
            
            # Check sink for delivery
            try:
                sink_resp = requests.get(self.webhook_sink_url.replace("/webhook", "/deliveries"), timeout=5)
                if sink_resp.status_code == 200:
                    deliveries = sink_resp.json().get("deliveries", [])
                    if deliveries:
                        self.log("Webhook Delivery", "PASS", f"Received {len(deliveries)} delivery(ies)")
                        # Print last delivery
                        last = deliveries[-1]
                        print(f"    Event: {last.get('event_type')}")
                        print(f"    Verified: {last.get('signature_verified')}")
                        return True
                    else:
                        self.log("Webhook Delivery", "FAIL", "No deliveries in sink")
                        return False
                else:
                    self.log("Webhook Delivery", "SKIP", "Cannot access sink")
                    return False
            except Exception as e:
                self.log("Webhook Delivery", "SKIP", f"Sink unreachable: {e}")
                return False
        except Exception as e:
            self.log("Trigger Webhook Event", "FAIL", str(e))
            return False
    
    def run_all(self) -> bool:
        """Run complete smoke test suite."""
        print("\n🔥 EXTERNAL PLATFORM SMOKE TEST 🔥\n")
        
        tests = [
            ("Backend Health", self.test_admin_health),
            ("API Key Creation", self.test_create_api_key),
            ("External API Call", self.test_external_me),
            ("Webhook Subscription", self.test_create_webhook_subscription),
            ("Webhook Delivery", self.test_trigger_webhook_delivery),
        ]
        
        passed = 0
        failed = 0
        
        for name, test_fn in tests:
            try:
                result = test_fn()
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log(name, "ERROR", str(e))
                failed += 1
        
        print(f"\n📊 RESULTS: {passed} passed, {failed} failed\n")
        
        return failed == 0


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="External Platform Smoke Test")
    parser.add_argument("--backend-url", required=True, help="Backend URL (e.g., http://localhost:8000)")
    parser.add_argument("--admin-key", required=True, help="Admin API key")
    parser.add_argument("--webhook-sink", required=True, help="Webhook sink URL (e.g., http://localhost:9090/webhook)")
    
    args = parser.parse_args()
    
    tester = ExternalApiSmokeTest(args.backend_url, args.admin_key, args.webhook_sink)
    success = tester.run_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
