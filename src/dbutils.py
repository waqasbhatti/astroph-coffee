#!/usr/bin/env python

'''dbutils - Waqas Bhatti (wbhatti@astro.princeton.edu) - Jun 2014

Contains utilities for astroph-coffee server SQLite database manipulation.

'''

import sqlite3
import os
import os.path
import ConfigParser


CONF = ConfigParser.ConfigParser()
CONF.read('conf/astroph.conf')

DBPATH = CONF.get('sqlite3','database')

def opendb():
    '''
    This just opens a connection to the database and returns it + a cursor.

    '''

    db = sqlite3.connect(
        DBPATH, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES
        )

    cur = db.cursor()

    return db, cur



def insert_articles(arxivdict, database=None):
    '''This inserts all articles in an arxivdict created by
    arxivutils.grab_arxiv_papers into the astroph-coffee server database.

    '''

    # open the database if needed and get a cursor
    if not database:
        database, cursor = opendb()
        closedb = True
    else:
        cursor = database.cursor()
        closedb = False




    # at the end, close the cursor and DB connection
    if closedb:
        cursor.close()
        database.close()


def get_articles(date,
                 invoteorder=True,
                 minvotes=1,
                 localtop=True,
                 database=None):
    '''This grabs all articles from the database for the given date.

    '''

    # open the database if needed and get a cursor
    if not database:
        database, cursor = opendb()
        closedb = True
    else:
        cursor = database.cursor()
        closedb = False




    # at the end, close the cursor and DB connection
    if closedb:
        cursor.close()
        database.close()
