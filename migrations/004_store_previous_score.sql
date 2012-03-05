ALTER TABLE players ADD score_prev BIGINTEGER;
UPDATE players SET score_prev = score;
