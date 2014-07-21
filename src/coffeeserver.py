#!/usr/bin/env python

'''coffeeserver.py - Waqas Bhatti (wbhatti@astro.princeton.edu) - Jul 2014

This is the Tornado web-server for astroph-coffee. It uses URL handlers defined
in coffeehandlers.py.

'''

import os
import os.path
import ConfigParser
import sqlite3

import signal
import logging

from datetime import time
from pytz import utc

# setup signal trapping on SIGINT
def recv_sigint(signum, stack):
    '''
    handler function to receive and process a SIGINT

    '''

    LOGGER.info('received SIGINT.')
    raise KeyboardInterrupt

# register the signal callback
signal.signal(signal.SIGINT,recv_sigint)
signal.signal(signal.SIGTERM,recv_sigint)


#####################
## TORNADO IMPORTS ##
#####################

import tornado.ioloop
import tornado.httpserver
import tornado.web
import tornado.options
from tornado.options import define, options

####################################
## LOCAL IMPORTS FOR URL HANDLERS ##
####################################

import coffeehandlers


###############################
### APPLICATION SETUP BELOW ###
###############################

# define our commandline options
define('port',
       default=5005,
       help='run on the given port.',
       type=int)
define('serve',
       default='127.0.0.1',
       help='bind to given address and serve content.',
       type=str)
define('debugmode',
       default=0,
       help='start up in debug mode if set to 1.',
       type=int)

############
### MAIN ###
############

# run the server
if __name__ == '__main__':

    # parse the command line
    tornado.options.parse_command_line()

    DEBUG = True if options.debugmode == 1 else False

    CURR_PID = os.getpid()
    PID_FNAME = 'coffeeserver'
    PID_FILE = open(os.path.join('pids',PID_FNAME),'w')
    PID_FILE.write('%s\n' % CURR_PID)
    PID_FILE.close()

    # get a logger
    LOGGER = logging.getLogger('coffeeserver')
    if DEBUG:
        LOGGER.setLevel(logging.DEBUG)
    else:
        LOGGER.setLevel(logging.INFO)

    # read the conf files
    CONF = ConfigParser.ConfigParser()
    CONF.read(os.path.join(os.getcwd(),'conf','astroph.conf'))

    # get the web config vars
    SESSIONSECRET = CONF.get('keys','secret')
    STATICPATH = os.path.abspath(
        os.path.join(os.getcwd(), CONF.get('paths','static'))
    )
    TEMPLATEPATH = os.path.join(STATICPATH,'templates')

    # set up the database
    DBPATH = os.path.abspath(
        os.path.join(os.getcwd(), CONF.get('sqlite3','database'))
    )
    DATABASE = sqlite3.connect(
        DBPATH,
        detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES
    )

    # get the times of day (UTC) to switch between voting and list mode
    VOTING_START = CONF.get('times','voting_start')
    VOTING_END = CONF.get('times','voting_end')

    VOTING_START = [int(x) for x in VOTING_START.split(':')]
    VOTING_START = time(VOTING_START[0], VOTING_START[1], tzinfo=utc)
    VOTING_END = [int(x) for x in VOTING_END.split(':')]
    VOTING_END = time(VOTING_END[0], VOTING_END[1], tzinfo=utc)

    SERVER_TZ = CONF.get('times','server_tz')


    ##################
    ## URL HANDLERS ##
    ##################

    HANDLERS = [
        (r'/astroph-coffee/',coffeehandlers.CoffeeHandler,
         {'database':DATABASE,
          'voting_start':VOTING_START,
          'voting_end':VOTING_END,
          'server_tz':SERVER_TZ}),
        (r'/astroph-coffee',coffeehandlers.CoffeeHandler,
         {'database':DATABASE,
          'voting_start':VOTING_START,
          'voting_end':VOTING_END,
          'server_tz':SERVER_TZ}),
        (r'/astroph-coffee/papers',coffeehandlers.ArticleListHandler,
         {'database':DATABASE,
          'voting_start':VOTING_START,
          'voting_end':VOTING_END,
          'server_tz':SERVER_TZ}),
        (r'/astroph-coffee/papers/',coffeehandlers.ArticleListHandler,
         {'database':DATABASE,
          'voting_start':VOTING_START,
          'voting_end':VOTING_END,
          'server_tz':SERVER_TZ}),
        (r'/astroph-coffee/vote',coffeehandlers.VotingHandler,
         {'database':DATABASE,
          'voting_start':VOTING_START,
          'voting_end':VOTING_END,
          'debug':DEBUG}),
        (r'/astroph-coffee/vote/',coffeehandlers.VotingHandler,
         {'database':DATABASE,
          'voting_start':VOTING_START,
          'voting_end':VOTING_END,
          'debug':DEBUG}),
        (r'/astroph-coffee/ajax',coffeehandlers.AjaxHandler,
         {'database':DATABASE,
          'voting_start':VOTING_START,
          'voting_end':VOTING_END}),
        (r'/astroph-coffee/about',coffeehandlers.AboutHandler,
         {'database':DATABASE}),
        (r'/astroph-coffee/about/',coffeehandlers.AboutHandler,
         {'database':DATABASE}),
    ]

    #######################
    ## APPLICATION SETUP ##
    #######################

    app = tornado.web.Application(
        handlers=HANDLERS,
        cookie_secret=SESSIONSECRET,
        static_path=STATICPATH,
        template_path=TEMPLATEPATH,
        static_url_prefix='/astroph-coffee/static/',
        xsrf_cookies=True,
        debug=DEBUG,
    )

    # start up the HTTP server and our application. xheaders = True turns on
    # X-Forwarded-For support so we can see the remote IP in the logs
    http_server = tornado.httpserver.HTTPServer(app, xheaders=True)
    http_server.listen(options.port, options.serve)

    LOGGER.info('starting event loop...')

    # start the IOLoop and begin serving requests
    try:
        tornado.ioloop.IOLoop.instance().start()

    except KeyboardInterrupt:
        LOGGER.info('shutting down...')
        DATABASE.close()
