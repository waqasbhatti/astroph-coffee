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
from pytz import utc


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


## INSERTING ARTICLES

def insert_articles(arxiv, database=None):
    '''
    This inserts all articles in an arxivdict created by
    arxivutils.grab_arxiv_papers into the astroph-coffee server database.

    '''

    # open the database if needed and get a cursor
    if not database:
        database, cursor = opendb()
        closedb = True
    else:
        cursor = database.cursor()
        closedb = False

    # make sure we know that the dt is in UTC
    arxiv_dt = arxiv['utc']
    if not arxiv_dt.tzinfo:
        arxiv_dt = arxiv_dt.replace(tzinfo=utc)


    papers = arxiv['papers']
    crosslists = arxiv['crosslists']

    query = ("insert into arxiv (utctime, utcdate, "
             "day_serial, title, article_type,"
             "arxiv_id, authors, comments, abstract, link, pdf, "
             "nvotes, voters, presenters, local_authors) values "
             "(?,?, ?,?,?, ?,?,?,?,?,?, ?,?,?,?)")

    try:

        for key in papers:

            print('inserting astronomy article %s: %s' %
                  (key, papers[key]['title']))

            params = (arxiv_dt,
                      arxiv_dt.date(),
                      key,
                      papers[key]['title'],
                      'astronomy',
                      papers[key]['arxiv'],
                      ','.join(papers[key]['authors']),
                      papers[key]['comments'],
                      papers[key]['abstract'],
                      'http://arxiv.org%s' % papers[key]['link'],
                      'http://arxiv.org%s' % papers[key]['pdf'],
                      0,
                      '',
                      '',
                      False)
            cursor.execute(query, params)

        for key in crosslists:

            print('inserting cross-list article %s: %s' %
                  (key, papers[key]['title']))

            params = (arxiv_dt,
                      arxiv_dt.date(),
                      key,
                      papers[key]['title'],
                      'crosslists',
                      papers[key]['arxiv'],
                      ','.join(papers[key]['authors']),
                      papers[key]['comments'],
                      papers[key]['abstract'],
                      'http://arxiv.org%s' % papers[key]['link'],
                      'http://arxiv.org%s' % papers[key]['pdf'],
                      0,
                      '',
                      '',
                      False)
            cursor.execute(query, params)

        database.commit()

    except Exception as e:

        print('could not insert articles into the DB, error was %s' % e)
        database.rollback()

    # at the end, close the cursor and DB connection
    if closedb:
        cursor.close()
        database.close()


## RETRIEVING ARTICLES

def get_articles(date,
                 invoteorder=True,
                 minvotes=1,
                 localtop=True,
                 database=None):
    '''
    This grabs all articles from the database for the given date.

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



## LOCAL AUTHORS

def find_local_authors(arxiv_date, database=None):
    '''
    This finds all local authors for all papers on the date arxiv_date.

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



## VOTERS AND PRESENTERS

def record_vote(arxiv_id, votername, vote, database=None):
    '''
    This records votes for a paper in the DB.

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



def modify_presenters(arxiv_id, presenter, action, database=None):
    '''
    This adds/removes presenters for a paper.

    action = 'add' -> adds person named presenter
    action = 'remove' -> removes person named presenter

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





