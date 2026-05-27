-- Migration: 2026-05-27 — make target + direction optional on price_alerts.
--
-- A row with target=NULL means "watch-only" — the ticker gets included in
-- the scan universe (if auto_score=true) but no price-cross ping fires.
-- A row with target set works as a full price alert as before.
--
-- Paste into Supabase SQL editor.

ALTER TABLE price_alerts ALTER COLUMN target    DROP NOT NULL;
ALTER TABLE price_alerts ALTER COLUMN direction DROP NOT NULL;

-- Replace the old CHECK constraint that required direction IN ('above','below')
-- with one that ALSO allows NULL (for watch-only entries).
ALTER TABLE price_alerts DROP CONSTRAINT IF EXISTS price_alerts_direction_check;
ALTER TABLE price_alerts ADD  CONSTRAINT price_alerts_direction_check
  CHECK (direction IS NULL OR direction IN ('above', 'below'));
