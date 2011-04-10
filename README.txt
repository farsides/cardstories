Copyright (C) 2011 Xavier Antoviaque <xavier@antoviaque.org> (gameplay and specifications)
Copyright (C) 2011 David Blanchard <david@blanchard.name> (gameplay and specifications)
Copyright (C) 2011 tartarugafeliz <contact@tartarugafeliz.com> (artwork)
Copyright (C) 2011 Loic Dachary <loic@dachary.org> (software)

  A player (who we will call the author) creates a new game. 
  He chooses a card, picks a word or a sentence to describe it
  and invites players to participate.
  Each players is given seven cards and are required to pick
  one that best matches the author's sentence.
  Once enough players have chosen a card, the author displays all chosen
  cards and the players try to figure out which one is the author's.
  The author wins if at least one of the players guesses right, but not all
  of them do. The winners are the author and the players who guessed right. 
  If the author loses, all the other players win. 

# display usage
PYTHONPATH=.:etc/cardstories twistd --nodaemon cardstories --help
# exercise the webservice
PYTHONPATH=.:etc/cardstories twistd --nodaemon cardstories --port 4923 --db /tmp/cardstories.sqlite
# retrieve the list of URLs and their status
curl --silent http://localhost:4923/resource
# run locally with all features activated
PYTHONPATH=.:etc/cardstories twistd --nodaemon cardstories --interface 0.0.0.0 --port 49238 --static $(pwd)/static --db /tmp/cardstories.sqlite
