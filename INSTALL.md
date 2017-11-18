This file details how to install the astroph-coffee server. The server is mostly
self-contained, runs its own web-server listening to a port on the localhost
interface, and is meant to be used along with a frontend reverse-proxy (like
nginx). An example nginx .conf file is provided.

The server uses an sqlite3 database to store everything. Most enterprise
distributions of Linux where this server is likely to be installed have an
sqlite3 library that is woefully out of date for some stuff we depend on (like
full-text search). Therefore, the server bundles the following packages:

- pysqlite from Gerhard Häring: https://pysqlite.readthedocs.io/en/latest/sqlite3.html
- a recent sqlite3 source (v3.21.0 as of this writing)  from Hipp, et al.: https://sqlite.org/releaselog/3_21_0.html

Together, these allow us to build an independent version of the Python sqlite3
bindings and use them in a virtualenv for everything. Since we'll be compiling
stuff, you'll need a C compiler.

## Prerequisites

You'll need the following already installed:

* a C compiler (tested with gcc 4.8.5, gcc 7.2.1, Apple clang XXXX)
* the virtualenv tool for Python
* nginx or Apache (if you want external access via reverse-proxy)
* rsync to incrementally copy stuff in `src` to the `run` directory

To get virtualenv if you don't have it:

On a recent Linux distribution:

```bash
$ sudo yum/dnf/apt-get install python-virtualenv
```

If that's not an option, try the easy_install tool:

```bash
$ easy_install virtualenv
```


## Installing the server

Clone this repository:

```bash
git clone https://github.com/waqasbhatti/astroph-coffee.git
```

Then, in the astroph-coffee directory:

```
$ make
```

This will make a virtualenv subdirectory named `run` under the astroph-coffee
directory where the server will run from. The following directories will also be
created:

* `astroph-coffee/run/logs` => logs go here
* `astroph-coffee/run/pids` => pids for the server processes go here
* `astroph-coffee/run/data` => the sqlite3 database for the server goes here

The Python dependencies will be automatically installed by pip. These include:

* tornado
* passlib
* requests
* BeautifulSoup4
* selenium
* pytz
* itsdangerous
* py2-ipaddress
* numpy

After this, the Makefile will compile a custom version of the sqlite3 shell;
this will be placed in `run/bin` and will be available preferably over any
system sqlite3 command while the virtualenv is active. Next, the Makefile will
compile pysqlite and install it to the virtualenv's Python `site-packages`
directory so it's available to import.


## Database

Finally, the Makefile will set up the working database for the server in
`run/data/astroph.sqlite`. It's a good idea to back this up frequently in case
of disaster. To do this:

```bash
[astroph-coffee/run]$ source bin/activate
(run) [astroph-coffee/run]$ sqlite3 data/astroph.sqlite
sqlite3> .output /path/to/backup/file.sqlite-dump-YYMMDD
sqlite3> .dump
sqlite3> .exit
```

Then to recover from disaster:

```bash
[astroph-coffee/run]$ source bin/activate

# re-import the tables
(run) [astroph-coffee/run]$ sqlite3 data/astroph.sqlite < /path/to/backup/file.sqlite-dump-YYMMDD

# force rebuild of the full-text search indices
(run) [astroph-coffee/run]$ sqlite3 data/astroph.sqlite < data/astroph-sqlite.sql
(run) [astroph-coffee/run]$ sqlite3 data/astroph.sqlite
sqlite3> insert into arxiv_fts(arxiv_fts) values ('rebuild');
sqlite3> .exit
```

## Config files

Once the server is installed, you'll need to edit the
`astroph-coffee/src/conf/astroph.conf` file. In particular, you'll need to
change the following settings:

```
secret = YOUR_SECRET_KEY_HERE

room = Example Room
building = Example Hall
department = Department of Astronomy
institution = Example University

admincontact = Admin Contact
adminemail = coffeeadmin@astro.institution.edu

# UTC times here; you'll have to change these a couple of times a year due
# to daylight savings time (sorry!)
voting_start = 00:45
voting_end = 14:28
coffee_time = 14:30

server_tz = America/New_York
allowed_countries = US
allowed_subdivisions = NJ, NY, PA

allowed_cidr = 128.0.0.0/8
edit_cidr = 128.0.0.0/8
admin_keys = secret_key_1, secret_key_2, secret_key_3

special_affil_tags = physics.xyz.edu, abc.edu, def.gov
special_affil_defs = Physics, Abc Dept, Def Lab
```

See the comments in the conf file for details. You should also edit the
`astroph-coffee/src/static/templates/base.html` file starting at line 70 for
your particular institution, department's name, URL, and logo.


## Updating the run directory

If you edit any python files, CSS files, conf files, or HTML files in `src/`,
make sure to update the `run` directory with newer versions before you start the
server. In the base `astroph-coffee` directory:

```bash
$ make update
```

This will copy over all of the changes to the `run` directory. It's often better
to make changes in `src`, commit them using git, then make update so there's a
record of what changed.


## Adding local authors

You should add local authors to the astroph-coffee server database to have these
automatically recognized on each nightly arxiv update. It's a good idea to use
the full name to make it easier to match names against authors in arXiv
listings. The astroph-coffee server uses the Python standard library
`difflib.get_close_matches` function to do the fuzzy string matching
required. The function that does this is `tag_local_authors` in
`src/arxivdb.py`. You can tune the default `match_threshold` kwarg for the
`insert_articles` function for looser/tighter matching.

To add a list of local authors, create a CSV file of the form:

```
Author Name One,authoremail1@astro.example.edu
Author Name Two,authoremail1@astro.example.edu
Author Name Two,authoremail1@astro.example.edu
.
.
.
etc.
```

You don't need to have the actual emails for people (this was meant for
notification functionality that hasn't materialized yet). For now, the domain
names in the emails are used as special affiliation markers. For example:

Everyone in your department has emails ending with astro.example.edu, but there
are some local people in an affiliated institute with emails ending with
@institute.edu who should be listed as local authors as well.

In this case, you set `special_affil_tags` in `src/conf/astroph.conf` to
institute.edu, and the corresponding `special_affil_defs` to Affilated
Institute. Then if these affiliated local people happen to have a paper show up,
the title in the day's listing will be tagged with [Affiliated Institute] to
make them easier to see.

After you've set up the CSV file as above, to add the authors to the
astroph-coffee server database, use the `add_local_authors` function in the
`astroph-coffee/src/webdb.py` module, like so:

```bash
[user@machine ~]$ cd /path/to/astroph-coffee
[user@machine astroph-coffee]$ cd run
[user@machine astroph-coffee]$ source bin/activate
(run)[user@machine astroph-coffee]$ python
Python 2.7.3 (default, Feb 27 2014, 19:58:35)
>>> import webdb
>>> webdb.add_local_authors('/path/to/local-authors.csv')
```


## Running the server

Use the coffeeserver.sh shell script in the `astroph-coffee/shell` directory to
run the actual server:

```
Usage: coffeeserver.sh start </path/to/astroph-coffee/directory> [debugflag] [server port]
       coffeeserver.sh stop
       coffeeserver.sh status
```

where:

```
[debugflag] = 0 -> deployment mode, templates cached, no backtraces
[debugflag] = 1 -> development mode, backtraces on errors,
                   live-reload on source change

[server port] -> set server port to use, default is 5005
```

Then navigate to: `http://localhost:[server port]/astroph-coffee`. For external
access to the server, it's best to use a reverse-proxy like nginx. The file
`astroph-coffee/src/conf/nginx-astroph-coffee.conf` contains sample directives
for the nginx webserver to handle this configuration.


## Updating the arxiv listings every night

The astroph-coffee server relies on a nightly update of its arxiv listings
database. Use the `astroph-coffee/shell/update_arxiv.sh` shell script for this task:

```
Usage: update_arxiv.sh </path/to/astroph-coffee>
```

A UNIX cronjob set up as follows (assuming US Eastern Time) will work well:

```
29 20 * * 0,2,3,4 /path/to/astroph-coffee/shell/update_arxiv.sh /path/to/astroph-coffee 2>&1
37 20 * * 1 /path/to/astroph-coffee/shell/update_arxiv.sh /path/to/astroph-coffee 2>&1

```

These will update the server database at 20:30 US EST on Sunday,
Tuesday--Thursday, but at 20:37 on Monday night because the arxiv usually
updates later on that night.

The working SQLite database for the server will be in the
`astroph-coffee/run/data/astroph.sqlite` file.


## Manual update of the arxiv listings

If the nightly automatic update doesn't work (e.g. arxiv updated super-late, or
something else broke), you'll have to do a manual update.

First, delete the old rows corresponding to next morning's listings:

```
[astroph-coffee/run]$ source bin/activate
(run) [astroph-coffee/run]$ sqlite3 data/astroph.sqlite

# here the date is tomorrow's date
sqlite3> delete from arxiv where utcdate = '20YY-MM-DD'
sqlite3> .exit
```

Next, run a manual update:
(run) [astroph-coffee/run]$ python

>>> import arxivutils, arxivdb

# download the HTML of tonight's astro-ph listing
>>> listing = arxivutils.arxiv_update()

# insert the articles into the DB and tag local authors automatically
# the match_threshold is used to set the strictness of local author matching
# smaller values are more relaxed, match_threshold ranges from 0.0 to 1.0.
# the default value is 0.93
>>> arxivdb.insert_articles(listing, match_threshold=X.XX)

>>> exit()
```


## Correcting arxiv listings

The most common problem you'll run into is the server tagging people incorrectly
as local authors or completely missing local authors that should've been tagged
as such. I still haven't figured out how to do this with > 70% accuracy (pull
requests are welcome). In the meantime, there are a couple of Python functions
that will help fix these problems.

```bash
[user@machine ~]$ cd /path/to/astroph-coffee
[user@machine astroph-coffee]$ cd run
[user@machine astroph-coffee]$ source bin/activate
(run)[user@machine astroph-coffee]$ python
```
Then in the python shell:

```python
>>> import arxivdb

# to untag a paper that's not actually a local author paper
>>> arxivdb.force_localauthor_untag('<arxiv id of the offending paper>')

# to retag a paper that was actually a local author paper,
# or if the server tagged the wrong people in the author list
# as the local authors
>>> arxivdb.force_localauthor_tag('<arxiv id of the offending paper>',
                                  [index_of_first_missing_author,
                                   index_of_second_missing_author, ...])

# an example where we missed a paper with local authors in the 1st, 3rd, and 6th
# positions in the author list
>>> arxivdb.force_localauthor_tag('arXiv:1711:01234', [0,2,5])

# to retag a paper that had an incorrect local special affiliation
>>> arxivdb.force_localauthor_tag('<arxiv id of the offending paper>',
                                  [index_of_first_author,
                                   index_of_second_author, ...],
                                  specaffils=['Affiliate1','Affiliate2', ...])
```
