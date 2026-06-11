-- Citadel Claims Database Setup
-- Run this in Supabase → SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Clients table
CREATE TABLE IF NOT EXISTS clients (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  phone TEXT UNIQUE NOT NULL,
  email TEXT,
  name TEXT,
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  telnyx_number TEXT,
  portal_token TEXT UNIQUE DEFAULT uuid_generate_v4()::TEXT,
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'suspended')),
  claims_used_this_month INTEGER DEFAULT 0,
  billing_cycle_start DATE DEFAULT CURRENT_DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Claims table
CREATE TABLE IF NOT EXISTS claims (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  claim_type TEXT,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'complete', 'failed')),
  voice_note_url TEXT,
  photo_urls TEXT[],
  transcript TEXT,
  estimate_draft TEXT,
  pdf_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  direction TEXT CHECK (direction IN ('inbound', 'outbound')),
  body TEXT,
  media_urls TEXT[],
  telnyx_message_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_clients_phone ON clients(phone);
CREATE INDEX IF NOT EXISTS idx_clients_portal_token ON clients(portal_token);
CREATE INDEX IF NOT EXISTS idx_clients_stripe_subscription ON clients(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_claims_client_id ON claims(client_id);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);
CREATE INDEX IF NOT EXISTS idx_messages_client_id ON messages(client_id);

-- Enable Row Level Security
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Create policies (service role can do everything, anon can only read own data by token)
DROP POLICY IF EXISTS "Service role can do anything" ON clients;
CREATE POLICY "Service role can do anything" ON clients
  FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service role can do anything" ON claims;
CREATE POLICY "Service role can do anything" ON claims
  FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service role can do anything" ON messages;
CREATE POLICY "Service role can do anything" ON messages
  FOR ALL USING (auth.role() = 'service_role');

-- Grant permissions
GRANT ALL ON clients TO service_role;
GRANT ALL ON claims TO service_role;
GRANT ALL ON messages TO service_role;
GRANT USAGE ON SCHEMA public TO anon;
GRANT USAGE ON SCHEMA public TO service_role;
GRANT ALL ON clients TO anon;
GRANT ALL ON claims TO anon;
GRANT ALL ON messages TO anon;

-- Verify tables created
SELECT 'Tables created successfully!' as status;
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';