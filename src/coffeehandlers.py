#!/usr/bin/env python

'''coffeehandlers.py - Waqas Bhatti (wbhatti@astro.princeton.edu) - Jul 2014

This contains the URL handlers for the astroph-coffee web-server.

'''

import logging
LOGGER = logging.getLogger(__name__)

from datetime import datetime
from pytz import utc, timezone

import os.path
import tornado.web
from tornado.escape import xhtml_escape, xhtml_unescape, url_unescape

import arxivdb
import webdb


##################
## URL HANDLERS ##
##################


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
        local_today = datetime.now(tz=utc).strftime('%Y-%m-%d %H:%M %Z')

        # first, get the session token
        session_token = self.get_secure_cookie('coffee_session',
                                               max_age_days=30)
        ip_address = self.request.remote_ip
        client_header = self.request.headers['User-Agent'] or 'none'
        user_name = 'anonuser@%s' % ip_address


        # check if this session_token corresponds to an existing user
        if session_token:

            sessioninfo = webdb.session_check(session_token,
                                              database=self.database)

            if sessioninfo[0]:

                user_name = sessioninfo[2]
                LOGGER.info('found session for %s, continuing with it' %
                            user_name)

            elif sessioninfo[-1] != 'database_error':

                LOGGER.warning('unknown user, starting a new session for '
                               '%s, %s' % (ip_address, client_header))


            else:

                self.set_status(500)
                message = ("There was a database error "
                           "trying to look up user credentials.")

                LOGGER.error('database error while looking up session for '
                               '%s, %s' % (ip_address, client_header))

                self.render("errorpage.html",
                            user_name=user_name,
                            error_message=message,
                            local_today=local_today)

        # show the contact page
        self.render("about.html",
                    local_today=local_today,
                    user_name=user_name)



class ArticleListHandler(tornado.web.RequestHandler):
    '''This handles all requests for the listing of selected articles. Note: if
    nobody voted on anything, the default is to return all articles with local
    authors at the top.

    '''

    def initialize(self, database,
                   voting_start,
                   voting_end,
                   server_tz):
        '''
        Sets up the database.

        '''

        self.database = database
        self.voting_start = voting_start
        self.voting_end = voting_end
        self.server_tz = server_tz


    def get(self):
        '''
        This handles GET requests.

        '''
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

        # check if this session_token corresponds to an existing user
        if session_token:

            sessioninfo = webdb.session_check(session_token,
                                               database=self.database)


            if sessioninfo[0]:

                user_name = sessioninfo[2]
                LOGGER.info('found session for %s, continuing with it' %
                            user_name)

            elif sessioninfo[-1] != 'database_error':

                LOGGER.warning('unknown user, starting a new session for '
                               '%s, %s' % (ip_address, client_header))

            else:

                self.set_status(500)
                message = ("There was a database error "
                           "trying to look up user credentials.")

                LOGGER.error('database error while looking up session for '
                               '%s, %s' % (ip_address, client_header))

                self.render("errorpage.html",
                            user_name=user_name,
                            local_today=local_today,
                            error_message=message)


        # there's no existing user session
        else:

            LOGGER.warning('unknown user, starting a new session for '
                           '%s, %s' % (ip_address, client_header))


        # get the articles for today
        local_articles, voted_articles, other_articles = (
            arxivdb.get_articles_for_listing(todays_utcdate,
                                             database=self.database)
        )

        # if today's papers aren't ready yet, show local time's papers
        if not local_articles and not voted_articles and not other_articles:

            local_articles, voted_articles, other_articles = (
                arxivdb.get_articles_for_listing(todays_localdate,
                                                 database=self.database)
            )
            todays_date = todays_localdate_str


        # show the listing page
        self.render("listing.html",
                    user_name=user_name,
                    local_today=local_today,
                    todays_date=todays_date,
                    local_articles=local_articles,
                    voted_articles=voted_articles,
                    other_articles=other_articles)



class VotingHandler(tornado.web.RequestHandler):
    '''
    This handles all requests for the voting page.

    '''

    def initialize(self, database, voting_start, voting_end, debug):
        '''
        Sets up the database.

        '''

        self.database = database
        self.voting_start = voting_start
        self.voting_end = voting_end
        self.debug = debug


    def get(self):
        '''
        This handles GET requests.

        '''

        # first, get the session token
        session_token = self.get_secure_cookie('coffee_session',
                                               max_age_days=30)
        ip_address = self.request.remote_ip
        client_header = self.request.headers['User-Agent'] or 'none'

        local_today = datetime.now(tz=utc).strftime('%Y-%m-%d %H:%M %Z')
        todays_date = datetime.now(tz=utc).strftime('%A, %b %d %Y')
        todays_utcdate = datetime.now(tz=utc).strftime('%Y-%m-%d')

        user_name = 'anonuser@%s' % ip_address

        # check if we're in voting time-limits
        timenow = datetime.now(tz=utc).timetz()

        # if we are within the time limits, then show the voting page
        if (self.voting_start < timenow < self.voting_end) or self.debug:

            # check if this session_token corresponds to an existing user
            if session_token:

                sessioninfo = webdb.session_check(session_token,
                                                   database=self.database)


                if sessioninfo[0]:

                    user_name = sessioninfo[2]
                    LOGGER.info('found session for %s, continuing with it' %
                                user_name)

                elif sessioninfo[-1] != 'database_error':

                    LOGGER.warning('unknown user, starting a new session for '
                                   '%s, %s' % (ip_address, client_header))

                else:

                    self.set_status(500)
                    message = ("There was a database error "
                               "trying to look up user credentials.")

                    LOGGER.error('database error while looking up session for '
                                   '%s, %s' % (ip_address, client_header))

                    self.render("errorpage.html",
                                user_name=user_name,
                                local_today=local_today,
                                error_message=message)


            # there's no existing user session
            else:

                LOGGER.warning('unknown user, starting a new session for '
                               '%s, %s' % (ip_address, client_header))


            # get the articles for today
            local_articles, other_articles = (
                arxivdb.get_articles_for_voting(database=self.database)
            )

            # if today's papers aren't ready yet, redirect to the papers display
            if not local_articles and not other_articles:
                self.redirect('/astroph-coffee/papers')


            # show the listing page
            self.render("voting.html",
                        user_name=user_name,
                        local_today=local_today,
                        todays_date=todays_date,
                        local_articles=local_articles,
                        other_articles=other_articles)

        # if we're not within the voting time limits, redirect to the articles
        # page
        else:
            self.redirect('/astroph-coffee/papers')



    def post(self, request):
        '''
        This handles POST requests for vote submissions.

        - handles errors
        - sets cookie if user is new
        - submits votes to DB
        - redirects to the articles page

        '''




class CoffeeHandler(tornado.web.RequestHandler):

    '''
    This handles all requests for /astroph-coffee and redirects based on
    time of day.

    '''


    def initialize(self,
                   database,
                   voting_start,
                   voting_end,
                   server_tz):
        '''
        Sets up the database.

        '''

        self.database = database
        self.voting_start = voting_start
        self.voting_end = voting_end
        self.local_tz = timezone(server_tz)
        LOGGER.info('server timezone is %s, pytz = %s' % (server_tz,
                                                          self.local_tz))


    def get(self):
        '''
        This handles GET requests.

        '''
        # first, get the session token
        session_token = self.get_secure_cookie('coffee_session',
                                               max_age_days=30)
        ip_address = self.request.remote_ip
        client_header = self.request.headers['User-Agent'] or 'none'
        local_today = datetime.now(tz=utc).strftime('%Y-%m-%d %H:%M %Z')

        user_name = 'anonuser@%s' % ip_address

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

            elif sessioninfo[-1] != 'database_error':

                LOGGER.warning('unknown user, starting a new session for '
                               '%s, %s' % (ip_address, client_header))

            else:

                self.set_status(500)
                message = ("There was a database error "
                           "trying to look up user credentials.")

                LOGGER.error('database error while looking up session for '
                               '%s, %s' % (ip_address, client_header))

                self.render("errorpage.html",
                            user_name=user_name,
                            local_today=local_today,
                            error_message=message)


        # there's no existing user session
        else:

            LOGGER.warning('unknown user, starting a new session for '
                           '%s, %s' % (ip_address, client_header))

        # construct the current dt and use it to figure out the local-to-server
        # voting times
        dtnow = datetime.now(tz=utc)

        dtstart = dtnow.replace(hour=self.voting_start.hour,
                                minute=self.voting_start.minute,
                                second=0)
        LOGGER.info('voting start = %s' % dtstart)
        local_start = dtstart.astimezone(self.local_tz)
        local_start = local_start.strftime('%H:%M %Z')

        dtend = dtnow.replace(hour=self.voting_end.hour,
                              minute=self.voting_end.minute,
                              second=0)
        LOGGER.info('voting end = %s' % dtend)
        local_end = dtend.astimezone(self.local_tz)
        local_end = local_end.strftime('%H:%M %Z')


        utc_start = self.voting_start.strftime('%H:%M %Z')
        utc_end = self.voting_end.strftime('%H:%M %Z')


        self.render("index.html",
                    user_name=user_name,
                    local_today=local_today,
                    voting_localstart=local_start,
                    voting_localend=local_end,
                    voting_start=utc_start,
                    voting_end=utc_end)



class AjaxHandler(tornado.web.RequestHandler):
    '''
    This handles all AJAX requests.

    request types:

    /astroph-coffee/ajax/vote, POST, args: arxiv_id, session_token

    '''

    def initialize(self, database, voting_start, voting_end):
        '''
        Sets up the database.

        '''

        self.database = database
        self.voting_start = voting_start
        self.voting_end = voting_end


    def get(self, request):
        '''
        This handles GET requests.

        '''


    def post(self, request):
        '''
        This handles POST requests.

        '''
