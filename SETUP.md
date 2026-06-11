# Citadel Claims Backend Setup Guide

## What Was Built

Complete FastAPI backend + frontend for Citadel Claims SMS-first insurance estimating service. Both frontend and backend deployed on **Render**.

### Project Structure
```
citadel-claims-backend/
├── main.py                     # FastAPI app entry point
├── frontend/
│   └── index.html              # Landing page, portal, checkout UI
├── requirements.txt            # All dependencies
├── .env.example                # Environment variables template
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
| GET | `/` | Serves the landing/portal page |
| GET | `/success` | Success page after checkout |
| POST | `/webhook/sms` | Receives inbound SMS from Telnyx |
| POST | `/webhook/stripe` | Receives Stripe payment events |
| GET | `/portal/{token}` | Serves client portal data via magic link |
| POST | `/create-checkout-session` | Creates Stripe checkout session |
| GET | `/health` | Health check endpoint |

---

## Setup Instructions

### Step 1: Fill in Environment Variables

Create a `.env` file from the template:

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

### Step 4: Push to GitHub

```bash
cd citadel-claims-backend
git add .
git commit -m "Initial Citadel Claims backend"
git remote add origin https://github.com/YOUR_USERNAME/citadel-claims.git
git push -u origin master
```

### Step 5: Deploy to Render

1. Go to [render.com](https://render.com) → New Web Service
2. Connect your GitHub repo
3. Configure:
   - **Name**: `citadel-claims`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables from your `.env` file
5. Deploy

### Step 6: Configure Webhooks

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

### Step 7: Update BASE_URL

After Render deployment, update your `.env`:
```env
BASE_URL=https://your-render-url.onrender.com
```

Then push changes and redeploy.

---

## Running Locally

```bash
cd citadel-claims-backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Then visit `http://localhost:8000`

---

## Testing the System

1. Visit your Render URL - should show landing page
2. Fill out checkout form - should redirect to Stripe
3. Complete payment - should create client and send SMS
4. Text your Telnyx number with "help" - should respond with instructions
5. Submit photos + voice note - should process claim and return PDF

---

## Architecture Notes

- Both frontend (HTML/CSS/JS) and backend (FastAPI) deployed on **Render**
- Frontend is served by FastAPI from the `frontend/` directory
- All data stored in Supabase (Postgres + Storage)
- SMS via Telnyx API
- AI via Groq (primary) + Gemini (fallback)
- Payments via Stripe