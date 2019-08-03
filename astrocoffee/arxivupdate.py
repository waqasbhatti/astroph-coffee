# -*- coding: utf-8 -*-

'''This handles various recurrence rules and periodic updates of the listings.

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

from datetime import datetime
from dateutil import tz, parser, rrule


###########################
## HANDLE VOTE/LIST MODE ##
###########################

DAYS_OF_WEEK = {
    "Monday":0,
    "Tuesday":1,
    "Wednesday":2,
    "Thursday":3,
    "Friday":4,
    "Saturday":5,
    "Sunday":6,
}


def voting_window_active(
        voting_start_localtime,
        voting_end_localtime,
        coffee_days,
        coffee_at_localtime,
        verbose=False,
        override_time=None,
):
    '''
    This returns a boolean indicating if we're in vote mode or not.

    '''

    # get the current local time
    our_tz = tz.gettz()

    if override_time is not None:
        now = parser.parse(
            override_time
        ).replace(tzinfo=our_tz)
    else:
        now = datetime.now(tz=our_tz)

    # check the voting start and end dts
    voting_start_dt = parser.parse(
        voting_start_localtime
    ).replace(tzinfo=our_tz)
    voting_end_dt = parser.parse(
        voting_end_localtime
    ).replace(tzinfo=our_tz)

    if verbose:
        LOGINFO("Now (local time): %s" % now)
        LOGINFO("Voting window (local time): %s to %s" % (voting_start_dt,
                                                          voting_end_dt))

    # check if we're in the voting window
    voting_start_utctime = voting_start_dt.astimezone(tz.UTC).timetz()
    voting_end_utctime = voting_end_dt.astimezone(tz.UTC).timetz()
    now_utcdt = now.astimezone(tz.UTC)
    now_utctime = now_utcdt.timetz()

    if verbose:
        LOGINFO("Time now (UTC): %s" % now_utctime)
        LOGINFO(
            "Voting window times (UTC): %s to %s" % (
                voting_start_utctime,
                voting_end_utctime
            )
        )

    # check if we're on the right weekday for voting
    now_weekday = now_utcdt.weekday()
    coffee_weekdays = [DAYS_OF_WEEK[x] for x in coffee_days]

    if verbose:
        LOGINFO("Weekday: %s" % now_weekday)

    if ((voting_start_utctime < now_utctime < voting_end_utctime) and
        (now_weekday in coffee_weekdays)):
        voting_mode = True
    else:
        voting_mode = False

    return voting_mode


def update_schedule(
        update_utc_times,
        update_utc_days,
):
    '''
    This figures out the recurrence rule for the periodic arxiv update.

    '''
