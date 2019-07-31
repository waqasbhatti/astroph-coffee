# -*- coding: utf-8 -*-

'''This handles author-related operations.

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

import re
import csv

from tornado.escape import squeeze
from fuzzywuzzy import process
from sqlalchemy import select, update, func, distinct, insert, exc

from . import database


###############
## CONSTANTS ##
###############

# to get rid of parens in author names
# these are applied in order

# this should turn:
# "author1 (1, 2, & 3), author1 (1, 2, and 3), ((1) blah1, (2) blah2)"
# into:
# "author1, author2"
affil_regex1 = re.compile(r'\([0-9, &and]+\)')

# this gets rid of patterns like (blah)
affil_regex2 = re.compile(r'\([^)]*\)')

# this gets rid of patterns like (blah)
affil_regex3 = re.compile(r'\(\w+|\s+\)')

#######################
## UTILITY FUNCTIONS ##
#######################

def strip_affiliations(authorstr, subchar=','):
    '''
    This tries to strip author affils from authorstr.

    As far as I can test, I think this handles:

    author (affil, ...)
    author (1) ... ((1) affil, ....)
    author (1, 2) ... ((1) affil, ....)
    author (1 & 2) ... ((1) affil, ....)
    author (1 and 2) ... ((1) affil, ....)

    I don't think it can handle:

    author (1) ... (1) affil, ...

    but I haven't seen these in use (yet).

    '''

    initial = authorstr.replace("Authors: ","")
    initial = authorstr.replace('\n','')
    prelim = affil_regex1.sub(subchar, initial)
    intermed1 = affil_regex2.sub(subchar, prelim)
    intermed2 = affil_regex3.sub(subchar, intermed1)
    cleaned = intermed2.split(',')
    final = [squeeze(x.strip()) for x in cleaned if len(x) > 1]

    return final


###################################
## INSERTING AUTHORS INTO THE DB ##
###################################

def insert_local_authors(
        dbinfo,
        author_csv,
        dbkwargs=None,
        overwrite=True,
):
    '''
    This inserts local authors into the database.

    '''

    #
    # get the database
    #
    dbref, dbmeta = dbinfo
    if not dbkwargs:
        dbkwargs = {}
    if isinstance(dbref, str):
        engine, conn, meta = database.get_astrocoffee_db(dbref,
                                                         dbmeta,
                                                         **dbkwargs)
    else:
        engine, conn, meta = None, dbref, dbmeta
        meta.bind = conn

    #
    # actual work
    #

    local_authors = meta.tables['local_authors']

    # read the CSV
    csvfd = open(author_csv,'r')

    with conn.begin() as transaction:

        LOGINFO("Inserting local authors...")

        ins = insert(local_authors)

        csvreader = csv.DictReader(csvfd, fieldnames=('name','email'))

        for row in csvreader:

            try:
                conn.execute(ins, row)

            except exc.IntegrityError:

                transaction.rollback()

                if not overwrite:
                    LOGERROR(
                        "Author: %s with email: %s already exists "
                        "in the DB and overwrite=False. Skipping..."
                        % (row['name'], row['email'])
                    )
                    continue

                upd = update(local_authors).where(
                    local_authors.c.name == row['name']
                ).values(row)

                conn.execute(upd)
                LOGWARNING("Updated existing author info for author: %s" %
                           row['name'])
    #
    # at the end, shut down the DB
    #
    if engine:
        conn.close()
        meta.bind = None
        engine.dispose()

    #
    # close the CSV
    #
    csvfd.close()
