# -*- coding: utf-8 -*-

'''This contains functions to handle voting, reserving, and presenting the arxiv
listings

'''

#############
## LOGGING ##
#############

import logging
from astrocoffee import log_sub, log_fmt, log_date_fmt
LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    style=log_sub,
    format=log_fmt,
    datefmt=log_date_fmt,
)

LOGDEBUG = LOGGER.debug
LOGINFO = LOGGER.info
LOGWARNING = LOGGER.warning
LOGERROR = LOGGER.error
LOGEXCEPTION = LOGGER.exception


#############
## IMPORTS ##
#############

from datetime import datetime, date
from dateutil import parser
from sqlalchemy import select, update

from . import database


############
## VOTING ##
############

def record_vote(dbinfo,
                vote_type,
                voter_session_token,
                arxiv_id,
                dbkwargs=None):
    '''This votes on a paper.

    vote_type is {'up','down'}

    voter_session_token is the authnzerver session token of the voter. This will
    go into the voter_info JSON column.

    arxiv_id is the article being voted on.

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

    with conn.begin() as transaction:

        arxiv_listings = meta.tables['arxiv_listings']

        # check first
        sel = select([
            arxiv_listings.c.voter_info
        ]).select_from(arxiv_listings).where(
            arxiv_listings.c.arxiv_id == arxiv_id
        )

        res = conn.execute(sel)
        row = res.first()

        if row is None:

            updated = False
            LOGERROR(
                "Could not apply vote: %s for session token: %s to article: %s."
                "Article does not exist."
                % (vote_type, voter_session_token, arxiv_id)
            )

        else:

            # check if there's no recorded votes ever
            if row[0] is None:

                new_value = {voter_session_token: True}

            else:

                existing_votes = row[0]

                if (voter_session_token not in existing_votes and
                    vote_type == 'up'):

                    LOGWARNING(
                        "Voter session token: %s voting up on %s"
                        % (voter_session_token, arxiv_id)
                    )
                    existing_votes[voter_session_token] = True
                    nvote_add = 1

                elif (voter_session_token not in existing_votes and
                      vote_type == 'down'):

                    LOGWARNING(
                        "Voter session token: %s has never voted before on "
                        "%s, ignoring their downvote..."
                        % (voter_session_token, arxiv_id)
                    )
                    nvote_add = 0

                elif (voter_session_token in existing_votes and
                      vote_type == 'up'):

                    LOGWARNING(
                        "Voter session token: %s has already voted "
                        "up on %s, ignoring..." % (voter_session_token,
                                                   arxiv_id)
                    )
                    nvote_add = 0

                elif (voter_session_token in existing_votes and
                      vote_type == 'down'):

                    LOGWARNING(
                        "Voter session token: %s is removing their upvote "
                        "on %s" % (voter_session_token, arxiv_id)
                    )
                    nvote_add = -1
                    del existing_votes[voter_session_token]

                new_value = existing_votes
                print(new_value)

            upd = update(
                arxiv_listings
            ).where(
                arxiv_listings.c.arxiv_id == arxiv_id
            ).values({
                'nvotes':arxiv_listings.c.nvotes + nvote_add,
                'voter_info':new_value
            })

            try:

                res = conn.execute(upd)
                updated = res.rowcount == 1
                res.close()

            except Exception:

                transaction.rollback()

                LOGEXCEPTION(
                    "Could not apply vote: %s for "
                    "session token: %s to article: %s"
                    % (vote_type, voter_session_token, arxiv_id)
                )
                updated = False

    #
    # at the end, shut down the DB
    #
    if engine:
        conn.close()
        meta.bind = None
        engine.dispose()

    return updated


################
## PRESENTING ##
################

def record_presenter(dbinfo,
                     presenter_info,
                     arxiv_id,
                     dbkwargs=None):
    '''This adds/removes a presenter to a paper.

    presenter_info is a dict::

        {'session_token': authnzerver session token of the presenter,
         'full_name': full name of the presenter}

    If presenter_info is None, the presenter is removed from the paper.

    The full_name is taken either from the full_name field of a logged in user's
    session info, or is provided by the user when they indicate they want to
    present a paper. For the second option, anonymous users from the allowed
    CIDR values only can choose to reserver a paper (i.e. on-campus only).

    - Only one presenter is allowed per paper.
    - Papers with reservations can't be presented.

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
    with conn.begin() as transaction:

        arxiv_listings = meta.tables['arxiv_listings']

        # check first
        sel = select([
            arxiv_listings.c.presenter_info,
            arxiv_listings.c.reserved,
        ]).select_from(arxiv_listings).where(
            arxiv_listings.c.arxiv_id == arxiv_id
        )

        res = conn.execute(sel)
        row = res.first()

        if row is None:

            updated = False
            LOGERROR(
                "Could not set a presenter. "
                "Presenter info provided: %r for requested article: %s."
                "Article does not exist."
                % (presenter_info, arxiv_id)
            )

        elif row and row['reserved']:

            updated = False
            LOGERROR(
                "Could not set a new presenter. "
                "Presenter info provided: %r for requested article: %s."
                "This paper has been reserved for a future coffee meeting."
                % (presenter_info, arxiv_id)
            )

        else:

            existing_presenter = row[0]

            if existing_presenter is not None and presenter_info is not None:

                updated = False
                LOGERROR(
                    "Could not set a presenter. "
                    "Presenter info provided: %r for requested article: %s."
                    "There is an existing presenter for this paper."
                    % (presenter_info, arxiv_id)
                )

            else:

                if presenter_info is None:

                    upd = update(arxiv_listings).where(
                        arxiv_listings.c.arxiv_id == arxiv_id
                    ).values(
                        presenter_info=None
                    )

                    LOGWARNING("Removing existing presenter: %r for paper: %s"
                               % (existing_presenter, arxiv_id))

                else:

                    upd = update(arxiv_listings).where(
                        arxiv_listings.c.arxiv_id == arxiv_id
                    ).values(
                        presenter_info={
                            'session_token':presenter_info['session_token'],
                            'full_name':presenter_info['full_name'],
                        }
                    )

                    LOGWARNING("Adding new presenter: %r for paper: %s"
                               % (presenter_info, arxiv_id))
                try:

                    res = conn.execute(upd)
                    updated = res.rowcount == 1
                    res.close()

                except Exception:

                    transaction.rollback()

                    LOGEXCEPTION(
                        "Could not set a presenter. "
                        "Presenter info provided: %r for requested article: %s."
                        % (presenter_info, arxiv_id)
                    )

    #
    # at the end, shut down the DB
    #
    if engine:
        conn.close()
        meta.bind = None
        engine.dispose()

    return updated


##################
## RESERVATIONS ##
##################

def record_reservation(dbinfo,
                       reserver_info,
                       arxiv_id,
                       reserve_until=None,
                       dbkwargs=None):
    '''This adds/removes a reserver for a paper.

    reserver_info is a dict::

        {'session_token': authnzerver session token of the reserver,
         'full_name': full name of the reserver}

    If reserver_info is None, the reservation is removed from the paper.

    The full_name is taken either from the full_name field of a logged in user's
    session info, or is provided by the user when they indicate they want to
    reserve a paper. For the second option, anonymous users from the allowed
    CIDR values only can choose to reserver a paper (i.e. on-campus only).

    - Only one reserver is allowed per paper.
    - Papers with active presenters can't be reserved.

    '''

    if reserver_info is not None and reserve_until is None:
        LOGERROR("No expiry date for the reservation was provided.")
        return False

    utcdate_now = datetime.utcnow().date()

    if isinstance(reserve_until, str):
        reserve_until_utcdate = parser.parse(reserve_until).date()
    elif isinstance(reserve_until, date):
        reserve_until_utcdate = reserve_until
    else:
        reserve_until_utcdate = None

    if reserve_until_utcdate and reserve_until_utcdate < utcdate_now:
        LOGERROR("Reservations can't be in the past.")
        return False

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

    updated = False

    with conn.begin() as transaction:

        arxiv_listings = meta.tables['arxiv_listings']

        # check first
        sel = select([
            arxiv_listings.c.reserver_info,
            arxiv_listings.c.reserved,
            arxiv_listings.c.presenter_info,
        ]).select_from(arxiv_listings).where(
            arxiv_listings.c.arxiv_id == arxiv_id
        )

        res = conn.execute(sel)
        row = res.first()

        if row is None:

            updated = False
            LOGERROR(
                "Could not set a reserver. "
                "Reserver info provided: %r for requested article: %s."
                "Article does not exist."
                % (reserver_info, arxiv_id)
            )

        elif row and row['presenter_info'] is not None:

            updated = False
            LOGERROR(
                "Could not set a new reserver. "
                "Reserver info provided: %r for requested article: %s."
                "This paper has an active presenter for the "
                "next coffee meeting."
                % (reserver_info, arxiv_id)
            )

        else:

            existing_reserver = row['reserver_info']
            reservation_exists = row['reserved']

            if ((existing_reserver is not None or reservation_exists) and
                reserver_info is not None):

                updated = False
                LOGERROR(
                    "Could not set a new reserver. "
                    "Reserver info provided: %r for requested article: %s."
                    "There is an existing reservation for this paper."
                    % (reserver_info, arxiv_id)
                )

            else:

                if reserver_info is None:

                    upd = update(arxiv_listings).where(
                        arxiv_listings.c.arxiv_id == arxiv_id
                    ).values(
                        reserved=False,
                        reserver_info=None,
                        reserved_until=None,
                        reserved_on=None,
                    )

                    LOGWARNING("Removing existing reserver: %r for paper: %s"
                               % (existing_reserver, arxiv_id))

                else:

                    upd = update(arxiv_listings).where(
                        arxiv_listings.c.arxiv_id == arxiv_id
                    ).values(
                        reserved=True,
                        reserver_info={
                            'session_token':reserver_info['session_token'],
                            'full_name':reserver_info['full_name'],
                        },
                        reserved_on=utcdate_now,
                        reserved_until=reserve_until_utcdate
                    )

                    LOGWARNING(
                        "Adding new reserver: %r for paper: %s."
                        "Reserved on: %s, until: %s"
                        % (reserver_info, arxiv_id,
                           utcdate_now,
                           reserve_until_utcdate)
                    )

                try:

                    res = conn.execute(upd)
                    updated = res.rowcount == 1
                    res.close()

                except Exception:

                    transaction.rollback()

                    LOGEXCEPTION(
                        "Could not set a new reserver. "
                        "Reserver info provided: %r for requested article: %s."
                        % (reserver_info, arxiv_id)
                    )
                    updated = False

    #
    # at the end, shut down the DB
    #
    if engine:
        conn.close()
        meta.bind = None
        engine.dispose()

    return updated
