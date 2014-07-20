#!/usr/bin/env python

'''coffeehandlers.py - Waqas Bhatti (wbhatti@astro.princeton.edu) - Jul 2014

This contains the URL handlers for the astroph-coffee web-server.

'''

import logging
LOGGER = logging.getLogger(__name__)

from datetime import datetime
from pytz import utc

import os.path
import tornado.web
from tornado.escape import xhtml_escape, xhtml_unescape, url_unescape

import arxivdb
import webdb


##################
## URL HANDLERS ##
##################


class ArticleListHandler(tornado.web.RequestHandler):
    '''This handles all requests for the listing of selected articles. Note: if
    nobody voted on anything, the default is to return all articles with local
    authors at the top.

    '''

    def initialize(self, database, voting_start, voting_end):
        '''
        Sets up the database.

        '''

        self.database = database
        self.voting_start = voting_start
        self.voting_end = voting_end


    def get(self):
        '''
        This handles GET requests.

        '''
        # first, get the session token
        session_token = self.get_secure_cookie('coffee_session',
                                               max_age_days=30)
        ip_address = self.request.remote_ip
        client_header = self.request.headers['User-Agent'] or 'none'

        # check if this session_token corresponds to an existing user
        if session_token:

            sessioninfo = webdb.session_check(session_token,
                                               database=self.database)

            useremail = 'anonuser@%s' % ip_address

            if sessioninfo[0]:

                useremail = sessioninfo[2]
                LOGGER.info('found session for %s, continuing with it' %
                            useremail)

                # show the listing page



            elif sessioninfo[-1] != 'database_error':

                LOGGER.warning('unknown user, starting a new session for '
                               '%s, %s' % (ip_address, client_header))


                # show the listing page

            else:

                self.set_status(500)
                message = ("There was a database error "
                           "trying to look up user credentials.")

                LOGGER.error('database error while looking up session for '
                               '%s, %s' % (ip_address, client_header))

                self.render("errorpage.html",
                            useremail=useremail,
                            message=message)


        # there's no existing user session
        else:

            session_token = webdb.gen_token(ip_address,
                                            client_header,
                                            'initial')





class VotingHandler(tornado.web.RequestHandler):
    '''
    This handles all requests for the voting page.

    '''

    def initialize(self, database, voting_start, voting_end):
        '''
        Sets up the database.

        '''

        self.database = database
        self.voting_start = voting_start
        self.voting_end = voting_end


    def get(self):
        '''
        This handles GET requests.

        '''

        # first, check if we're in voting time-limits
        timenow = datetime.now(tz=utc).timetz()

        # if we are within the time limits, then show the voting page
        if self.voting_start < timenow < self.voting_end:

            # get the session token
            session_token = self.get_secure_cookie('coffee_session',
                                                   max_age_days=30)
            ip_address = self.request.remote_ip
            client_header = self.request.headers['User-Agent'] or 'none'

            # check if this session_token corresponds to an existing user
            if session_token:

                sessioninfo = webdb.session_check(session_token,
                                                   database=self.database)

                useremail = 'anonuser@%s' % ip_address

                if sessioninfo[0]:

                    useremail = sessioninfo[2]
                    LOGGER.info('found session for %s, '
                                'continuing with it' %
                                useremail)

                    # show the voting page for this user



                elif sessioninfo[-1] != 'database_error':

                    LOGGER.warning('unknown user, starting a new session for '
                                   '%s, %s' % (ip_address, client_header))


                    # show the voting page for the new user

                else:

                    self.set_status(500)
                    message = ("There was a database error "
                               "trying to look up user credentials.")

                    LOGGER.error('database error while looking up session for '
                                   '%s, %s' % (ip_address, client_header))

                    self.render("errorpage.html",
                                useremail=useremail,
                                message=message)


            # there's no existing user session
            else:

                # generate an initial session token
                session_token = webdb.gen_token(ip_address,
                                                client_header,
                                                'initial')


                # get the articles for today



                # set the cookie
                self.set_secure_cookie('coffee_session',
                                       session_token,
                                       expires_days=30)

                # render the special voting page with articles for today


        # if we're not within the voting time limits, redirect to the articles
        # page
        else:
            self.redirect('/astroph-coffee/articles')



    def post(self, request):
        '''
        This handles POST requests for vote submissions.

        '''



class CoffeeHandler(tornado.web.RequestHandler):

    '''
    This handles all requests for /astroph-coffee and redirects based on
    time of day.

    '''


    def initialize(self,
                   database,
                   voting_start,
                   voting_end):
        '''
        Sets up the database.

        '''

        self.database = database
        self.voting_start = voting_start
        self.voting_end = voting_end


    def get(self):
        '''
        This handles GET requests.

        '''

        # figure out which URL to redirect to
        timenow = datetime.now(tz=utc).timetz()

        if self.voting_start < timenow < self.voting_end:
            self.redirect('/astroph-coffee/vote')
        else:
            self.redirect('/astroph-coffee/articles')



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
