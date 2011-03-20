The game includes a deck of cards.

    * A player (who we will call the author) creates a new game. 
          o He chooses a card,
          o picks a word or a sentence to describe it,
          o offers players to play the session 
    * the participant players choose a card in their own deck that matches the author's sentence
    * Once enough players have chosen the card, the author displays all chosen cards, and the players try to figure out which one is the author's
    * The author wins if at least one of his friends gesses right, but not all of them do. Then the winners are the author and the friends who guessed right. 

If the author loses, all the other players win. 

# display usage
PYTHONPATH=.:etc/cardstories twistd --nodaemon cardstories --help
# exercise the webservice without polling urls
PYTHONPATH=.:etc/cardstories twistd --nodaemon cardstories --port 4923 --db /tmp/cardstories.sqlite
# retrieve the list of URLs and their status
curl --silent http://localhost:4923/resource
# run locally with all features activated
PYTHONPATH=.:etc/cardstories twistd --nodaemon cardstories --interface 0.0.0.0 --port 49238 --static $(pwd)/static --db /tmp/cardstories.sqlite
