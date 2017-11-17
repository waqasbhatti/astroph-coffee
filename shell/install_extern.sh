#!/bin/bash

BINDIR=`readlink -e $1`

source $BINDIR/bin/activate

# install latest versions of needed packages
pip install pip -U
pip install tornado -U
pip install requests -U
pip install BeautifulSoup4 -U
pip install selenium -U
pip install pytz -U
pip install itsdangerous -U
pip install geoip2 -U
pip install py2-ipaddress -U

cd pysqlite

# build the sqlite3 command-line binary
gcc -Os -I. -DSQLITE_THREADSAFE=0 -DSQLITE_ENABLE_FTS4 \
   -DSQLITE_ENABLE_FTS5 -DSQLITE_ENABLE_JSON1 \
   -DSQLITE_ENABLE_RTREE -DSQLITE_ENABLE_EXPLAIN_COMMENTS \
   -DHAVE_USLEEP -DHAVE_READLINE \
   shell.c sqlite3.c -ldl -lm -o $BINDIR/sqlite3

# build pysqlite using the sqlite3 amalgamation
CFLAGS="-DSQLITE_ENABLE_COLUMN_METADATA \
-DSQLITE_ENABLE_DBSTAT_VTAB \
-DSQLITE_ENABLE_FTS3 \
-DSQLITE_ENABLE_FTS3_PARENTHESIS \
-DSQLITE_ENABLE_FTS4 \
-DSQLITE_ENABLE_FTS5 \
-DSQLITE_ENABLE_JSON1 \
-DSQLITE_ENABLE_STAT4 \
-DSQLITE_ENABLE_UPDATE_DELETE_LIMIT \
-DSQLITE_SECURE_DELETE \
-DSQLITE_SOUNDEX \
-DSQLITE_TEMP_STORE=3 \
-O2 \
-fPIC" LIBS="-lm" python setup.py build_static

python setup.py install

cd -

deactivate
