Deployment instructions for mygpo
=================================


Dependencies
------------

When no version number is indicated, it is advisable to install the current
development version from the repository.

* Python (>= 2.6) or PyPy (tested with 2.0 beta1)
* [CouchDB](https://couchdb.apache.org/) (>= 1.2)


Basic setup
-----------

Here's how you start from scratch with a new mygpo install (assuming a
Ubuntu 12.04 x86 install, 'should work' with other versions/archs as well).

If you are on a Debian/Ubuntu system, do:

    sudo apt-get install erlang git python-pip python-dev libevent-dev
    sudo apt-get build-dep couchdb

    [ install couchdb 1.2.0 from source ]

For creating logo thumbnails, install libraries for the various image formats.
They are used by the pillow library.

    sudo apt-get install libjpeg-dev zlib1g-dev libpng12-dev

Select a cozy place for the mygpo sources and clone it:

    git clone git://github.com/gpodder/mygpo.git
    cd mygpo

Now install additional dependencies locally (you could also use virtualenv or
some other fancy stuff):

    pip install -r requirements.txt

That's it for the setup. Now to initialize the DB:

    cd mygpo
    python manage.py sync_couchdb
    python manage.py sync-design-docs

..and here we go:

    python manage.py runserver

Ok, so you need a user. This requires e-mails to be sent. If your machine is
configured to send e-mail, that should work out well. If not, you can use the
Django E-Mail File Backend to "send" mails to a local folder:

    mkdir inbox

Now, edit mygpo/settings_prod.py (or create it) and add the following lines:

    import os.path

    EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    EMAIL_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'inbox')


Accessing the dev server from other devices
-------------------------------------------

Sometimes you might want to access the server from another machine than
localhost. In that case, you have to pass an additional argument to the
runserver command of manage.py, like this:

    python manage.py runserver 0.0.0.0:8000

Beware, though, that this will expose the web service to your all networks
that your machine is connected to. Apply common sense and ideally use only
on trusted networks.


Installing database dumps (if you have any, that is)
----------------------------------------------------

As easy as..

    cd lib
    hg clone https://code.google.com/p/couchdb-python/
    cd couchdb-python
    zcat /path/to/your.dump.gz | python couchdb/tools/load.py \
                                        http://localhost:5984/mygpo

..when you have created a dump like this:

    python manage.py dump-sample --user=[username] | gzip > my.dump.gz

(where [username] is a specific user for which the data will be dumped)

Updating derived data
---------------------

Certain data in the database is only calculated when you
run special commands. This is usually done regularly on
a production server using cron. You can also run these
commands regularly on your development machine:

    cd mygpo
    python manage.py update-categories
    python manage.py update-toplist
    python manage.py update-episode-toplist

    python manage.py feed-downloader
    python manage.py feed-downloader <feed-url> [...]
    python manage.py feed-downloader --max <max-updates>
    python manage.py feed-downloader --random --max <max-updates>
    python manage.py feed-downloader --toplist --max <max-updates>
    python manage.py feed-downloader --update-new --max <max-updates>

or to only do a dry run (this won't do any web requests for feeds):

    python manage.py feed-downloader --list-only [other parameters]


Maintaining publisher relationships with user accounts
------------------------------------------------------

To set a user as publisher for a given feed URL, use:

    cd mygpo
    python manage.py make-publisher <username> <feed-url> [...]


Resetting the database ("start from scratch")
---------------------------------------------

Delete the database:

    curl -X DELETE http://127.0.0.1:5984/mygpo
    curl -X DELETE http://127.0.0.1:5984/mygpo_sessions

Recreate the design documents:

    cd mygpo
    python manage.py sync_couchdb
    python manage.py sync-design-docs


Additional details on couchDB
-----------------------------

A source distribution of CouchDB can be obtained from

   http://couchdb.apache.org/downloads.html

Build and installation instructions can be found at

   http://wiki.apache.org/couchdb/Installation

Here are some rough instructions on how to build CouchDB 1.2.0 from source
and setting it up with a local user account:

    (assuming you have downloaded and extracted the CouchDB 1.2.0 source)
    sudo apt-get build-dep couchdb
    export COUCHDB_HOME=~/pkg/apache-couchdb-1.2.0/
    ./configure --prefix=$COUCHDB_HOME
    make -j4 && make install
    sudo useradd -d $COUCHDB_HOME/var/lib/couchdb couchdb
    sudo chown -R couchdb: $COUCHDB_HOME
    sudo chown -R root:couchdb $COUCHDB_HOME/etc/couchdb
    sudo chmod 664 $COUCHDB_HOME/etc/couchdb/*.ini
    sudo chmod 775 $COUCHDB_HOME/etc/couchdb/*.d


If you want to avoid installing a CouchDB server yourself, you can use a free
CouchDB hosting service, for example from

   http://www.iriscouch.com/service

Please note, however, that hosted CouchDB services generally do not provide
security or authentication mechanisms, so this might only be useful for
development servers.

If you don't use a local database, you need to update the COUCHDB_DATABASES
setting (see the "Settings" section below).



Initializing an empty Database
------------------------------

To create the database, execute the following on the commandline

    curl -X PUT http://127.0.0.1:5984/mygpo

To initialize the views, execute from the mygpo directory

    python manage.py sync_couchdb


Importing a Dump
----------------

To import a CouchDB dump, execute the following from the commandline

    gunzip -c <dumpfile.couch.gz> | couchdb-load http://127.0.0.1:5984/mygpo




Settings
--------

Check the settings in mygpo/settings.py. If you want to change any settings,
add them to mygpo/settings_prod.py with the correct value. If you want to
avoid warning messages on startup, simply:

    touch mygpo/settings_prod.py



Web-Server
----------

Django comes with a development webservice which you can run from the mygpo
directory with

    python manage.py runserver

If you want to run a production server, check out

   https://docs.djangoproject.com/en/dev/howto/deployment/
