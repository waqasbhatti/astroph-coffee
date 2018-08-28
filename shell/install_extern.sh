#!/bin/bash

BINDIR=`readlink -e $1`

source $BINDIR/bin/activate

# install latest versions of needed packages
pip install pip -U
pip install tornado==4.5.2
pip install requests==2.18.4
pip install BeautifulSoup4==4.6.0
pip install selenium==3.7.0
pip install pytz
pip install itsdangerous==0.24
pip install geoip2==2.6.0
pip install py2-ipaddress==3.4.1

# for better local author matching
pip install python-levenshtein==0.12.0
pip install fuzzywuzzy==0.16.0

# for sorting and stuff
pip install numpy==1.13.3

cd pysqlite

echo "Building sqlite3 command shell..."

# build the sqlite3 command-line binary
# FIXME: think about putting in linenoise.h and linenoise.c here since things
# are painful without readline behavior
cc -O2 -I. -DSQLITE_THREADSAFE=0 -DSQLITE_ENABLE_FTS4 \
   -DSQLITE_ENABLE_FTS5 -DSQLITE_ENABLE_JSON1 \
   -DSQLITE_ENABLE_RTREE -DSQLITE_ENABLE_EXPLAIN_COMMENTS \
   -DHAVE_USLEEP shell.c sqlite3.c -ldl -lm -o $BINDIR/bin/sqlite3

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
-DSQLITE_TEMP_STORE=2 \
-O2 \
-fPIC" LIBS="-lm" python setup.py build_static

python setup.py install

cd -

deactivate
