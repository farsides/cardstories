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

To run the tests, you will also need the Mock package 
(http://www.voidspace.org.uk/python/mock/)

$ sudo pip install mock==0.7.2

Now, make sure you are at the root of the cardstories checkout.  At this point,
create the default database structure for the website (an sqlite database will
be automatically created at /tmp/cardstories.website):

$ website/manage.py syncdb

Note that for local Facebook development, you must also add an entry to
/etc/hosts that matches the domain name in your Django site configuration.  It
is recommended when running the above syncdb command to chose
"local.cardstories.org" as the domain name, and then to add a line in
/etc/hosts like the following:

127.0.0.1 local.cardstories.org

On one terminal window, run the cardstories web service.  Under default
configuration, the following command assumes you have postfix configured
properly for relaying emails sent to 'localhost' (otherwise invitations won't
be sent out):

$ PYTHONPATH=.:etc/cardstories twistd --nodaemon cardstories \
	--static $(pwd)/static --port 5000 --interface 0.0.0.0 \
	--db /tmp/cardstories.sqlite \
	--plugins-dir plugins \
	--plugins-libdir /tmp \
	--plugins-logdir log/ \
	--plugins-confdir tests \
	--plugins 'djangoauth chat mail' \
	--plugins-pre-process 'djangoauth chat'

On a second terminal window, still from the root of the checkout, run the
website development server, which by default binds to localhost and port 8000.
However, for local Facebook redirection to work (which you set up above in
/etc/hosts), you must run the server on port 80 as root:

$ sudo website/manage.py runserver 0.0.0.0:80

Now simply access http://local.cardstories.org/, and code away!

If for any reason you need to run the website dev server on a different host or
port, these files that must be modified accordingly, and the cardstories web
service restarted:

   * tests/djangoauth/djangoauth.xml
   * tests/mail/mail.xml

Finally, if the cardstories web service is not running on port 5000, make sure
to change the CARDSTORIES_HOST parameter here, and restart the website server:

   * website/settings.py


###########################
Enabling Open Web Analytics
###########################

To use OWA, first you must get it up and running somewhere.  To do so, follow
the installation steps here:

http://wiki.openwebanalytics.com/index.php?title=Installation

Once it's configured and running, for example at http://localhost:8080/, log in
and obtain your Site ID.  With this information in hand, start by setting the
correct values in website/settings.py:

$ vim website/settings.py
----------
OWA_ENABLE = True
OWA_URL = 'http://localhost:8080/'
OWA_SITE_ID = '<your_site_id>'
----------

Once this is done, all relevant page views should be logged.  Game state
changes will be artificially logged as page views with URLs in the following
format, where <skin_name> refers to an existing skin in the game.

http://local.cardstories.org/?skin=<skin_name>

You can then proceed to set up goals in OWA accordingly.


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

Don't forget to create the default database for the website and run the
cardstories web service as described in the previous section.

Finally, to future deployments, you can create a separate local_settings.py
containing just the stuff you want applied locally (such as Facebook app id,
OWA url, etc) in:

/usr/share/cardstories/website/local_settings.py

To disable specific email notifications, after deployment edit
/etc/cardstories/plugins/mail/mail.xml so that it contains only the "allow"
nodes you need (valid options are 'invite', 'pick', 'voting', 'vote',
'complete'):

<mail ...>
  <allow>invite</allow>
  <allow>vote</allow>
</mail>

If NO notifications are to be sent, create an empty allow node (for backward
compatibility, if there aren't any allow nodes, mail will be sent for all
events):

<mail ...>
  <allow></allow>
</mail>


##############
Usage examples
##############

To display the cardstories web service usage information:

$ PYTHONPATH=.:etc/cardstories twistd cardstories --help

To run the webservice without mail or djangoauth:

$ PYTHONPATH=.:etc/cardstories twistd --nodaemon cardstories \
	--static $(pwd)/static --port 5000 --interface 0.0.0.0 \
	--db /tmp/cardstories.sqlite \
	--plugins-dir plugins \
	--plugins-libdir /tmp \
	--plugins-confdir tests \
	--plugins-logdir log \
	--plugins 'auth chat' \
	--plugins-pre-process 'auth chat' \
	--plugins-post-process auth

To check if the webservice replies, run the following (requires curl). The
following must return the {"win": {}, "games": [], "modified": 0} string:

$ curl --silent 'http://localhost:5000/resource?action=lobby&my=true&player_id=TEST&in_progress=yes'


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
