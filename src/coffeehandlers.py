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
import base64


######################
## USEFUL FUNCTIONS ##
######################

from tornado.escape import xhtml_escape, xhtml_unescape

def msgencode(message):
    '''
    This escapes a message, then base64 encodes it.

    '''
    try:
        msg = base64.b64encode(xhtml_escape(message))
        msg = msg.replace('=','*')
        return msg

    except Exception as e:
        return ''


def msgdecode(message):
    '''
    This base64 decodes a message, then unescapes it.

    '''
    try:
        msg = message.replace('*','=')
        return xhtml_unescape(base64.b64decode(msg))
    except Exception as e:
        return ''




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
                   server_tz):
        '''
        Sets up the database.

        '''

        self.database = database
        self.voting_start = voting_start
        self.voting_end = voting_end
        self.local_tz = timezone(server_tz)


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
                    voting_end=utc_end,
                    flash_message=flash_message,
                    new_user=new_user)




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

            flash_message = (
                "<div data-alert class=\"alert-box radius\">"
                "Papers for today haven't been imported yet. "
                "In the meantime, here are yesterday's papers. "
                "Please wait a few minutes and try again."
                "<a href=\"#\" class=\"close\">&times;</a></div>"
            )


        # show the listing page
        self.render("listing.html",
                    user_name=user_name,
                    local_today=local_today,
                    todays_date=todays_date,
                    local_articles=local_articles,
                    voted_articles=voted_articles,
                    other_articles=other_articles,
                    flash_message=flash_message,
                    new_user=new_user)



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
        '''This handles GET requests.

        FIXME: should also get the user's previous votes for today's date if the
        user is logged in and send them to the template, which will set the
        states of the voting buttons accordingly.

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


        # first, get the session token
        session_token = self.get_secure_cookie('coffee_session',
                                               max_age_days=30)
        ip_address = self.request.remote_ip
        client_header = self.request.headers['User-Agent'] or 'none'

        local_today = datetime.now(tz=utc).strftime('%Y-%m-%d %H:%M %Z')
        todays_date = datetime.now(tz=utc).strftime('%A, %b %d %Y')
        todays_utcdate = datetime.now(tz=utc).strftime('%Y-%m-%d')

        user_name = 'anonuser@%s' % ip_address
        new_user = True

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


            # get the articles for today
            local_articles, other_articles = (
                arxivdb.get_articles_for_voting(database=self.database)
            )

            # if today's papers aren't ready yet, redirect to the papers display
            if not local_articles and not other_articles:

                LOGGER.warning('no papers for today yet, '
                               'redirecting to previous day papers')

                redirect_msg = msgencode(
                    "Papers for today haven't been imported yet. "
                    "In the meantime, here are yesterday's papers. "
                    "Please wait a few minutes and try again."
                )

                redirect_url = '/astroph-coffee/papers?f=%s' % redirect_msg
                self.redirect(redirect_url)

            else:

                # get this user's votes
                user_articles = arxivdb.get_user_votes(todays_utcdate,
                                                       user_name,
                                                       database=self.database)
                LOGGER.info('user has votes on: %s' % user_articles)

                # show the listing page
                self.render("voting.html",
                            user_name=user_name,
                            local_today=local_today,
                            todays_date=todays_date,
                            local_articles=local_articles,
                            other_articles=other_articles,
                            flash_message=flash_message,
                            new_user=new_user,
                            user_articles=user_articles)

        # if we're not within the voting time limits, redirect to the articles
        # page
        else:

            LOGGER.warning('voting period is over, '
                           'redirecting to previous day papers')
            redirect_msg = msgencode(
                "Sorry, the voting period has ended. "
                "Here are today's selected papers."
            )

            redirect_url = '/astroph-coffee/papers?f=%s' % redirect_msg
            self.redirect(redirect_url)



    def post(self):
        '''This handles POST requests for vote submissions.

        takes the following arguments:

        arxivid: article to vote for
        votetype: up / down

        checks if an existing session is in play. if not, flashes a message
        saying no dice, bro in a flash message

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

        # if all things are satisfied, then process the vote request
        if arxivid and votetype and sessioninfo[0]:

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


        else:

            message = ("Your vote request could be authorized"
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


        # show the contact page
        self.render("about.html",
                    local_today=local_today,
                    user_name=user_name,
                    flash_message=flash_message,
                    new_user=new_user)





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
