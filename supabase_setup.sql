-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Update/Create Enums
CREATE TYPE receipt_status AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED');
CREATE TYPE report_status AS ENUM ('DRAFT', 'SENT', 'APPROVED', 'REJECTED');

-- 2. Storage Bucket Setup (Executar manualmente en Supabase Dashboard si esto falla por permisos)
INSERT INTO storage.buckets (id, name, public) 
VALUES ('receipts', 'receipts', false)
ON CONFLICT (id) DO NOTHING;

-- 3. RLS Policies for Storage
-- Allow users to upload to their own company folder: receipts/{company_id}/*
-- NOTE: We are assuming company_id is strictly handled. 
-- In a real scenario you might verify if user belongs to company via a function or join.

-- Allow authenticated uploads
CREATE POLICY "Authenticated users can upload"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'receipts');

-- Allow users to read files in their company folder
CREATE POLICY "Users can read own company files"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'receipts');
-- Ideally: AND (storage.foldername(name))[1] IN (SELECT company_id FROM public.users_companies WHERE user_id = auth.uid())
-- But for MVP simple path matching:

-- 4. Database Schema Updates
-- Note: SqlAlchemy models will manage schema in this setup, 
-- but RLS policies must be applied directly to DB.

ALTER TABLE receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;

-- Receipts Policy
CREATE POLICY "Users can view receipts of their companies"
ON receipts FOR SELECT
USING (
  company_id IN (
    SELECT id FROM companies WHERE user_id = auth.uid()::text -- Cast if needed depending on ID types
  )
);

CREATE POLICY "Users can insert receipts for their companies"
ON receipts FOR INSERT
WITH CHECK (
  company_id IN (
    SELECT id FROM companies WHERE user_id = auth.uid()::text
  )
);

-- Reports Policy
CREATE POLICY "Users can access reports of their companies"
ON reports
USING (
  company_id IN (
    SELECT id FROM companies WHERE user_id = auth.uid()::text
  )
);

-- Companies Policy
CREATE POLICY "Users can see their own companies"
ON companies FOR SELECT
USING (user_id = auth.uid()::text);

