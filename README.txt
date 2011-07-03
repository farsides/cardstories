http://cardstories.org/

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


####################################
Setting up a development environment
####################################

The following are instructions to set up a contained development environment
on a recent installation of Ubuntu or Debian.

First, install the following packages.

$ sudo apt-get install python-twisted python-lxml python-django postfix

Note that Django must be version 1.2.5 or greater, otherwise things will break
in interesting ways.  If your distribution is too old (or too new), instead of
python-django install python-pip and then use it to install Django:

$ sudo apt-get install python-pip
$ sudo pip install Django==1.2.5

Now, make sure you are at the root of the cardstories checkout.  At this point,
create the default database structure for the website (an sqlite database will
be automatically created at /tmp/cardstories.website):

$ website/manage.py syncdb

On one terminal window, run the cardstories web service.  Under default
configuration, the following command assumes you have postfix configured
properly for relaying emails sent to 'localhost' (otherwise invitations won't
be sent out):

$ PYTHONPATH=.:etc/cardstories twistd --nodaemon cardstories \
	--static $(pwd)/static --port 5000 --interface 0.0.0.0 \
	--db /tmp/cardstories.sqlite \
	--plugins-dir plugins \
	--plugins-libdir /tmp \
	--plugins-confdir tests \
	--plugins 'djangoauth solo mail' \
	--plugins-pre-process 'djangoauth solo' \
	--plugins-post-process 'djangoauth'

On a second terminal window, still from the root of the checkout, run the
website development server, which by default binds to localhost and port 8000:
(Note: Django's default "manage.py runserver" does not work with the djangoauth
plugin because it can only handle one request at a time, so our manage.py has
been hacked to provide multithreaded goodness.)

$ website/manage.py runserver 0.0.0.0:8000

Now simply access http://localhost:8000/, and code away!

If for any reason you need to run the website dev server on a different host or
port, these files that must be modified accordingly, and the cardstories web
service restarted:

   * tests/djangoauth/djangoauth.xml
   * tests/mail/mail.xml

Finally, if the cardstories web service is not running on port 5000, make sure
to change the CARDSTORIES_HOST parameter here, and restart the website server:

   * website/settings.py


#################################
Deploying cardstories with Apache
#################################

In order to deploy cardstories with Apache, the following packages must be
installed:

$ sudo apt-get install python-twisted python-lxml python-django postfix \
	apache2 libapache2-mod-wsgi

From the root of your cardstories checkout, install cardstories to the default
locations with:

$ sudo python setup.py install

Then, from cardstories root, copy the apache configuration file to the proper
location on the file system, and enable it.  You may need to edit it depending
on your site characteristics (particularly the location of django's admin
media):

$ sudo cp website/apache/apache2.conf /etc/apache2/sites-available/cardstories
$ sudo a2ensite cardstories

Now enable the required apache mods, and restart the server:

$ a2enmod wsgi
$ a2enmod proxy_http
$ sudo /etc/init.d/apache2 restart

Finally, don't forget to create the default database for the website and run
the cardstories web service as described in the previous section.


##############
Usage examples
##############

To display the cardstories web service usage information:

$ PYTHONPATH=.:etc/cardstories twistd cardstories --help

To run the webservice without the mail plugin:

$ PYTHONPATH=.:etc/cardstories twistd --nodaemon cardstories \
	--static $(pwd)/static --port 5000 --interface 0.0.0.0 \
	--db /tmp/cardstories.sqlite \
	--plugins-dir plugins \
	--plugins-libdir /tmp \
	--plugins-confdir tests \
	--plugins 'djangoauth solo' \
	--plugins-pre-process 'auth solo' \
	--plugins-post-process auth

To check if the webservice replies, run the following (requires curl). The
following must return the {"win": {}, "games": [], "modified": 0} string:

$ curl --silent 'http://localhost:8000/resource?action=lobby&my=true&player_id=TEST&in_progress=yes'


######################
Packaging instructions
######################

To create a source distribution use:

$ v=1.0.5 ; python setup.py sdist --dist-dir .. ; mv ../cardstories-$v.tar.gz ../cardstories_$v.orig.tar.gz

To create the Debian GNU/Linux package use:

$ dpkg-buildpackage -S -uc -us


######################
Additional information
######################

As of Apr, 26th 2011 there are 321 LOC of JavaScript, 687 LOC of Python = 1008 LOC
As of Jun, 19th 2011 there are 473 LOC of JavaScript, 896 LOC of Python = 1369 LOC
