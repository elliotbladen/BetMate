-- migration 024: add T10 State of Origin columns to tier2_performance

ALTER TABLE tier2_performance ADD COLUMN t10_handicap_delta   REAL    NOT NULL DEFAULT 0.0;
ALTER TABLE tier2_performance ADD COLUMN totals_T10           REAL    NOT NULL DEFAULT 0.0;
ALTER TABLE tier2_performance ADD COLUMN t10_home_origin_pts  REAL    NOT NULL DEFAULT 0.0;
ALTER TABLE tier2_performance ADD COLUMN t10_away_origin_pts  REAL    NOT NULL DEFAULT 0.0;
ALTER TABLE tier2_performance ADD COLUMN t10_game_number      INTEGER NOT NULL DEFAULT 0;
ALTER TABLE tier2_performance ADD COLUMN home_origin_outs     TEXT;
ALTER TABLE tier2_performance ADD COLUMN away_origin_outs     TEXT;
