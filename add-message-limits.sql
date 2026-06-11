-- Add message limit columns to clients table
-- Run this in Supabase → SQL Editor

ALTER TABLE clients 
ADD COLUMN IF NOT EXISTS message_limit INTEGER DEFAULT 1000,
ADD COLUMN IF NOT EXISTS messages_used_this_month INTEGER DEFAULT 0;

-- Verify the columns were added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'clients' 
AND column_name IN ('message_limit', 'messages_used_this_month');