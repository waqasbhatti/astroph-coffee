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


def phrase_query_paginated(querystr,
                           getcolumns,
                           sortcol='arxiv_id',
                           sortorder='desc',
                           pagestarter=None,
                           pagelimit=100,
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

    # add the sortcol to the query so we can paginate on it later
    if sortcol not in getcolumns:
        getcolumns.insert(0,sortcol)

    columnstr = ',' .join(['arxiv.%s' % x for x in getcolumns])

    queryparams = []

    # this does paging
    # pagestarter is the last element in the sortcol of the previous results
    # pageop is chosen based on sortorder: > if 'asc', < if 'desc'
    if pagestarter:

        if sortorder == 'asc':
            pageop = '>'
        else:
            pageop = '<'

        query = ('select {columns} from '
                 'arxiv_fts join arxiv on (arxiv_fts.docid = arxiv.rowid) '
                 'where arxiv_fts MATCH ? and '
                 'arxiv.{sortcol} {pageop} ? '
                 'order by arxiv_fts.{sortcol} {sortorder}')
        query = query.format(columns=columnstr,
                             sortcol=sortcol,
                             pageop=pageop,
                             pagestarter=pagestarter,
                             sortorder=sortorder)
        queryparams = (pagestarter, querystr)

    else:

        query = ('select {columns} from '
                 'arxiv_fts join arxiv on (arxiv_fts.docid = arxiv.rowid) '
                 'where arxiv_fts MATCH ? '
                 'order by arxiv_fts.{sortcol} {sortorder}')
        query = query.format(columns=columnstr,
                             sortcol=sortcol,
                             sortorder=sortorder)
        queryparams = (querystr,)

    # use page limit if necessary
    if pagelimit and pagelimit > 0:
        query = '%s limit %s' % (query, pagelimit)
    else:
        pagelimit = 100
        query = '%s limit %s' % (query, pagelimit)

    print(query, queryparams)

    cursor.execute(query, queryparams)
    rows = cursor.fetchall()

    nmatches = len(rows)
    if nmatches > 0:
        mcols = zip(*rows)
        results = {x:y for x,y in zip(getcolumns, mcols)}
    else:
        results = None

    # at the end, close the cursor and DB connection
    if closedb:
        cursor.close()
        database.close()

    return {'nmatches':len(rows),
            'results':results,
            'columns':getcolumns,
            'sortcol':sortcol,
            'sortorder':sortorder,
            'pagelimit':pagelimit}


def column_simple_query(querystr,
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
