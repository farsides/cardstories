CREATE TABLE IF NOT EXISTS tabs (
    player_id INTEGER,
    game_id INTEGER,
    created DATETIME
);
CREATE UNIQUE INDEX IF NOT EXISTS tabs_idx ON tabs (player_id, game_id);