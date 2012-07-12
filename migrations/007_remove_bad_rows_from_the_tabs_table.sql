DELETE FROM tabs
  WHERE game_id NOT IN
    (SELECT id FROM games);
