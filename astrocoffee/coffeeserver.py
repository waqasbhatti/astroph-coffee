# -*- coding: utf-8 -*-

'''This is the main server module.

'''

#############
## LOGGING ##
#############

import logging


#############
## IMPORTS ##
#############

import os
import os.path
import signal
import time
import sys
import socket
import multiprocessing as mp
from functools import partial


# setup signal trapping on SIGINT
def recv_sigint(signum, stack):
    '''
    handler function to receive and process a SIGINT

    '''
    raise KeyboardInterrupt


#####################
## TORNADO IMPORTS ##
#####################

try:
    import asyncio
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    IOLOOP_SPEC = 'uvloop'
except Exception:
    HAVE_UVLOOP = False
    IOLOOP_SPEC = 'asyncio'

import tornado.ioloop
import tornado.httpserver
import tornado.web
import tornado.options
from tornado.options import define, options


###############################
### APPLICATION SETUP BELOW ###
###############################

modpath = os.path.abspath(os.path.dirname(__file__))

## define our commandline options ##

# basedir is the directory where the server will work.
define('basedir',
       default=os.getcwd(),
       help=("The base work directory of the server. "
             "This directory contains the astro-coffee and "
             "authentication databases, the server's config file, "
             "templates, and CSS/JS files. "
             "The default basedir is the current directory "
             "in which the server was launched."),
       type=str)

# conf is the path to the server config file (this must be a complete conf file)
define('conf',
       default=None,
       help=("The configuration file to use for all settings. "
             "This overrides every other command-line option."),
       type=str)


###########
## UTILS ##
###########

def setup_worker(database_url, authdb_url):
    '''This sets up the workers to ignore the INT signal, which is handled by
    the main process.

    Sets up the backend database instance. Also sets up the bucket client if
    required.

    '''

    from . import database
    from authnzerver import authdb

    # unregister interrupt signals so they don't get to the worker
    # and the executor can kill them cleanly (hopefully)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    # set up the database
    currproc = mp.current_process()

    # sets up the engine, connection, and metadata objects as process-local
    # variables
    currproc.engine, currproc.connection, currproc.metadata = (
        database.get_astrocoffee_db(database_url)
    )

    # setup the authnzerver DB
    currproc.authdb_engine, currproc.authdb_conn, currproc.authdb_meta = (
        authdb.get_auth_db(authdb_url)
    )


def close_database():

    '''This is used to close the database when the worker loop
    exits.

    '''

    currproc = mp.current_process()
    if getattr(currproc, 'metadata', None):
        del currproc.metadata

    if getattr(currproc, 'connection', None):
        currproc.connection.close()
        del currproc.connection

    if getattr(currproc, 'engine', None):
        currproc.engine.dispose()
        del currproc.engine

    if getattr(currproc, 'authdb_meta', None):
        del currproc.authdb_meta

    if getattr(currproc, 'authdb_conn', None):
        currproc.authdb_conn.close()
        del currproc.authdb_conn

    if getattr(currproc, 'authdb_engine', None):
        currproc.authdb_engine.dispose()
        del currproc.authdb_engine

    print('Database engines in worker process: %s shutdown.' % currproc.name,
          file=sys.stdout)


##########
## MAIN ##
##########

def main():
    '''
    The main function.

    '''

    # parse the command line
    tornado.options.parse_command_line()

    LOGGER = logging.getLogger(__name__)

    ###################
    ## LOCAL IMPORTS ##
    ###################

    from . import firstrun, modtools
    from authnzerver.external.futures37.process import ProcessPoolExecutor

    ####################################
    ## SET UP THE BASEDIR IF NOT DONE ##
    ####################################

    BASEDIR = os.path.abspath(options.basedir)

    firstrun_file = os.path.join(BASEDIR, '.coffee-first-run-done')
    conf_file = os.path.join(BASEDIR, 'coffee_settings.py')

    if os.path.exists(firstrun_file) and os.path.exists(conf_file):
        LOGGER.info("Loading config from: %s" % conf_file)
        CONF = modtools.module_from_string(conf_file,
                                           force_reload=True)
    elif os.path.exists(firstrun_file) and not os.path.exists(conf_file):
        LOGGER.error("No config file found in basedir: %s, can't continue. "
                     "Hint: remove the %s file to regenerate it." %
                     (BASEDIR, firstrun_file))
        sys.exit(1)
    elif not os.path.exists(firstrun_file):
        LOGGER.warning("Generating a new config file and "
                       "initializing the coffee-server base directory in %s. "
                       "Existing auth and arXiv databases will be retained." %
                       BASEDIR)
        conf_file = firstrun.setup_coffee_server(BASEDIR, nodb=True)
        CONF = modtools.module_from_string(conf_file,
                                           force_reload=True)

    else:
        LOGGER.error("Could not load the expected config file "
                     "in the server basedir: %s. Can't continue..." %
                     conf_file)
        sys.exit(1)

    ###########################
    ## WORK AROUND APPLE BUG ##
    ###########################

    # here, we have to initialize networking in the main thread
    # before forking for MacOS. see:
    # https://bugs.python.org/issue30385#msg293958
    # if this doesn't work, Python will segfault.
    # the workaround noted in the report is to launch
    # lcc-server like so:
    # env no_proxy='*' indexserver
    if sys.platform == 'darwin':
        import requests
        requests.get('http://captive.apple.com/hotspot-detect.html')

    ####################################
    ## PERSISTENT BACKGROUND EXECUTOR ##
    ####################################

    #
    # this is the background executor we'll pass over to the handler
    #
    EXECUTOR = ProcessPoolExecutor(
        max_workers=CONF.max_workers,
        initializer=setup_worker,
        initargs=(CONF.database_url, CONF.authdb_url),
        finalizer=close_database
    )

    #########################
    ## IMPORT URL HANDLERS ##
    #########################

    from .handlers import baseuimodules
    from .handlers.basehandler import PageNotFoundHandler
    from .handlers import coffee_handlers as coffee
    from .handlers import auth_handlers as auth
    from .handlers import admin_handlers as admin
    from .handlers import api_handlers as api
    from .arxivupdate import periodic_arxiv_update

    #####################
    ## DEFINE HANDLERS ##
    #####################

    BASEURL = CONF.base_url

    HANDLERS = [

        ###################
        ## PAGE HANDLERS ##
        ###################

        # index page
        (r'{baseurl}'.format(baseurl=BASEURL),
         coffee.IndexHandler,
         {'conf':CONF, 'executor':EXECUTOR}),
        (r'{baseurl}/'.format(baseurl=BASEURL),
         coffee.IndexHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        # the local author list page
        (r'{baseurl}/local-authors'.format(baseurl=BASEURL),
         coffee.LocalAuthorListHandler,
         {'conf':CONF, 'executor':EXECUTOR}),
        (r'{baseurl}/local-authors/'.format(baseurl=BASEURL),
         coffee.LocalAuthorListHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        # the about page
        (r'{baseurl}/about'.format(baseurl=BASEURL),
         coffee.AboutHandler,
         {'conf':CONF, 'executor':EXECUTOR}),
        (r'{baseurl}/about/'.format(baseurl=BASEURL),
         coffee.AboutHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        # - /papers/today directs to today
        (r'{baseurl}/papers/today'.format(baseurl=BASEURL),
         coffee.ArticleListingHandler,
         {'conf':CONF, 'executor':EXECUTOR}),
        (r'{baseurl}/papers/today/'.format(baseurl=BASEURL),
         coffee.ArticleListingHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        # - /papers/YYYYMMDD directs to papers on that date
        (r'{baseurl}/papers/(\d{{8}})'.format(baseurl=BASEURL),
         coffee.ArchiveListingHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        # - /papers directs to the archive of papers
        (r'{baseurl}/papers'.format(baseurl=BASEURL),
         coffee.ArchiveIndexHandler,
         {'conf':CONF, 'executor':EXECUTOR}),
        (r'{baseurl}/papers/'.format(baseurl=BASEURL),
         coffee.ArchiveIndexHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        ##################
        ## API HANDLERS ##
        ##################

        (r'{baseurl}/api/vote'.format(baseurl=BASEURL),
         api.VoteHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        (r'{baseurl}/api/reserve'.format(baseurl=BASEURL),
         api.ReserveHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        (r'{baseurl}/api/present'.format(baseurl=BASEURL),
         api.PresentHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        (r'{baseurl}/api/edit'.format(baseurl=BASEURL),
         api.EditHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        ###################
        ## AUTH HANDLERS ##
        ###################

        # this is the login page
        (r'{baseurl}/users/login'.format(baseurl=BASEURL),
         auth.LoginHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        # this is the logout page
        (r'{baseurl}/users/logout'.format(baseurl=BASEURL),
         auth.LogoutHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        # this is the new user page
        (r'{baseurl}/users/new'.format(baseurl=BASEURL),
         auth.NewUserHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        # this is the verification page for verifying email addresses
        (r'{baseurl}/users/verify'.format(baseurl=BASEURL),
         auth.VerifyUserHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        # this is step 1 page for forgotten passwords
        (r'{baseurl}/users/forgot-password-step1'.format(baseurl=BASEURL),
         auth.ForgotPassStep1Handler,
         {'conf':CONF, 'executor':EXECUTOR}),

        # this is the verification page for verifying email addresses
        (r'{baseurl}/users/forgot-password-step2'.format(baseurl=BASEURL),
         auth.ForgotPassStep2Handler,
         {'conf':CONF, 'executor':EXECUTOR}),

        # this is the password change page
        (r'{baseurl}/users/password-change'.format(baseurl=BASEURL),
         auth.ChangePassHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        # this is the user-delete page
        (r'{baseurl}/users/delete'.format(baseurl=BASEURL),
         auth.DeleteUserHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        ####################
        ## ADMIN HANDLERS ##
        ####################

        # this is the admin index page
        (r'{baseurl}/czar'.format(baseurl=BASEURL),
         admin.AdminIndexHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        # this handles email settings updates
        (r'{baseurl}/czar/email'.format(baseurl=BASEURL),
         admin.EmailSettingsHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        # this handles user updates
        (r'{baseurl}/czar/users'.format(baseurl=BASEURL),
         admin.UserAdminHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

        # this handles arxiv settings updates
        (r'{baseurl}/czar/arxiv'.format(baseurl=BASEURL),
         admin.ArxivSettingsHandler,
         {'conf':CONF, 'executor':EXECUTOR}),

    ]

    ########################
    ## APPLICATION SET UP ##
    ########################

    app = tornado.web.Application(
        ui_modules=baseuimodules,
        static_path=CONF.asset_path,
        handlers=HANDLERS,
        template_path=CONF.template_path,
        static_url_prefix='{baseurl}/static/'.format(baseurl=BASEURL),
        compress_response=True,
        cookie_secret=CONF.session_secret,
        xsrf_cookies=True,
        xsrf_cookie_kwargs={'samesite':'Lax'},
        default_handler_class=PageNotFoundHandler,
        default_handler_args={'conf':CONF, 'executor':EXECUTOR},
    )

    # start up the HTTP server and our application. xheaders = True turns on
    # X-Forwarded-For support so we can see the remote IP in the logs
    http_server = tornado.httpserver.HTTPServer(app, xheaders=True)

    ######################
    ## start the server ##
    ######################

    # make sure the port we're going to listen on is ok
    # inspired by how Jupyter notebook does this
    portok = False
    serverport = CONF.server_port
    serveraddress = CONF.server_address
    maxtries = 10
    thistry = 0
    while not portok and thistry < maxtries:
        try:
            http_server.listen(serverport, serveraddress)
            portok = True
        except socket.error:
            LOGGER.warning('%s:%s is already in use, trying port %s' %
                           (serveraddress, serverport, serverport + 1))
            serverport = serverport + 1

    if not portok:
        LOGGER.error('could not find a free port after %s tries, giving up' %
                     maxtries)
        sys.exit(1)

    LOGGER.info('Started coffee-server. listening on http://%s:%s' %
                (serveraddress, serverport))
    LOGGER.info('Background worker processes: %s, IOLoop in use: %s' %
                (CONF.max_workers, IOLOOP_SPEC))
    LOGGER.info('The current base directory is: %s' % os.path.abspath(BASEDIR))

    # register the signal callbacks
    signal.signal(signal.SIGINT,recv_sigint)
    signal.signal(signal.SIGTERM,recv_sigint)

    # start the IOLoop and begin serving requests
    try:

        loop = tornado.ioloop.IOLoop.current()

        periodic_arxiv_update_fn = partial(
            periodic_arxiv_update,
            CONF,
        )

        # run once at start
        periodic_arxiv_update_fn()

        # add our periodic callback for the arxiv worker
        # runs every 15 minutes to check if it's close to voting start time
        # if it is, schedules the arxiv update
        periodic_arxiv_updater = tornado.ioloop.PeriodicCallback(
            periodic_arxiv_update_fn,
            900000.0,
            jitter=0.1,
        )
        periodic_arxiv_updater.start()

        # start the IOLoop
        loop.start()

    except KeyboardInterrupt:

        LOGGER.info('received Ctrl-C: shutting down...')
        loop.stop()
        # close down the processpool

    EXECUTOR.shutdown()
    time.sleep(2)


# run the server
if __name__ == '__main__':
    main()
