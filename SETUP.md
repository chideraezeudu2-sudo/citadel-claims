# Citadel Claims Backend Setup Guide

## What Was Built

Complete FastAPI backend for Citadel Claims SMS-first insurance estimating service.

### Project Structure
```
citadel-claims-backend/
├── main.py                     # FastAPI app entry point
├── requirements.txt            # All dependencies
├── .env                        # Environment variables (fill in your keys)
├── .gitignore
├── routers/
│   ├── sms.py                  # Telnyx webhook handler
│   ├── stripe_webhooks.py      # Stripe webhook handler
│   └── portal.py               # Magic link portal API
├── services/
│   ├── nlp.py                  # Groq + Gemini intent classifier
│   ├── ai_pipeline.py          # Gemini vision + transcription + estimate drafting
│   ├── pdf_generator.py        # WeasyPrint PDF builder
│   ├── sms_sender.py           # Outbound Telnyx SMS
│   ├── storage.py              # Supabase file storage
│   └── watchdog.py             # Free tier usage monitor + alerts
├── models/
│   └── schemas.py              # Pydantic models
└── utils/
    └── supabase_client.py      # Supabase connection
```

### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhook/sms` | Receives inbound SMS from Telnyx |
| POST | `/webhook/stripe` | Receives Stripe payment events |
| GET | `/portal/{token}` | Serves client portal data via magic link |
| POST | `/create-checkout-session` | Creates Stripe checkout session |
| GET | `/health` | Health check endpoint |
| GET | `/` | Root endpoint |

---

## Setup Instructions for Sam

### Step 1: Fill in Environment Variables

Edit the `.env` file with your actual API keys:

```env
# Telnyx (from telnyx.com)
TELNYX_API_KEY=your_telnyx_api_key
TELNYX_PUBLIC_KEY=your_telnyx_public_key
TELNYX_MESSAGING_PROFILE_ID=your_messaging_profile_id

# Groq (from console.groq.com)
GROQ_API_KEY=your_groq_api_key

# Google Gemini (from aistudio.google.com)
GEMINI_API_KEY=your_gemini_api_key

# Supabase (from supabase.com)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Stripe (from dashboard.stripe.com)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...

# App URLs (set after deployment)
BASE_URL=https://your-backend.onrender.com
PORTAL_BASE_URL=https://your-frontend.vercel.app
ALERT_EMAIL=your@email.com

# SendGrid (from sendgrid.com)
SENDGRID_API_KEY=your_sendgrid_api_key
```

### Step 2: Create Supabase Database Tables

Run this SQL in Supabase → SQL Editor:

```sql
-- Clients table
CREATE TABLE clients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone TEXT UNIQUE NOT NULL,
  email TEXT,
  name TEXT,
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  telnyx_number TEXT,
  portal_token TEXT UNIQUE DEFAULT gen_random_uuid()::TEXT,
  status TEXT DEFAULT 'active',
  claims_used_this_month INTEGER DEFAULT 0,
  billing_cycle_start DATE DEFAULT CURRENT_DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Claims table
CREATE TABLE claims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES clients(id),
  claim_type TEXT,
  status TEXT DEFAULT 'pending',
  voice_note_url TEXT,
  photo_urls TEXT[],
  transcript TEXT,
  estimate_draft TEXT,
  pdf_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- Usage tracking table
CREATE TABLE api_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service TEXT NOT NULL,
  tokens_used INTEGER DEFAULT 0,
  requests_used INTEGER DEFAULT 0,
  date DATE DEFAULT CURRENT_DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Inbound message log
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES clients(id),
  direction TEXT,
  body TEXT,
  media_urls TEXT[],
  telnyx_message_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Step 3: Create Supabase Storage Buckets

In Supabase Dashboard → Storage → New Bucket:
1. Create bucket `claim-media` (Public: true)
2. Create bucket `estimates` (Public: true)

### Step 4: Deploy to Render

1. Push code to GitHub
2. Go to render.com → New Web Service
3. Connect GitHub repo
4. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add all environment variables from `.env`
6. Deploy

### Step 5: Configure Webhooks

**Telnyx:**
1. Go to telnyx.com → Messaging → Messaging Profiles
2. Open your profile
3. Set Webhook URL to: `https://your-render-url.onrender.com/webhook/sms`
4. Set webhook API version to V2

**Stripe:**
1. Go to dashboard.stripe.com → Developers → Webhooks
2. Add endpoint: `https://your-render-url.onrender.com/webhook/stripe`
3. Select events: `checkout.session.completed`, `customer.subscription.deleted`
4. Copy signing secret → add as `STRIPE_WEBHOOK_SECRET`

### Step 6: Update BASE_URL

After Render deployment, update `.env`:
```env
BASE_URL=https://your-render-url.onrender.com
```

---

## Running Locally

```bash
cd citadel-claims-backend
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## Testing the System

1. Text your Telnyx number with "help" - should respond with instructions
2. Text with "status" - should show claim status
3. Text with "portal" - should return magic link
4. Submit photos + voice note - should process claim and return PDF

---

## Notes

- Updated from `google-generativeai` to `google-genai` for latest Gemini SDK
- Uses `gemini-2.0-flash` model for all AI operations
- Free tier watchdog sends alerts at 80% and 95% usage