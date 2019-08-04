# -*- coding: utf-8 -*-

'''This contains worker functions that wrap the backend fns for async operation.

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

import multiprocessing as mp

from .. import authors, arxiv


###################
## LOCAL AUTHORS ##
###################

def get_local_authors(include_affiliations=True):
    '''
    This talks to the backend database and gets a local author list.

    '''

    currproc = mp.current_process()
    conn, meta = currproc.connection, currproc.metadata

    local_authors = authors.get_local_authors(
        (conn, meta),
        include_affiliations=include_affiliations
    )

    author_list = list(local_authors.keys())
    return author_list, local_authors


###############################
## PAPER DISCUSSION ARCHIVES ##
###############################

def get_coffee_archive():
    '''
    This gets the full archive of papers.

    '''

    currproc = mp.current_process()
    conn, meta = currproc.connection, currproc.metadata

    paper_archive = arxiv.get_coffee_archive(
        (conn, meta),
        returndict=True
    )

    return paper_archive


#############################
## GETTING ARTICLE LISTING ##
#############################

def get_arxiv_listing(utcdate=None):
    '''
    This fetches the arxiv listing for given utcdate.

    If utcdate is None, gets the latest available utcdate's listings.

    '''

    currproc = mp.current_process()
    conn, meta = currproc.connection, currproc.metadata

    arxiv_listing = arxiv.get_arxiv_listing(
        (conn, meta),
        utcdate=utcdate
    )

    return arxiv_listing
