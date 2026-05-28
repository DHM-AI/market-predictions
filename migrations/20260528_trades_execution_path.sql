-- 2026-05-28  Add execution_path to trades
-- Tracks whether a trade was placed via:
--   "rule_confirmed" — score≥MIN_SCORE AND confidence≥Medium (both gates fired)
--   "model_bypass"   — score≥HIGH_SCORE_BYPASS (model alone qualified, Low conf)
--   ""               — blocked/closed rows (not applicable)
-- After 2+ weeks of data, compare win rates between the two paths.

ALTER TABLE trades
  ADD COLUMN IF NOT EXISTS execution_path TEXT DEFAULT '';
