CREATE TABLE IF NOT EXISTS event_logs (
    player_id INTEGER,
    game_id INTEGER,
    event_type SMALLINT,
    data TEXT,
    timestamp DATETIME
);
CREATE INDEX IF NOT EXISTS eventlogs_player_idx ON event_logs (player_id, timestamp);
CREATE INDEX IF NOT EXISTS eventlogs_game_idx ON event_logs (game_id, timestamp);