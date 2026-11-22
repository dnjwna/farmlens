-- Optional, recommended: database-level guarantee of one claim per
-- (policy, trigger type, weather day), even if two checks run at the same time.
-- Run once in Supabase -> SQL Editor.
CREATE UNIQUE INDEX IF NOT EXISTS uq_insurance_claim_policy_type_day
    ON insurance_claims (policy_id, trigger_type, weather_date);
