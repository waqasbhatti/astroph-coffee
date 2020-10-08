# -*- coding: utf-8 -*-

'''This contains functions to migrate older astroph-coffee databases to the new
version.

'''

#############
## LOGGING ##
#############

import logging
LOGGER = logging.getLogger(__name__)

LOGDEBUG = LOGGER.debug
LOGINFO = LOGGER.info
LOGWARNING = LOGGER.warning
LOGERROR = LOGGER.error
LOGEXCEPTION = LOGGER.exception


#############
## IMPORTS ##
#############

from io import StringIO
import sqlite3

from datetime import timedelta
from dateutil import parser
from sqlalchemy import select, update, insert, exc

from . import database, authors


#########################
## MIGRATION FUNCTIONS ##
#########################

def migrate_local_authors(old_dbfile,
                          new_dburl,
                          truncate=False,
                          overwrite=True):
    '''
    This migrates the local_authors table.

    '''

    oldconn = sqlite3.connect(old_dbfile)
    oldcur = oldconn.cursor()
    q = "select author, email from local_authors"
    oldcur.execute(q)
    oldrows = oldcur.fetchall()
    oldcur.close()
    oldconn.close()

    LOGINFO("Total authors to migrate: %s" % len(oldrows))

    strio = StringIO()
    for row in oldrows:
        strio.write("%s,%s,\n" % row)
    strio.seek(0)

    inserted = authors.insert_local_authors(
        (new_dburl, database.ASTROCOFFEE),
        strio,
        truncate=truncate,
        overwrite=overwrite
    )
    strio.close()

    return inserted


def migrate_articles(old_dbfile,
                     new_dburl,
                     overwrite=False):
    '''
    This migrates the arxiv table over to the new database.

    '''

    LOGINFO("Fetching articles to migrate...")

    oldconn = sqlite3.connect(old_dbfile)
    oldconn.row_factory = sqlite3.Row
    oldcur = oldconn.cursor()
    q = (
        "select utcdate, day_serial, title, article_type, arxiv_id, "
        "authors, comments, abstract, link, pdf, "
        "nvotes, voters, "
        "reservers, reserved, "
        "local_authors, local_author_indices, local_author_specaffils "
        "from arxiv"
    )
    oldcur.execute(q)
    oldrows = oldcur.fetchall()
    oldcur.close()
    oldconn.close()

    LOGINFO("Total articles to migrate: %s" % len(oldrows))

    engine, newconn, meta = database.get_astrocoffee_db(new_dburl)

    #
    # now go through all the rows
    #
    with newconn.begin() as transaction:

        LOGINFO("Migrating articles...")

        try:
            import tqdm
            rowiter = tqdm.tqdm(oldrows)
        except Exception:
            rowiter = oldrows

        for row in rowiter:

            utcdate = parser.parse(row['utcdate']).date()

            # handle the author list
            author_list = authors.strip_affiliations(row['authors'])
            author_json = {'list':author_list}

            # handle the article type
            if row['article_type'] == 'astronomy':
                article_type = 'newarticle'
            elif row['article_type'] == 'crosslists':
                article_type = 'crosslist'

            # handle the voters
            voter_info = {x:True for x in
                          row['voters'].split(',') if len(x) > 0}

            # handle the reservers
            if row['reservers'] is not None and len(row['reservers']) > 0:
                reserver_info = {'session_token':row['reservers'],
                                 'full_name':row['reservers']}
                reserved = True
                reserved_on = utcdate
                reserved_until = reserved_on + timedelta(days=3)
            else:
                reserver_info = None
                reserved = False
                reserved_on = None
                reserved_until = None

            # handle the local authors
            if row['local_authors']:

                mark_other_affil = (
                    row['local_author_specaffils'] is not None
                )
                mark_local = 'primary'

                if row['local_author_indices']:
                    indices = row['local_author_indices'].split(',')
                    indices = [int(x) for x in indices if len(x) > 0]
                else:
                    indices = []
                if row['local_author_specaffils']:
                    specaffil = row['local_author_specaffils'].split(',')
                    specaffil = [x for x in specaffil if len(x) > 0]
                else:
                    specaffil = []

                local_authors = {
                    'mark_other_affil':mark_other_affil,
                    'mark_local':mark_local,
                    'indices':indices,
                    'specaffil':specaffil
                }

            else:

                local_authors = None

            # generate the insert/update dict
            insert_dict = {
                'utcdate':utcdate,
                'day_serial':row['day_serial'],
                'title':row['title'],
                'article_type':article_type,
                'arxiv_id':row['arxiv_id'],
                'authors':author_json,
                'comments':row['comments'],
                'abstract':row['abstract'],
                'link':row['link'],
                'pdf':row['pdf'],
                'nvotes':row['nvotes'],
                'voter_info':voter_info,
                'reserved':reserved,
                'reserver_info':reserver_info,
                'reserved_on':reserved_on,
                'reserved_until':reserved_until,
                'local_authors':local_authors,
            }

            arxiv_listings = meta.tables['arxiv_listings']

            ins = insert(arxiv_listings)

            try:

                newconn.execute(ins, insert_dict)

            except exc.IntegrityError:

                transaction.rollback()

                if not overwrite:

                    LOGERROR("Article with ID: %s already exists! "
                             "Skipping..." % row['arxiv_id'])
                    continue

                # if overwrite is set, do the update
                upd = update(arxiv_listings).where(
                    arxiv_listings.c.arxiv_id == row['arxiv_id']
                ).values(insert_dict)
                newconn.execute(upd)

                LOGWARNING("Updated existing listing for article: %s" %
                           row['arxiv_id'])

            except Exception:
                raise

    #
    # at the end, shut down the DB
    #
    newconn.close()
    meta.bind = None
    engine.dispose()

    return True
