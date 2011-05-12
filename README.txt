http://cardstori.es/

Copyright (C) 2010,2011 Xavier Antoviaque <xavier@antoviaque.org> (gameplay and specifications)
Copyright (C) 2010,2011 David Blanchard <david@blanchard.name> (gameplay and specifications)
Copyright (C) 2010,2011 tartarugafeliz <contact@tartarugafeliz.com> (artwork)
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
PYTHONPATH=.:etc/cardstories twistd cardstories --help
# run locally with all features activated
PYTHONPATH=.:etc/cardstories twistd --nodaemon cardstories --static $(pwd)/static --port 5000 --interface 0.0.0.0 --db /tmp/cardstories.sqlite --auth basic --auth-db /tmp/authcardstories.sqlite
# check if the webservice replies. The following must return the {} string
curl --silent http://localhost:4923/resource

To create a source distribution use:
v=1.0.3 ; python setup.py sdist --dist-dir .. ; mv ../cardstories-$v.tar.gz ../cardstories_$v.orig.tar.gz
To create the Debian GNU/Linux package use:
dpkg-buildpackage -S -uc -us

As of Apr, 26th 2011 there are 321 LOC of JavaScript, 687 LOC of Python = 1008 LOC
