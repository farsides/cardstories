CREATE TABLE players (
    player_id INTEGER,
    score BIGINTEGER,
    levelups INTEGER
);
CREATE UNIQUE INDEX players_idx ON players (player_id);
CREATE TABLE player_cards (
    id INTEGER PRIMARY KEY,
    player_id INTEGER,
    card INTEGER,
    UNIQUE ("player_id", "card")
);
