# Partner Onboarding Guide

**Status:** Active Phase 10.3+  
**Last Updated:** Dec 25, 2025  
**Audience:** Partners integrating OneRing External API into their applications

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [The Onboarding Wizard](#the-onboarding-wizard)
4. [Step-by-Step Walkthrough](#step-by-step-walkthrough)
5. [Common Issues](#common-issues)
6. [Support & FAQ](#support--faq)

---

## Overview

OneRing's **Partner Onboarding Wizard** streamlines the process of getting an external API key and webhook configured in minutes. The wizard guides partners through three essential steps:

1. **Create API Key** — Select scopes and tier, receive secret
2. **Test API** — Verify your key works with provided curl command
3. **Create Webhook** — Set up event delivery to your system

### What You'll Need

- **OneRing Account** — Signed up at https://onering.app
- **Basic Web Knowledge** — Ability to paste curl commands, understand webhooks
- **Production Environment** — Where you want to receive webhook events
- **~15 Minutes** — Time to complete the wizard

---

## Getting Started

### Access the Partner Console

1. Sign in to OneRing at https://onering.app
2. Navigate to **Partner Console** → **External API** section
3. Click **"Start Onboarding"** or **"Manage Keys & Webhooks"**

If you don't see the Partner Console, you may need to:
- Verify your account is marked as a **Partner** (contact support if unsure)
- Check that your organization is enabled for External API access

### Prerequisites

- ✅ Verified email address
- ✅ (Optional) Stripe verification for higher quotas
- ✅ HTTPS endpoint for webhooks (required in Step 3)

---

## The Onboarding Wizard

### Visual Layout

```
┌─────────────────────────────────────────┐
│  Step Indicator: 1/3 | 2/3 | 3/3        │
├─────────────────────────────────────────┤
│                                         │
│  Step 1: Create API Key                 │
│  ┌─────────────────────────────────┐   │
│  │ Scope: draft.read ☑             │   │
│  │ Scope: draft.write ☐            │   │
│  │                                 │   │
│  │ Tier: Starter (1M calls/month)  │   │
│  │                                 │   │
│  │ [Create Key] [Copy Secret]      │   │
│  └─────────────────────────────────┘   │
│                                         │
│ Created! Your key: ext_key_abc123       │
│                                         │
│ [Next] [Cancel]                         │
└─────────────────────────────────────────┘
```

### Step Progression

- **Automatic Advancement:** Each step auto-advances when complete
- **Manual Control:** Use [Next] button to proceed manually
- **Back Button:** Return to previous step to edit selections
- **Cancel:** Exit wizard at any time (progress saved)

---

## Step-by-Step Walkthrough

### Step 1: Create API Key

#### What Happens

You'll select the **scopes** your integration needs and choose a **tier** based on expected API volume.

#### Scopes Explained

| Scope | Allows | Use Case |
|-------|--------|----------|
| `draft.read` | Get draft details, list drafts | Analytics, fetching shared content |
| `draft.write` | Create, update, publish drafts | Building content on behalf of users |
| `webhook.manage` | Create/update/delete webhooks | Managing your own webhook subscriptions |
| `admin` | Full access (superuser only) | System integrations |

**Recommended for Creators:**
- ☑ `draft.read` — View creator content, analytics
- ☑ `draft.write` — Create content on their behalf
- ☐ `webhook.manage` — Let OneRing manage webhooks

**Recommended for Analytics Platforms:**
- ☑ `draft.read` — Fetch all drafts for analytics
- ☐ Other scopes

#### Tiers

| Tier | API Calls/Month | Webhooks | Price | Best For |
|------|-----------------|----------|-------|----------|
| **Starter** | 1M | Unlimited | Free | Testing, small integrations |
| **Growth** | 10M | Unlimited | $99/mo | Production, moderate volume |
| **Enterprise** | Custom | Unlimited | Custom | High volume, SLA required |

Click [Create Key] to generate your API key. Your secret will be displayed once — **copy it immediately** using [Copy Secret].

```
✓ Key Created!
ID: ext_key_abc123def456
Secret: onering_secret_xyz789... (shown once only)
Tier: Starter
Scopes: draft.read, draft.write
```

**Keep this secret safe!** Use environment variables in production, never commit to git.

---

### Step 2: Test API

#### What Happens

The wizard provides a curl command to test your newly created key.

#### Copy the Curl Command

The wizard displays:

```bash
curl -X GET https://api.onering.app/v1/external/me \
  -H "Authorization: Bearer ext_key_abc123def456"
```

Click **[Copy]** to copy this command to your clipboard.

#### Run in Your Terminal

Paste the command in your terminal (macOS, Linux, or Windows PowerShell):

```bash
# You should see a response like:
{
  "org_id": "org_partner_123",
  "tier": "starter",
  "api_calls_this_month": 0,
  "rate_limit_remaining": 1000000
}
```

#### Paste Response Back

Copy the response (just the JSON part) and paste it into the text field:

```json
{
  "org_id": "org_partner_123",
  "tier": "starter",
  "api_calls_this_month": 0,
  "rate_limit_remaining": 1000000
}
```

Click **[Verify]** to confirm the response is valid.

**Troubleshooting:**
- **"401 Unauthorized"** — Check your API key is correct
- **"Connection refused"** — Verify API endpoint is reachable
- **"Invalid JSON"** — Make sure you copied the full response including `{` and `}`

Once verified, you'll automatically advance to Step 3.

---

### Step 3: Create Webhook

#### What Happens

You'll register a webhook endpoint to receive real-time events from OneRing.

#### Select Events

Check the events you want to receive:

| Event | Fires When | Payload Contains |
|-------|-----------|-----------------|
| `draft.created` | New draft created | Draft ID, title, creator ID |
| `draft.published` | Draft goes live | Draft ID, publish timestamp, content |
| `draft.updated` | Draft content changes | Draft ID, diff (if available) |
| `draft.deleted` | Draft removed | Draft ID, deletion timestamp |
| `webhook_test` | Manual test from console | Test flag, timestamp |

**Recommended:** Start with `draft.published` and `webhook_test` for testing.

#### Provide Webhook URL

Enter your webhook endpoint (must be HTTPS and publicly accessible):

```
https://your-app.com/webhooks/onering
```

The webhook must:
- ✅ Accept POST requests with JSON body
- ✅ Verify the `X-OneRing-Signature` header (see [Consumer Guide](./EXTERNAL_API_CONSUMER_GUIDE.md#webhook-signature-verification))
- ✅ Return `200 OK` within 30 seconds
- ✅ Be publicly accessible (no localhost, staging ok with basic auth)

#### Webhook Secret

A secret is automatically generated. You'll need this to verify webhook signatures:

```
webhook_secret_abc123...
```

Click **[Copy]** to save it. Store this in your environment as `ONERING_WEBHOOK_SECRET`.

#### Create Webhook

Click **[Create Webhook]** to register.

**What Next?**
- The wizard completes
- You'll see a summary with your key, tier, and webhook URL
- Events will start flowing to your webhook endpoint
- Test with **[Send Test Event]** button in the partner console

---

## Common Issues

### "Key Created But Secret Not Showing"

**Solution:** Secrets are displayed only once. If you miss it, revoke the key and create a new one.

1. Go to **Manage Keys**
2. Find your key → Click **[⋯]** → **Revoke**
3. Create a new key and copy the secret immediately

### "Test API Returns 401 Unauthorized"

**Possible causes:**
1. **Wrong key ID** — You copied the key ID instead of the full key with prefix
   - Correct: `ext_key_abc123def456` (with `ext_key_` prefix)
   - Wrong: `abc123def456` (missing prefix)

2. **Key revoked** — Check if the key status shows "Active"
   - Go to **Manage Keys** and verify the key is not revoked

3. **Typo in command** — Re-copy the curl command from the wizard

### "Webhook Not Receiving Events"

**Checklist:**
1. ✓ Webhook URL is HTTPS (not HTTP)
2. ✓ URL is publicly accessible (test in browser, should show 404 or 200)
3. ✓ Endpoint accepts POST requests
4. ✓ Webhook status shows "Active" (not "Failed" or "Disabled")
5. ✓ No firewall blocking requests from `api.onering.app`

**Test the webhook:**
1. Go to **Manage Webhooks**
2. Click **[Send Test Event]**
3. Check your server logs for incoming POST request
4. If you see it, the webhook works — you may have a handler issue

**Still stuck?** See [Webhook Debugging](./EXTERNAL_API_CONSUMER_GUIDE.md#webhook-debugging) guide.

### "Rate Limit Exceeded (429)"

You've exceeded your tier's API call quota for the month.

**Solutions:**
1. **Switch to Growth tier** — Upgrade for 10M calls/month
2. **Upgrade to Enterprise** — Custom limits, contact sales@onering.app
3. **Wait until next month** — Quota resets on the 1st of each month

Your current usage is shown in the partner console:

```
This month: 1,024,531 / 1,000,000 calls
Resets: Jan 1, 2026
```

---

## Support & FAQ

### How do I rotate my API key?

1. Go to **Manage Keys**
2. Create a new key with same scopes
3. Update your app to use the new key
4. Once confirmed working, revoke the old key
5. Revoked keys stop working immediately

### Can I have multiple API keys?

Yes! Create one per environment (dev, staging, prod) for better security and troubleshooting.

### What if my webhook endpoint goes down?

OneRing will **retry for 7 days** with exponential backoff:
- 1st attempt: immediately
- 2nd attempt: 5 minutes later
- 3rd attempt: 30 minutes later
- ... (increasing intervals)
- Final attempt: 7 days later

After 7 days, events are discarded. You can manually re-fetch them via the API.

### Do I need to renew my API key?

No. API keys don't expire. You can keep using the same key indefinitely.

### How do I see my API usage?

In the partner console, navigate to **Usage & Billing**:

```
This month: 42,531 / 1,000,000 API calls (4.25%)
Tier: Starter (free, renews Jan 1)
Next billing date: N/A (free tier)
```

### What's the difference between Starter and Growth tier?

| Feature | Starter | Growth |
|---------|---------|--------|
| API Calls/Month | 1M | 10M |
| Price | Free | $99/mo |
| Support | Community | Priority Email |
| SLA | Best effort | 99.5% uptime |
| Webhook Delivery | Guaranteed 7 days | Guaranteed 30 days |

### Can I pay monthly instead of yearly?

Growth and Enterprise tiers are billed monthly, starting on the date you subscribe. No long-term commitment.

### Who do I contact for help?

- **Bug reports:** support@onering.app
- **Technical questions:** docs@onering.app
- **Sales inquiries:** sales@onering.app

**Response times:**
- Starter: 48 hours (best effort)
- Growth: 24 hours (SLA)
- Enterprise: 1 hour (SLA)

---

## Next Steps

1. ✅ Complete the onboarding wizard
2. ✅ Test your API key (Step 2)
3. ✅ Receive your first webhook event (Step 3)
4. ✅ Read the [API Consumer Guide](./EXTERNAL_API_CONSUMER_GUIDE.md) for full endpoint reference
5. ✅ Check out [Webhook Signing & Verification](./EXTERNAL_API_CONSUMER_GUIDE.md#webhook-signature-verification)
6. ✅ Review [Rate Limits & Quotas](./EXTERNAL_API_CONSUMER_GUIDE.md#rate-limits--quotas)

---

**Happy integrating! 🎉**

Have questions? Reach out to **support@onering.app** — we're here to help.
