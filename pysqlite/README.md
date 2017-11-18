This directory contains the pysqlite Python module and sqlite3.c, sqlite3.h, and
shell.c from the sqlite3 source. I've modified setup.py here to not use
pkg-config so it's forced to use the current directory when looking for sqlite3
source files.

pysqlite is under the BSD 3-clause license. sqlite3.c, sqlite3.h, and shell.c
are in the public domain.

## pysqlite

Python DB-API module for SQLite 3.

Online documentation can be found [here](https://pysqlite.readthedocs.org/en/latest/sqlite3.html).

You can get help from the community on the Google Group: https://groups.google.com/forum/#!forum/python-sqlite

## sqlite3

See https://sqlite.org. The current version used here is
[v3.21.0](https://sqlite.org/releaselog/3_21_0.html).
