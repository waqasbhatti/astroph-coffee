# -*- coding: utf-8 -*-

'''This contains FTS5 search functions for coffeeserver.

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

import sqlite3


###################
## FTS FUNCTIONS ##
###################

def full_text_query(
        connection,
        query_string,
        columns,
        column_weights=None,
):
    '''This runs an FTS query.

    This requires an active SQLite DBAPI connection. Get this from the
    SQLAlchemy Connection object.

    '''

    # this is the query to run
    q = ("select {columnstr} "
         "from arxiv_fts "
         "join arxiv_listings on (arxiv_fts.rowid = arxiv.rowid) where "
         "arxiv_fts MATCH ? {query_string} "
         "order by bm25(arxiv_fits{relevance_weights})")
