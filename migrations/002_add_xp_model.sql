CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    score BIGINTEGER,
    levelups INTEGER
);

CREATE TABLE player_cards (
    id INTEGER PRIMARY KEY,
    player_id INTEGER,
    card INTEGER,
    UNIQUE ("player_id", "card")
);
