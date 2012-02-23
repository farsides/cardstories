/* SQLite has no MODIFY COLUMN, so we need to recreate the table
   in order to change the default state to 'create' */

BEGIN TRANSACTION;

CREATE TEMPORARY TABLE games_backup_1 (
  id INTEGER PRIMARY KEY,
  owner_id INTEGER,
  players INTEGER DEFAULT 1,
  sentence TEXT,
  cards VARCHAR(43),
  board VARCHAR(6),
  state VARCHAR(8) DEFAULT 'invitation',
  created DATETIME,
  completed DATETIME
);

INSERT INTO games_backup_1
  SELECT id, owner_id, players, sentence, cards, board, state, created, completed
  FROM games;

DROP TABLE games;

CREATE TABLE games (
  id INTEGER PRIMARY KEY,
  owner_id INTEGER,
  players INTEGER DEFAULT 1,
  sentence TEXT,
  cards VARCHAR(43),
  board VARCHAR(6),
  state VARCHAR(8) DEFAULT 'create',
  created DATETIME,
  completed DATETIME
);

CREATE INDEX games_idx ON games (id);

INSERT INTO games
  SELECT id, owner_id, players, sentence, cards, board, state, created, completed
  FROM games_backup_1;

DROP TABLE games_backup_1;

COMMIT;