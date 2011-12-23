Bots plugin

#########################
Installation instructions
#########################

Install the required dependencies:

    $ sudo apt-get install python-nltk
    
Create five "normal" player accounts, one for each of the bots, and edit the configuration 
file with their player_ids:

    $ gvim ./plugins/bot/bot.xml
    
Bot avatar images are available in /static/css/images/avatars/bots 
    
Run the word lists generator to produce the data the bots will use to pick the cards.
The environment variables must match the ones passed to the webservice. You may also add it 
to your crontab to make sure they take advantage of new games)

    $ PYTHONPATH=. PLUGINS_CONFDIR=./tests DB=/tmp/cardstories.sqlite ./plugins/bot/buildwordsscores.py

If you don't have game data to feed the bots, a sample file is included:

    $ cp ./plugins/bot/cards_words_scores.json.sample ./tests/bot/cards_words_scores.json
    
Add the 'bot' plugin to the command-line used to start the webservice, and restart it:

    ... \
    --plugins 'auth chat bot' \
    ...
    