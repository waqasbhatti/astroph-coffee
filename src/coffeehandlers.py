#!/usr/bin/env python

'''coffeehandlers.py - Waqas Bhatti (wbhatti@astro.princeton.edu) - Jul 2014

This contains the URL handlers for the astroph-coffee web-server.

'''

import os.path
import logging
import base64
import re

LOGGER = logging.getLogger(__name__)

from datetime import datetime, timedelta
from pytz import utc, timezone

import tornado.web
from tornado.escape import xhtml_escape, xhtml_unescape, url_unescape

import arxivdb
import webdb

######################
## USEFUL CONSTANTS ##
######################

ARCHIVEDATE_REGEX = re.compile(r'^(\d{4})(\d{2})(\d{2})$')
MONTH_NAMES = {x:datetime(year=2014,month=x,day=12)
               for x in range(1,13)}


######################
## USEFUL FUNCTIONS ##
######################

def msgencode(message, signer):
    '''This escapes a message, then base64 encodes it.

    Uses an itsdangerous.Signer instance provided as the signer arg to sign the
    message to protect against tampering.

    '''
    try:
        msg = base64.b64encode(signer.sign(xhtml_escape(message)))
        msg = msg.replace('=','*')
        return msg
    except Exception as e:
        return ''



def msgdecode(message, signer):
    '''This base64 decodes a message, then unescapes it.

    Uses an itsdangerous.Signer instance provided as the signer arg to verify
    the message to protect against tampering.

    '''
    try:
        msg = message.replace('*','=')
        decoded_message = base64.b64decode(msg)
        decoded_message = signer.unsign(decoded_message)
        return xhtml_unescape(decoded_message)
    except Exception as e:
        return ''



def group_arxiv_dates(dates, npapers, nlocal, nvoted):
    '''
    This takes a list of datetime.dates and the number of papers corresponding
    to each date and builds a nice dict out of it, allowing the following
    listing (in rev-chron order) to be made:

    YEAR X

    Month X:

    Date X --- <strong>YY<strong> papers

    .
    .
    .

    YEAR 1

    Month 1:

    Date 1 --- <strong>YY<strong> papers

    '''

    years, months = [], []

    for x in dates:
        years.append(x.year)
        months.append(x.month)

    unique_years = set(years)
    unique_months = set(months)

    yeardict = {}

    for year in unique_years:
        yeardict[year] = {}
        for month in unique_months:
            yeardict[year][MONTH_NAMES[month]] = [
                (x,y,z,w) for (x,y,z,w) in zip(dates, npapers, nlocal, nvoted)
                if (x.year == year and x.month == month)
                ]
        for month in yeardict[year].copy():
            if not yeardict[year][month]:
                del yeardict[year][month]

    return yeardict



##################
## URL HANDLERS ##
##################


class CoffeeHandler(tornado.web.RequestHandler):

    '''
    This handles all requests for /astroph-coffee and redirects based on
    time of day.

    '''


    def initialize(self,
                   database,
                   voting_start,
                   voting_end,
                   coffee_time,
                   server_tz,
                   signer,
                   room,
                   building,
                   department,
                   institution):
        '''
        Sets up the database.

        '''

        self.database = database
        self.voting_start = voting_start
        self.voting_end = voting_end
        self.coffee_time = coffee_time
        self.local_tz = timezone(server_tz)
        self.signer = signer
        self.room = room
        self.building = building
        self.department = department
        self.institution = institution


    def get(self):
        '''
        This handles GET requests.

        '''
        # handle a redirect with an attached flash message
        flash_message = self.get_argument('f', None)
        if flash_message:
            flashtext = msgdecode(flash_message, self.signer)
            LOGGER.warning('flash message: %s' % flashtext)
            flashbox = (
                '<div data-alert class="alert-box radius">%s'
                ' <a class="close">&times;</a></div>' %
                flashtext
                )
            flash_message = flashbox
        else:
            flash_message = ''


        # first, get the session token
        session_token = self.get_secure_cookie('coffee_session',
                                               max_age_days=30)
        ip_address = self.request.remote_ip
        client_header = self.request.headers['User-Agent'] or 'none'
        local_today = datetime.now(tz=utc).strftime('%Y-%m-%d %H:%M %Z')

        user_name = 'anonuser@%s' % ip_address
        new_user = True

        # check if we're in voting time-limits
        timenow = datetime.now(tz=utc).timetz()

        # check if this session_token corresponds to an existing user
        if session_token:

            sessioninfo = webdb.session_check(session_token,
                                              database=self.database)


            if sessioninfo[0]:

                user_name = sessioninfo[2]
                LOGGER.info('found session for %s, continuing with it' %
                            user_name)
                new_user = False

            elif sessioninfo[-1] != 'database_error':

                LOGGER.warning('unknown user, starting a new session for '
                               '%s, %s' % (ip_address, client_header))

                sessionok, token = webdb.anon_session_initiate(
                    ip_address,
                    client_header,
                    database=self.database
                )

                if sessionok and token:
                    self.set_secure_cookie('coffee_session',
                                           token,
                                           httponly=True)

                else:
                    LOGGER.error('could not set session cookie for %s, %s' %
                                 (ip_address, client_header))
                    self.set_status(500)
                    message = ("There was a database error "
                               "trying to look up user credentials.")

                    LOGGER.error('database error while looking up session for '
                                   '%s, %s' % (ip_address, client_header))

                    self.render("errorpage.html",
                                user_name=user_name,
                                local_today=local_today,
                                error_message=message,
                                flash_message=flash_message,
                                new_user=new_user)


            else:

                self.set_status(500)
                message = ("There was a database error "
                           "trying to look up user credentials.")

                LOGGER.error('database error while looking up session for '
                               '%s, %s' % (ip_address, client_header))

                self.render("errorpage.html",
                            user_name=user_name,
                            local_today=local_today,
                            error_message=message,
                            flash_message=flash_message,
                            new_user=new_user)


        # there's no existing user session
        else:

            if ('crawler' not in client_header.lower() and
                'bot' not in client_header.lower()):

                LOGGER.warning('unknown user, starting a new session for '
                               '%s, %s' % (ip_address, client_header))

                sessionok, token = webdb.anon_session_initiate(
                    ip_address,
                    client_header,
                    database=self.database
                    )

                if sessionok and token:
                    self.set_secure_cookie('coffee_session',
                                           token,
                                           httponly=True)
                else:
                    LOGGER.error('could not set session cookie for %s, %s' %
                                 (ip_address, client_header))
                    self.set_status(500)
                    message = ("There was a database error "
                               "trying to look up user credentials.")

                    LOGGER.error('database error while looking up session for '
                                 '%s, %s' % (ip_address, client_header))

                    self.render("errorpage.html",
                                user_name=user_name,
                                local_today=local_today,
                                error_message=message,
                                flash_message=flash_message,
                                new_user=new_user)



        # construct the current dt and use it to figure out the local-to-server
        # voting times
        dtnow = datetime.now(tz=utc)

        dtstart = dtnow.replace(hour=self.voting_start.hour,
                                minute=self.voting_start.minute,
                                second=0)
        local_start = dtstart.astimezone(self.local_tz)
        local_start = local_start.strftime('%H:%M %Z')

        dtend = dtnow.replace(hour=self.voting_end.hour,
                              minute=self.voting_end.minute,
                              second=0)
        local_end = dtend.astimezone(self.local_tz)
        local_end = local_end.strftime('%H:%M %Z')

        dtcoffee = dtnow.replace(hour=self.coffee_time.hour,
                                 minute=self.coffee_time.minute,
                                 second=0)
        local_coffee = dtcoffee.astimezone(self.local_tz)
        local_coffee = local_coffee.strftime('%H:%M %Z')


        utc_start = self.voting_start.strftime('%H:%M %Z')
        utc_end = self.voting_end.strftime('%H:%M %Z')
        utc_coffee = self.coffee_time.strftime('%H:%M %Z')

        self.render("index.html",
                    user_name=user_name,
                    local_today=local_today,
                    voting_localstart=local_start,
                    voting_localend=local_end,
                    voting_start=utc_start,
                    voting_end=utc_end,
                    coffeetime_local=local_coffee,
                    coffeetime_utc=utc_coffee,
                    flash_message=flash_message,
                    new_user=new_user,
                    coffee_room=self.room,
                    coffee_building=self.building,
                    coffee_department=self.department,
                    coffee_institution=self.institution)




class ArticleListHandler(tornado.web.RequestHandler):
    '''This handles all requests for the listing of selected articles and voting
    pages. Note: if nobody voted on anything, the default is to return all
    articles with local authors at the top.

    '''

    def initialize(self, database,
                   voting_start,
                   voting_end,
                   server_tz,
                   signer):
        '''
        Sets up the database.

        '''

        self.database = database
        self.voting_start = voting_start
        self.voting_end = voting_end
        self.server_tz = server_tz
        self.signer = signer


    def get(self):
        '''
        This handles GET requests.

        '''

        # handle a redirect with an attached flash message
        flash_message = self.get_argument('f', None)
        if flash_message:

            flashtext = msgdecode(flash_message, self.signer)
            LOGGER.warning('flash message: %s' % flashtext)
            flashbox = (
                '<div data-alert class="alert-box radius">%s'
                '<a href="#" class="close">&times;</a></div>' %
                flashtext
                )
            flash_message = flashbox
        else:
            flash_message = ''

        # first, get the session token
        session_token = self.get_secure_cookie('coffee_session',
                                               max_age_days=30)
        ip_address = self.request.remote_ip
        client_header = self.request.headers['User-Agent'] or 'none'

        local_today = datetime.now(tz=utc).strftime('%Y-%m-%d %H:%M %Z')
        todays_date = datetime.now(tz=utc).strftime('%A, %b %d %Y')
        todays_utcdate = datetime.now(tz=utc).strftime('%Y-%m-%d')
        todays_localdate = (
            datetime.now(tz=timezone(self.server_tz)).strftime('%Y-%m-%d')
        )
        todays_localdate_str = (
            datetime.now(tz=timezone(self.server_tz)).strftime('%A, %b %d %Y')
            )

        user_name = 'anonuser@%s' % ip_address
        new_user = True

        # check if this session_token corresponds to an existing user
        if session_token:

            sessioninfo = webdb.session_check(session_token,
                                               database=self.database)


            if sessioninfo[0]:

                user_name = sessioninfo[2]
                LOGGER.info('found session for %s, continuing with it' %
                            user_name)
                new_user = False

            elif sessioninfo[-1] != 'database_error':

                LOGGER.warning('unknown user, starting a new session for '
                               '%s, %s' % (ip_address, client_header))

                sessionok, token = webdb.anon_session_initiate(
                    ip_address,
                    client_header,
                    database=self.database
                )

                if sessionok and token:
                    self.set_secure_cookie('coffee_session',
                                           token,
                                           httponly=True)
                else:
                    LOGGER.error('could not set session cookie for %s, %s' %
                                 (ip_address, client_header))
                    self.set_status(500)
                    message = ("There was a database error "
                               "trying to look up user credentials.")

                    LOGGER.error('database error while looking up session for '
                                   '%s, %s' % (ip_address, client_header))

                    self.render("errorpage.html",
                                user_name=user_name,
                                local_today=local_today,
                                error_message=message,
                                flash_message=flash_message,
                                new_user=new_user)

            else:

                self.set_status(500)
                message = ("There was a database error "
                           "trying to look up user credentials.")

                LOGGER.error('database error while looking up session for '
                               '%s, %s' % (ip_address, client_header))

                self.render("errorpage.html",
                            user_name=user_name,
                            local_today=local_today,
                            error_message=message,
                            flash_message=flash_message,
                            new_user=new_user)


        # there's no existing user session
        else:

            if ('crawler' not in client_header.lower() and
                'bot' not in client_header.lower()):

                LOGGER.warning('unknown user, starting a new session for '
                               '%s, %s' % (ip_address, client_header))

                sessionok, token = webdb.anon_session_initiate(
                    ip_address,
                    client_header,
                    database=self.database
                    )

                if sessionok and token:
                    self.set_secure_cookie('coffee_session',
                                           token,
                                           httponly=True)
                else:
                    LOGGER.error('could not set session cookie for %s, %s' %
                                 (ip_address, client_header))
                    self.set_status(500)
                    message = ("There was a database error "
                               "trying to look up user credentials.")

                    LOGGER.error('database error while looking up session for '
                                 '%s, %s' % (ip_address, client_header))

                    self.render("errorpage.html",
                                user_name=user_name,
                                local_today=local_today,
                                error_message=message,
                                flash_message=flash_message,
                                new_user=new_user)



        ############################
        ## SERVE THE PAGE REQUEST ##
        ############################

        # check if we're in voting time-limits
        timenow = datetime.now(tz=utc).timetz()

        # if we are within the time limits, then show the voting page
        if (self.voting_start < timenow < self.voting_end):

            # get the articles for today
            (local_articles, voted_articles,
             other_articles, reserved_articles) = (
                 arxivdb.get_articles_for_voting(database=self.database)
            )

            # if today's papers aren't ready yet, redirect to the papers display
            if not local_articles and not voted_articles and not other_articles:

                LOGGER.warning('no papers for today yet, '
                               'redirecting to previous day papers')

                (latestdate, local_articles, flagged_local_authors,
                 voted_articles, other_articles, reserved_articles) = (
                     arxivdb.get_articles_for_listing(
                         database=self.database
                     )
                )
                todays_date = datetime.strptime(latestdate,
                                                '%Y-%m-%d').strftime('%A, %b %d %Y')

                flash_message = (
                    "<div data-alert class=\"alert-box radius\">"
                    "Papers for today haven't been imported yet. "
                    "Here are the most recent papers. "
                    "Please wait a few minutes and try again."
                    "<a href=\"#\" class=\"close\">&times;</a></div>"
                )

                # show the listing page
                self.render("listing.html",
                            user_name=user_name,
                            local_today=local_today,
                            todays_date=todays_date,
                            local_articles=local_articles,
                            flagged_local_authors=flagged_local_authors,
                            voted_articles=voted_articles,
                            other_articles=other_articles,
                            reserved_articles=reserved_articles,
                            flash_message=flash_message,
                            new_user=new_user)

            # if today's papers are ready, show them and ask for votes
            else:

                # get this user's votes
                user_articles = arxivdb.get_user_votes(todays_utcdate,
                                                       user_name,
                                                       database=self.database)
                user_reserved = arxivdb.get_user_reservations(
                    todays_utcdate,
                    user_name,
                    database=self.database
                )
                LOGGER.info('user has votes on: %s, has reservations on: %s'
                            % (user_articles, user_reserved))

                # show the listing page
                self.render("voting.html",
                            user_name=user_name,
                            local_today=local_today,
                            todays_date=todays_date,
                            local_articles=local_articles,
                            voted_articles=voted_articles,
                            other_articles=other_articles,
                            reserved_articles=reserved_articles,
                            flash_message=flash_message,
                            new_user=new_user,
                            user_articles=user_articles,
                            user_reserved=user_reserved)

        # otherwise, show the article list
        else:

            # get the articles for today
            (latestdate, local_articles, flagged_local_authors,
             voted_articles, other_articles, reserved_articles) = (
                 arxivdb.get_articles_for_listing(utcdate=todays_utcdate,
                                                  database=self.database)
            )

            # if today's papers aren't ready yet, show latest papers
            if not local_articles and not voted_articles and not other_articles:

                (latestdate, local_articles,
                 voted_articles, other_articles, reserved_articles) = (
                     arxivdb.get_articles_for_listing(
                         database=self.database
                     )
                )
                todays_date = datetime.strptime(latestdate,
                                                '%Y-%m-%d').strftime('%A, %b %d %Y')

                flash_message = (
                    "<div data-alert class=\"alert-box radius\">"
                    "Papers for today haven't been imported yet. "
                    "Here are the most recent papers. "
                    "Please wait a few minutes and try again."
                    "<a href=\"#\" class=\"close\">&times;</a></div>"
                )


            # show the listing page
            self.render("listing.html",
                        user_name=user_name,
                        local_today=local_today,
                        todays_date=todays_date,
                        local_articles=local_articles,
                        flagged_local_author=flagged_local_authors,
                        voted_articles=voted_articles,
                        other_articles=other_articles,
                        reserved_articles=reserved_articles,
                        flash_message=flash_message,
                        new_user=new_user)



class ReservationHandler(tornado.web.RequestHandler):
    '''
    This handles all requests for the voting page.

    '''

    def initialize(self,
                   database,
                   voting_start,
                   voting_end,
                   debug,
                   signer,
                   geofence,
                   countries,
                   regions):
        '''
        Sets up the database.

        '''

        self.database = database
        self.voting_start = voting_start
        self.voting_end = voting_end
        self.debug = debug
        self.signer = signer
        self.geofence = geofence
        self.countries = countries
        self.regions = regions


    def post(self):
        '''
        This handles a POST request for a paper reservation.

        '''

        arxivid = self.get_argument('arxivid', None)
        reservetype = self.get_argument('reservetype', None)

        session_token = self.get_secure_cookie('coffee_session',
                                               max_age_days=30)

        sessioninfo = webdb.session_check(session_token,
                                          database=self.database)
        user_name = sessioninfo[2]
        todays_utcdate = datetime.now(tz=utc).strftime('%Y-%m-%d')

        user_ip = self.request.remote_ip

        # if we're asked to geofence, then do so
        # (unless the request came from INSIDE the building)
        # FIXME: add exceptions for private network IPv4 addresses
        geolocked = False

        if self.geofence and user_ip != '127.0.0.1':

            try:
                geoip = self.geofence.city(user_ip)

                if (geoip.country.iso_code in self.countries and
                    geoip.subdivisions.most_specific.iso_code
                    in self.regions):
                    LOGGER.info('geofencing ok: '
                                'reservation request '
                                'from inside allowed regions')

                else:
                    LOGGER.warning(
                        'geofencing activated: '
                        'vote request from %s '
                        'is outside allowed regions' %
                        ('%s-%s' % (
                            geoip.country.iso_code,
                            geoip.subdivisions.most_specific.iso_code
                            ))
                        )
                    message = ("Sorry, you're trying to vote "
                               "from an IP address that is "
                               "blocked from voting.")

                    jsondict = {'status':'failed',
                                'message':message,
                                'results':None}
                    geolocked = True

                    self.write(jsondict)
                    self.finish()


            # fail deadly
            except Exception as e:
                LOGGER.exception('geofencing failed for IP %s, '
                                 'blocking request.' % user_ip)

                message = ("Sorry, you're trying to vote "
                           "from an IP address that is "
                           "blocked from voting.")

                jsondict = {'status':'failed',
                            'message':message,
                            'results':None}
                geolocked = True

                self.write(jsondict)
                self.finish()

        #############################
        ## PROCESS THE RESERVATION ##
        #############################

        # check if we're in voting time-limits
        timenow = datetime.now(tz=utc).timetz()

        # if we are within the time limits, then allow the voting POST request
        if (self.voting_start < timenow < self.voting_end):
            in_votetime = True
        else:
            in_votetime = False

        # if all things are satisfied, then process the reserve request
        if (arxivid and
            reservetype and
            sessioninfo[0] and
            (not geolocked) and
            in_votetime):

            arxivid = xhtml_escape(arxivid)
            reservetype = xhtml_escape(reservetype)

            LOGGER.info('user: %s, reserving: %s, on: %s' % (user_name,
                                                             reservetype,
                                                             arxivid))

            if 'arXiv:' not in arxivid or reservetype not in ('reserve',
                                                              'release'):

                message = ("Your paper reservation request "
                           "used invalid arguments "
                           "and has been discarded.")

                jsondict = {'status':'failed',
                            'message':message,
                            'results':None}
                self.write(jsondict)
                self.finish()

            else:

                # first, check how many reservations this user has
                user_reservations = arxivdb.get_user_reservations(
                    todays_utcdate,
                    user_name,
                    database=self.database
                )

                # make sure it's less than 5 or we're not adding another
                # reservation
                if len(user_reservations) < 5 or reservetype != 'reserve':

                    reserve_outcome = arxivdb.record_reservation(
                        arxivid,
                        user_name,
                        reservetype,
                        database=self.database
                    )

                    if reserve_outcome is False or None:

                        message = ("That article doesn't exist, "
                                   "and your reservation "
                                   "has been discarded.")

                        jsondict = {'status':'failed',
                                    'message':message,
                                    'results':None}
                        self.write(jsondict)
                        self.finish()

                    else:

                        if (reserve_outcome[0] == 1 and
                            reserve_outcome[1] == user_name):

                            message = ("Reservation successfully recorded for %s"
                                       % arxivid)

                            jsondict = {'status':'success',
                                        'message':message,
                                        'results':{'reserved':reserve_outcome[0]}}

                        elif (reserve_outcome[0] == 1 and
                              reserve_outcome[1] != user_name):

                            message = ("Someeone else already reserved that paper!")

                            jsondict = {'status':'failed',
                                        'message':message,
                                        'results':{'reserved':reserve_outcome[0]}}

                        elif (reserve_outcome[0] == 0):

                            message = ("Release successfully recorded for %s"
                                       % arxivid)

                            jsondict = {'status':'success',
                                        'message':message,
                                        'results':{'reserved':reserve_outcome[0]}}

                        else:

                            message = ("That article doesn't exist, "
                                       "or your reservation "
                                       "has been discarded because of a problem.")

                            jsondict = {'status':'failed',
                                        'message':message,
                                        'results':None}

                        self.write(jsondict)
                        self.finish()

                else:

                    message = ("You've reserved 5 articles already.")

                    jsondict = {'status':'failed',
                                'message':message,
                                'results':None}
                    self.write(jsondict)
                    self.finish()


        elif not geolocked:

            message = ("Your reservation request could not be authorized"
                       " and has been discarded.")

            jsondict = {'status':'failed',
                        'message':message,
                        'results':None}
            self.write(jsondict)
            self.finish()



class VotingHandler(tornado.web.RequestHandler):
    '''
    This handles all requests for the voting page.

    '''

    def initialize(self,
                   database,
                   voting_start,
                   voting_end,
                   debug,
                   signer,
                   geofence,
                   countries,
                   regions):
        '''
        Sets up the database.

        '''

        self.database = database
        self.voting_start = voting_start
        self.voting_end = voting_end
        self.debug = debug
        self.signer = signer
        self.geofence = geofence
        self.countries = countries
        self.regions = regions


    def post(self):
        '''This handles POST requests for vote submissions.

        takes the following arguments:

        arxivid: article to vote for
        votetype: up / down

        checks if an existing session is in play. if not, flashes a message
        saying 'no dice' in a flash message

        - checks if the user has more than five votes used for the utcdate of
          the requested arxivid
        - if they do, then deny vote
        - if they don't, allow vote

        if vote is allowed:
        - changes the nvote column for arxivid
        - adds the current user to the voters column
        - returns the nvotes for the arxivid along with
          success/failure

        if vote is not allowed:
        - sends back a 401 + error message, which the frontend JS turns into a
          flash message

        the frontend JS then:

        - updates the vote total for this arxivid
        - handles flash messages
        - updates the vote button status

        '''

        arxivid = self.get_argument('arxivid', None)
        votetype = self.get_argument('votetype', None)

        session_token = self.get_secure_cookie('coffee_session',
                                               max_age_days=30)

        sessioninfo = webdb.session_check(session_token,
                                          database=self.database)
        user_name = sessioninfo[2]
        todays_utcdate = datetime.now(tz=utc).strftime('%Y-%m-%d')

        user_ip = self.request.remote_ip

        # TESTING
        # user_ip = '131.111.184.18' # Cambridge UK
        # user_ip = '71.168.183.215' # FIOS NJ
        # user_ip = '70.192.88.245' # VZW NJ
        # user_ip = '70.42.157.5' # VZW NY
        # user_ip = '69.141.255.240' # Comcast PA
        # user_ip = '128.112.25.36' # Princeton Univ, NJ

        # if we're asked to geofence, then do so
        # (unless the request came from INSIDE the building)
        # FIXME: add exceptions for private network IPv4 addresses
        geolocked = False

        if self.geofence and user_ip != '127.0.0.1':

            try:
                geoip = self.geofence.city(user_ip)

                if (geoip.country.iso_code in self.countries and
                    geoip.subdivisions.most_specific.iso_code
                    in self.regions):
                    LOGGER.info('geofencing ok: '
                                'vote request from inside allowed regions')

                else:
                    LOGGER.warning(
                        'geofencing activated: '
                        'vote request from %s '
                        'is outside allowed regions' %
                        ('%s-%s' % (
                            geoip.country.iso_code,
                            geoip.subdivisions.most_specific.iso_code
                            ))
                        )
                    message = ("Sorry, you're trying to vote "
                               "from an IP address that is "
                               "blocked from voting.")

                    jsondict = {'status':'failed',
                                'message':message,
                                'results':None}
                    geolocked = True

                    self.write(jsondict)
                    self.finish()


            # fail deadly
            except Exception as e:
                LOGGER.exception('geofencing failed for IP %s, '
                                 'blocking request.' % user_ip)

                message = ("Sorry, you're trying to vote "
                           "from an IP address that is "
                           "blocked from voting.")

                jsondict = {'status':'failed',
                            'message':message,
                            'results':None}
                geolocked = True

                self.write(jsondict)
                self.finish()


        # check if we're in voting time-limits
        timenow = datetime.now(tz=utc).timetz()

        # if we are within the time limits, then allow the voting POST request
        if (self.voting_start < timenow < self.voting_end):
            in_votetime = True
        else:
            in_votetime = False


        # if all things are satisfied, then process the vote request
        if (arxivid and
            votetype and
            sessioninfo[0] and
            (not geolocked) and
            in_votetime):

            arxivid = xhtml_escape(arxivid)
            votetype = xhtml_escape(votetype)

            LOGGER.info('user: %s, voting: %s, on: %s' % (user_name,
                                                          votetype,
                                                          arxivid))

            if 'arXiv:' not in arxivid or votetype not in ('up','down'):

                message = ("Your vote request used invalid arguments"
                           " and has been discarded.")

                jsondict = {'status':'failed',
                            'message':message,
                            'results':None}
                self.write(jsondict)
                self.finish()

            else:

                # first, check how many votes this user has
                user_votes = arxivdb.get_user_votes(todays_utcdate,
                                                    user_name,
                                                    database=self.database)

                # make sure it's less than 5 or the votetype isn't up
                if len(user_votes) < 5 or votetype != 'up':

                    vote_outcome = arxivdb.record_vote(arxivid,
                                                       user_name,
                                                       votetype,
                                                       database=self.database)

                    if vote_outcome is False:

                        message = ("That article doesn't exist, and your vote "
                                   "has been discarded.")

                        jsondict = {'status':'failed',
                                    'message':message,
                                    'results':None}
                        self.write(jsondict)
                        self.finish()

                    else:

                        message = ("Vote successfully recorded for %s" % arxivid)

                        jsondict = {'status':'success',
                                    'message':message,
                                    'results':{'nvotes':vote_outcome}}
                        self.write(jsondict)
                        self.finish()

                else:

                    message = ("You've voted on 5 articles already.")

                    jsondict = {'status':'failed',
                                'message':message,
                                'results':None}
                    self.write(jsondict)
                    self.finish()


        elif not geolocked:

            message = ("Your vote request could not be authorized"
                       " and has been discarded.")

            jsondict = {'status':'failed',
                        'message':message,
                        'results':None}
            self.write(jsondict)
            self.finish()




class AboutHandler(tornado.web.RequestHandler):

    '''
    This handles all requests for /astroph-coffee/about.

    '''


    def initialize(self, database):
        '''
        This sets up the database.

        '''

        self.database = database


    def get(self):
        '''
        This handles GET requests.

        '''

        # handle a redirect with an attached flash message
        flash_message = self.get_argument('f', None)
        if flash_message:
            flashtext = msgdecode(flash_message)
            LOGGER.warning('flash message: %s' % flashtext)
            flashbox = (
                '<div data-alert class="alert-box radius">%s'
                '<a href="#" class="close">&times;</a></div>' %
                flashtext
                )
            flash_message = flashbox
        else:
            flash_message = ''


        local_today = datetime.now(tz=utc).strftime('%Y-%m-%d %H:%M %Z')

        # first, get the session token
        session_token = self.get_secure_cookie('coffee_session',
                                               max_age_days=30)
        ip_address = self.request.remote_ip
        client_header = self.request.headers['User-Agent'] or 'none'
        user_name = 'anonuser@%s' % ip_address
        new_user = True


        # check if this session_token corresponds to an existing user
        if session_token:

            sessioninfo = webdb.session_check(session_token,
                                              database=self.database)

            if sessioninfo[0]:

                user_name = sessioninfo[2]
                LOGGER.info('found session for %s, continuing with it' %
                            user_name)
                new_user = False

            elif sessioninfo[-1] != 'database_error':

                LOGGER.warning('unknown user, starting a new session for '
                               '%s, %s' % (ip_address, client_header))

                sessionok, token = webdb.anon_session_initiate(
                    ip_address,
                    client_header,
                    database=self.database
                )

                if sessionok and token:
                    self.set_secure_cookie('coffee_session',
                                           token,
                                           httponly=True)
                else:
                    LOGGER.error('could not set session cookie for %s, %s' %
                                 (ip_address, client_header))
                    self.set_status(500)
                    message = ("There was a database error "
                               "trying to look up user credentials.")

                    LOGGER.error('database error while looking up session for '
                                   '%s, %s' % (ip_address, client_header))

                    self.render("errorpage.html",
                                user_name=user_name,
                                local_today=local_today,
                                error_message=message,
                                flash_message=flash_message,
                                new_user=new_user)


            else:

                self.set_status(500)
                message = ("There was a database error "
                           "trying to look up user credentials.")

                LOGGER.error('database error while looking up session for '
                               '%s, %s' % (ip_address, client_header))

                self.render("errorpage.html",
                            user_name=user_name,
                            error_message=message,
                            local_today=local_today,
                            flash_message=flash_message,
                            new_user=new_user)


        else:

            if ('crawler' not in client_header.lower() and
                'bot' not in client_header.lower()):

                LOGGER.warning('unknown user, starting a new session for '
                               '%s, %s' % (ip_address, client_header))

                sessionok, token = webdb.anon_session_initiate(
                    ip_address,
                    client_header,
                    database=self.database
                    )

                if sessionok and token:
                    self.set_secure_cookie('coffee_session',
                                           token,
                                           httponly=True)
                else:
                    LOGGER.error('could not set session cookie for %s, %s' %
                                 (ip_address, client_header))
                    self.set_status(500)
                    message = ("There was a database error "
                               "trying to look up user credentials.")

                    LOGGER.error('database error while looking up session for '
                                 '%s, %s' % (ip_address, client_header))

                    self.render("errorpage.html",
                                user_name=user_name,
                                local_today=local_today,
                                error_message=message,
                                flash_message=flash_message,
                                new_user=new_user)


        #########################
        # show the contact page #
        #########################
        self.render("about.html",
                    local_today=local_today,
                    user_name=user_name,
                    flash_message=flash_message,
                    new_user=new_user)





class ArchiveHandler(tornado.web.RequestHandler):
    '''
    This handles all paper archive requests.

    url: /astroph-coffee/archive/YYYYMMDD

    '''

    def initialize(self,
                   database,
                   signer):
        '''
        Sets up the database.

        '''

        self.database = database
        self.signer = signer


    def get(self, archivedate):
        '''
        This handles GET requests.

        '''

        # handle a redirect with an attached flash message
        flash_message = self.get_argument('f', None)
        if flash_message:
            flashtext = msgdecode(flash_message, self.signer)
            LOGGER.warning('flash message: %s' % flashtext)
            flashbox = (
                '<div data-alert class="alert-box radius">%s'
                '<a href="#" class="close">&times;</a></div>' %
                flashtext
                )
            flash_message = flashbox
        else:
            flash_message = ''


        local_today = datetime.now(tz=utc).strftime('%Y-%m-%d %H:%M %Z')

        # first, get the session token
        session_token = self.get_secure_cookie('coffee_session',
                                               max_age_days=30)
        ip_address = self.request.remote_ip
        client_header = self.request.headers['User-Agent'] or 'none'
        user_name = 'anonuser@%s' % ip_address
        new_user = True

        # check if this session_token corresponds to an existing user
        if session_token:

            sessioninfo = webdb.session_check(session_token,
                                              database=self.database)

            if sessioninfo[0]:

                user_name = sessioninfo[2]
                LOGGER.info('found session for %s, continuing with it' %
                            user_name)
                new_user = False

            elif sessioninfo[-1] != 'database_error':

                LOGGER.warning('unknown user, starting a new session for '
                               '%s, %s' % (ip_address, client_header))

                sessionok, token = webdb.anon_session_initiate(
                    ip_address,
                    client_header,
                    database=self.database
                )

                if sessionok and token:
                    self.set_secure_cookie('coffee_session',
                                           token,
                                           httponly=True)
                else:
                    LOGGER.error('could not set session cookie for %s, %s' %
                                 (ip_address, client_header))
                    self.set_status(500)
                    message = ("There was a database error "
                               "trying to look up user credentials.")

                    LOGGER.error('database error while looking up session for '
                                   '%s, %s' % (ip_address, client_header))

                    self.render("errorpage.html",
                                user_name=user_name,
                                local_today=local_today,
                                error_message=message,
                                flash_message=flash_message,
                                new_user=new_user)


            else:

                self.set_status(500)
                message = ("There was a database error "
                           "trying to look up user credentials.")

                LOGGER.error('database error while looking up session for '
                               '%s, %s' % (ip_address, client_header))

                self.render("errorpage.html",
                            user_name=user_name,
                            error_message=message,
                            local_today=local_today,
                            flash_message=flash_message,
                            new_user=new_user)


        else:

            if ('crawler' not in client_header.lower() and
                'bot' not in client_header.lower()):

                LOGGER.warning('unknown user, starting a new session for '
                               '%s, %s' % (ip_address, client_header))

                sessionok, token = webdb.anon_session_initiate(
                    ip_address,
                    client_header,
                    database=self.database
                    )

                if sessionok and token:
                    self.set_secure_cookie('coffee_session',
                                           token,
                                           httponly=True)
                else:
                    LOGGER.error('could not set session cookie for %s, %s' %
                                 (ip_address, client_header))
                    self.set_status(500)
                    message = ("There was a database error "
                               "trying to look up user credentials.")

                    LOGGER.error('database error while looking up session for '
                                 '%s, %s' % (ip_address, client_header))

                    self.render("errorpage.html",
                                user_name=user_name,
                                local_today=local_today,
                                error_message=message,
                                flash_message=flash_message,
                                new_user=new_user)


        ##################################
        # now handle the archive request #
        ##################################
        if archivedate is not None:

            archivedate = xhtml_escape(archivedate)
            archivedate = re.match(ARCHIVEDATE_REGEX, archivedate)

            if archivedate:

                year, month, day = archivedate.groups()
                listingdate = '%s-%s-%s' % (year, month, day)

                # get the articles for today
                (latestdate, local_articles, flagged_local_authors,
                 voted_articles, other_articles, reserved_articles) = (
                     arxivdb.get_articles_for_listing(utcdate=listingdate,
                                                      database=self.database)
                )

                # if this date's papers aren't available, show the archive index
                if (not local_articles and
                    not voted_articles and
                    not other_articles and
                    not reserved_articles):

                    flash_message = (
                        "<div data-alert class=\"alert-box radius\">"
                        "No papers for %s were found. "
                        "You've been redirected to the Astro-Coffee archive."
                        "<a href=\"#\" class=\"close\">&times;</a></div>"
                        ) % listingdate

                    (archive_dates, archive_npapers,
                     archive_nlocal, archive_nvoted) = arxivdb.get_archive_index(
                         database=self.database
                     )
                    paper_archives = group_arxiv_dates(archive_dates,
                                                       archive_npapers,
                                                       archive_nlocal,
                                                       archive_nvoted)

                    self.render("archive.html",
                                user_name=user_name,
                                flash_message=flash_message,
                                new_user=new_user,
                                paper_archives=paper_archives,
                                local_today=local_today)

                else:

                    # figure out the UTC date for this archive listing
                    archive_datestr = datetime(
                        hour=0,
                        minute=15,
                        second=0,
                        day=int(day),
                        month=int(month),
                        year=int(year),
                        tzinfo=utc
                        ).strftime('%A, %b %d %Y')

                    # show the listing page
                    self.render("archivelisting.html",
                                user_name=user_name,
                                local_today=local_today,
                                todays_date=archive_datestr,
                                local_articles=local_articles,
                                flagged_local_authors=flagged_local_authors,
                                voted_articles=voted_articles,
                                other_articles=other_articles,
                                reserved_articles=reserved_articles,
                                flash_message=flash_message,
                                new_user=new_user)

            else:

                (archive_dates, archive_npapers,
                 archive_nlocal, archive_nvoted) = arxivdb.get_archive_index(
                     database=self.database
                 )
                paper_archives = group_arxiv_dates(archive_dates,
                                                   archive_npapers,
                                                   archive_nlocal,
                                                   archive_nvoted)

                self.render("archive.html",
                            user_name=user_name,
                            flash_message=flash_message,
                            new_user=new_user,
                            paper_archives=paper_archives,
                            local_today=local_today)

        else:

            (archive_dates, archive_npapers,
             archive_nlocal, archive_nvoted) = arxivdb.get_archive_index(
                 database=self.database
             )
            paper_archives = group_arxiv_dates(archive_dates,
                                               archive_npapers,
                                               archive_nlocal,
                                               archive_nvoted)

            self.render("archive.html",
                        user_name=user_name,
                        flash_message=flash_message,
                        new_user=new_user,
                        paper_archives=paper_archives,
                        local_today=local_today)



class LocalListHandler(tornado.web.RequestHandler):

    '''
    This handles all requests for /astroph-coffee/local-authors.

    '''


    def initialize(self, database, admincontact, adminemail):
        '''
        This sets up the database.

        '''

        self.database = database
        self.admincontact = admincontact
        self.adminemail = adminemail


    def get(self):
        '''
        This handles GET requests.

        '''

        # handle a redirect with an attached flash message
        flash_message = self.get_argument('f', None)
        if flash_message:
            flashtext = msgdecode(flash_message)
            LOGGER.warning('flash message: %s' % flashtext)
            flashbox = (
                '<div data-alert class="alert-box radius">%s'
                '<a href="#" class="close">&times;</a></div>' %
                flashtext
                )
            flash_message = flashbox
        else:
            flash_message = ''


        local_today = datetime.now(tz=utc).strftime('%Y-%m-%d %H:%M %Z')

        # first, get the session token
        session_token = self.get_secure_cookie('coffee_session',
                                               max_age_days=30)
        ip_address = self.request.remote_ip
        client_header = self.request.headers['User-Agent'] or 'none'
        user_name = 'anonuser@%s' % ip_address
        new_user = True


        # check if this session_token corresponds to an existing user
        if session_token:

            sessioninfo = webdb.session_check(session_token,
                                              database=self.database)

            if sessioninfo[0]:

                user_name = sessioninfo[2]
                LOGGER.info('found session for %s, continuing with it' %
                            user_name)
                new_user = False

            elif sessioninfo[-1] != 'database_error':

                LOGGER.warning('unknown user, starting a new session for '
                               '%s, %s' % (ip_address, client_header))

                sessionok, token = webdb.anon_session_initiate(
                    ip_address,
                    client_header,
                    database=self.database
                )

                if sessionok and token:
                    self.set_secure_cookie('coffee_session',
                                           token,
                                           httponly=True)
                else:
                    LOGGER.error('could not set session cookie for %s, %s' %
                                 (ip_address, client_header))
                    self.set_status(500)
                    message = ("There was a database error "
                               "trying to look up user credentials.")

                    LOGGER.error('database error while looking up session for '
                                   '%s, %s' % (ip_address, client_header))

                    self.render("errorpage.html",
                                user_name=user_name,
                                local_today=local_today,
                                error_message=message,
                                flash_message=flash_message,
                                new_user=new_user)


            else:

                self.set_status(500)
                message = ("There was a database error "
                           "trying to look up user credentials.")

                LOGGER.error('database error while looking up session for '
                               '%s, %s' % (ip_address, client_header))

                self.render("errorpage.html",
                            user_name=user_name,
                            error_message=message,
                            local_today=local_today,
                            flash_message=flash_message,
                            new_user=new_user)


        else:

            if ('crawler' not in client_header.lower() and
                'bot' not in client_header.lower()):

                LOGGER.warning('unknown user, starting a new session for '
                               '%s, %s' % (ip_address, client_header))

                sessionok, token = webdb.anon_session_initiate(
                    ip_address,
                    client_header,
                    database=self.database
                    )

                if sessionok and token:
                    self.set_secure_cookie('coffee_session',
                                           token,
                                           httponly=True)
                else:
                    LOGGER.error('could not set session cookie for %s, %s' %
                                 (ip_address, client_header))
                    self.set_status(500)
                    message = ("There was a database error "
                               "trying to look up user credentials.")

                    LOGGER.error('database error while looking up session for '
                                 '%s, %s' % (ip_address, client_header))

                    self.render("errorpage.html",
                                user_name=user_name,
                                local_today=local_today,
                                error_message=message,
                                flash_message=flash_message,
                                new_user=new_user)


        ###############################
        # show the local authors page #
        ###############################

        authorlist = webdb.get_local_authors()

        print('admin = %s' % self.admincontact)
        print('email = %s' % self.adminemail)


        if authorlist:

            self.render("local-authors.html",
                        local_today=local_today,
                        user_name=user_name,
                        flash_message=flash_message,
                        new_user=new_user,
                        authorlist=authorlist,
                        admincontact=self.admincontact,
                        adminemail=self.adminemail)

        else:


            LOGGER.error('could not get the author list!')
            message = ("There was a database error "
                       "trying to look up local authors. "
                       "Please "
                       "<a href=\"/astroph-coffee/about\">"
                       "let us know</a> about this problem!")

            self.render("errorpage.html",
                        user_name=user_name,
                        local_today=local_today,
                        error_message=message,
                        flash_message=flash_message,
                        new_user=new_user)
