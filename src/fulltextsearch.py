#!/usr/bin/env python

'''
arxivdb - Waqas Bhatti (wbhatti@astro.princeton.edu) - Jun 2014

Contains utilities for astroph-coffee server SQLite database manipulation for
inserting/modifying arXiv papers.

'''

import sqlite3
import os
import os.path
import ConfigParser
from datetime import datetime, date, timedelta
from pytz import utc

from tornado.escape import squeeze


CONF = ConfigParser.ConfigParser()
CONF.read('conf/astroph.conf')

DBPATH = CONF.get('sqlite3','database')

# local imports
from arxivdb import opendb


def phrase_query(querystr,
                 getcolumns,
                 database=None):
    '''
    This just runs the verbatim query querystr on the full FTS table.

    Returns getcolumns. getcolumns is a list of strings with column names.

    '''

    # open the database if needed and get a cursor
    if not database:
        database, cursor = opendb()
        closedb = True
    else:
        cursor = database.cursor()
        closedb = False

    columnstr = ',' .join(getcolumns)
    query = 'select {columns} from arxiv_fts where arxiv_fts MATCH ?'
    query = query.format(columns=columnstr)

    cursor.execute(query, (querystr,))
    rows = cursor.fetchall()

    # at the end, close the cursor and DB connection
    if closedb:
        cursor.close()
        database.close()

    return rows


def column_query(querystr,
                 matchcolumn,
                 getcolumns,
                 database=None):
    '''
    This runs the MATCH querystr against oncolumn only and returns getcolumns.

    matchcolumn is a column in the arxiv_fts table to return.

    Returns getcolumns. getcolumns is a list of strings with column names.

    '''

    # open the database if needed and get a cursor
    if not database:
        database, cursor = opendb()
        closedb = True
    else:
        cursor = database.cursor()
        closedb = False

    columnstr = ',' .join(getcolumns)
    query = 'select {columns} from arxiv_fts where {matchcol} MATCH ?'
    query = query.format(columnstr=columnstr, matchcol=matchcolumn)

    cursor.execute(query, (querystr,))
    rows = cursor.fetchall()

    # at the end, close the cursor and DB connection
    if closedb:
        cursor.close()
        database.close()

    return rows
