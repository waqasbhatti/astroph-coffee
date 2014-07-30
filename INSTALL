This file details how to install the astroph-coffee server. The server is mostly
self-contained, runs its own web-server listening to a port on the localhost
interface, and is meant to be used along with a frontend reverse-proxy (like
nginx). An example nginx .conf file is provided.


PREREQUISITES

You'll need the following already installed:

* sqlite3
* virtualenv
* nginx or Apache (if you want external access via reverse-proxy)

On a recent Linux distribution:

$ sudo yum install python-virtualenv sqlite3 [nginx or httpd] (Fedora/RHEL/CentOS)

or

$ sudo apt-get install python-virtualenv sqlite3 [nginx or apache2] (Debian/Ubuntu)

will do this for you.


INSTALLING THE ASTROPH-COFFEE SERVER

In the astroph-coffee directory:

$ make (or make install)

will make a virtualenv directory named "run" under the astroph-coffee directory
where the server will run from. The following directories will also be created:

* astroph-coffee/run/logs => logs go here
* astroph-coffee/run/pids => pids for the server processes go here
* astroph-coffee/run/data => the sqlite3 database for the server goes here

The Python dependencies will be automatically installed by pip. These include:

* tornado
* passlib
* requests
* BeautifulSoup4
* selenium
* pytz
* itsdangerous

Once the server is installed, you'll need to edit the
astroph-coffee/run/conf/astroph.conf file. In particular, you'll need to
generate the secret key used by the server for cookie signing and change the
values in the [times] and [places] sections to match your location.

You should also edit the astroph-coffee/run/static/templates/base.html file
starting at line 70 for your particular institution, department's name, URL, and
logo.


ADDING LOCAL AUTHORS

You should add local authors to the astroph-coffee server database to have these
automatically recognized on each nightly arxiv update. It's a good idea to use
the full name to make it easier to match names against authors in arXiv
listings. The astroph-coffee server uses the Python standard library
difflib.get_close_matches function to do the fuzzy string matching required. The
function that does this is tag_local_authors in src/arxivdb.py. You can tune the
match_threshold parameter for looser/tighter matching.

First, create a CSV file of the form:

Author Name One,authoremail1@astro.example.edu
Author Name Two,authoremail1@astro.example.edu
Author Name Two,authoremail1@astro.example.edu
.
.
.
etc.


Then, to add the authors to the astroph-coffee server database, use the
add_local_authors function in the src/webdb.py module, like so:

[user@machine ~]$ cd /path/to/astroph-coffee
[user@machine astroph-coffee]$ cd run
[user@machine astroph-coffee]$ source bin/activate
(run)[user@machine astroph-coffee]$ python
Python 2.7.3 (default, Feb 27 2014, 19:58:35)
>>> import webdb
>>> webdb.add_local_authors('/path/to/local-authors.csv')


RUNNING THE ASTROPH-COFFEE SERVER


Use the coffeeserver.sh shell script in the astroph-coffee/shell directory to
run the actual server:

Usage: coffeeserver.sh start </path/to/astroph-coffee> [debugflag] [server port]
       coffeeserver.sh stop
       coffeeserver.sh status

where: [debugflag] = 0 -> deployment mode, templates cached, no backtraces
       [debugflag] = 1 -> development mode, backtraces on errors,
                          live-reload on source change

      [server port] -> set server port to use, default is 5005

Then navigate to: http://localhost:[server port]/astroph-coffee. For external
access to the server, it's best to use a reverse-proxy like nginx. The file
astroph-coffee/src/conf/nginx-astroph-coffee.conf contains sample directives for
the nginx webserver to handle this configuration.

The astroph-coffee server relies on a nightly update of its arxiv listings
database. Use the update_arxiv.sh shell script for this task:

Usage: update_arxiv.sh </path/to/astroph-coffee>

A cronjob set up as follows:

25 20 * * 0,1,2,3,4 /path/to/astroph-coffee/shell/update_arxiv.sh \
/path/to/astroph-coffee > \
/path/to/astroph-coffee/run/logs/arxiv-auto-update.log 2>&1

will update the server database every Sunday through Thursday night at 20:25 US
Eastern time (new listings usually come out between 20:00 and 20:20).

The working SQLite database for the server will be in the
astroph-coffee/run/data/astroph.sqlite file. It's a good idea to back this up
frequently in case of disaster.
