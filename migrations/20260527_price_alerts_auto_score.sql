-- Migration: 2026-05-27 — add auto_score flag to price_alerts.
--
-- When TRUE (default), the ticker on this alert is also fed into the scan
-- universe so it gets scored alongside S&P 500 + watchlist on every cycle.
-- When FALSE, the alert only fires a price-cross Slack ping — no analysis.
--
-- Paste into Supabase SQL editor.

ALTER TABLE price_alerts
  ADD COLUMN IF NOT EXISTS auto_score BOOLEAN NOT NULL DEFAULT TRUE;
