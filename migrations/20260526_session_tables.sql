-- Migration: 2026-05-26 session — adds 4 tables for new signals and price alerts.
-- Paste this entire file into Supabase SQL editor (one shot, idempotent).
--
-- Tables created:
--   insider_cache       — SEC Form 4 cluster-buy signal (24h cache)
--   analyst_cache       — analyst revisions signal (24h cache)
--   weekly_trend_cache  — weekly trend signal (6h cache)
--   price_alerts        — "ping me when X hits $Y" alerts
--
-- Safe to re-run: all CREATE TABLE statements use IF NOT EXISTS.

-- ─────────────────────────────────────────────────────────────────────
-- Insider activity cache (SEC Form 4 cluster buys/sells via yfinance)
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS insider_cache (
  ticker     TEXT PRIMARY KEY,
  checked_at TIMESTAMPTZ NOT NULL,
  payload    JSONB NOT NULL
);

-- ─────────────────────────────────────────────────────────────────────
-- Analyst revisions cache (upgrades/downgrades via yfinance)
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analyst_cache (
  ticker     TEXT PRIMARY KEY,
  checked_at TIMESTAMPTZ NOT NULL,
  payload    JSONB NOT NULL
);

-- ─────────────────────────────────────────────────────────────────────
-- Weekly trend cache (multi-timeframe alignment via yfinance / resample)
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS weekly_trend_cache (
  ticker     TEXT PRIMARY KEY,
  checked_at TIMESTAMPTZ NOT NULL,
  payload    JSONB NOT NULL
);

-- ─────────────────────────────────────────────────────────────────────
-- Price alerts ("ping me when NVDA hits $200")
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS price_alerts (
  id          BIGSERIAL PRIMARY KEY,
  ticker      TEXT NOT NULL,
  target      NUMERIC NOT NULL,
  direction   TEXT NOT NULL CHECK (direction IN ('above', 'below')),
  note        TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  fired       BOOLEAN NOT NULL DEFAULT FALSE,
  fired_at    TIMESTAMPTZ,
  fired_price NUMERIC
);

-- Useful indexes (the active-alerts query filters on fired=false)
CREATE INDEX IF NOT EXISTS price_alerts_active_idx
  ON price_alerts (fired, ticker) WHERE fired = FALSE;

CREATE INDEX IF NOT EXISTS price_alerts_ticker_idx
  ON price_alerts (ticker);

-- ─────────────────────────────────────────────────────────────────────
-- Model drift check log (weekly calibration drift report)
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS model_drift_log (
  id         BIGSERIAL PRIMARY KEY,
  checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  total_rows INT,
  max_drift  NUMERIC,
  flagged    BOOLEAN,
  report     JSONB
);
