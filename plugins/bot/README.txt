Bots plugin

#########################
Installation instructions
#########################

Install the required dependencies:

    $ sudo apt-get install python-yaml python-numpy
    $ sudo pip install nltk

Download the maxent_treebank_pos_tagger:

    $ python

    Python 2.6.6 (r266:84292, Dec 26 2010, 22:31:48) 
    [GCC 4.4.5] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import nltk
    >>> nltk.download()
    NLTK Downloader
    ---------------------------------------------------------------------------
        d) Download   l) List    u) Update   c) Config   h) Help   q) Quit
    ---------------------------------------------------------------------------
    Downloader> d

    Download which package (l=list; x=cancel)?
      Identifier> maxent_treebank_pos_tagger
        Downloading package 'maxent_treebank_pos_tagger' to
            /var/www/nltk_data...
          Unzipping taggers/maxent_treebank_pos_tagger.zip.
    
Create five "normal" player accounts, one for each of the bots, and edit the configuration 
file with their player_ids:

    $ gvim ./tests/bot/bot.xml
    
Bot avatar images are available in /static/css/images/avatars/bots 
    
Run the word lists generator to produce the data the bots will use to pick the cards.
The environment variables must match the ones passed to the webservice. You may also add it 
to your crontab to make sure they take advantage of new games)

    $ PYTHONPATH=. PLUGINS_CONFDIR=./tests DB=/tmp/cardstories.sqlite ./plugins/bot/buildwordsscores.py

If you don't have game data to feed the bots, a sample file is included:

    $ cp ./plugins/bot/cards_words_scores.json.sample ./tests/bot/cards_words_scores.json
    
Add the 'bot' plugin to the command-line used to start the webservice, and restart it:

    ... \
    --plugins 'auth chat activity table mail bot' \
    --plugins-pre-process 'auth chat bot'
    ...
    
