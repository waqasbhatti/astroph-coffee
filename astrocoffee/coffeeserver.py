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

# the port the server will listen on
define('port',
       default=5005,
       help='Run on the given TCP port.',
       type=int)

# the address the server will listen on.
define('serve',
       default='0.0.0.0',
       help=('Bind to given address and serve content. '
             '0.0.0.0 binds to all network interfaces '
             '(internal and external). 127.0.0.1 binds to only '
             'the localhost address so the server will not accept '
             'external connections.'),
       type=str)

# basedir is the directory where the server will work.
define('basedir',
       default=os.getcwd(),
       help=("The base work directory of the server. "
             "This directory contains the astro-coffee and "
             "authentication databases, the server's config file, "
             "templates, and CSS/JS files."),
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

def setup_worker(database_url):
    '''This sets up the workers to ignore the INT signal, which is handled by
    the main process.

    Sets up the backend database instance. Also sets up the bucket client if
    required.

    '''

    from . import database

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

    print('Shutting down database engine in process: %s' % currproc.name,
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

    from . import firstrun
    from astrocoffee.vendored.futures37.process import ProcessPoolExecutor

    ####################################
    ## SET UP THE BASEDIR IF NOT DONE ##
    ####################################

    BASEDIR = os.path.abspath(options.basedir)
    PORT = options.port
    LISTEN = options.serve

    firstrun_file = os.path.join(BASEDIR, '.coffee-first-run-done')
    if options.conf is not None and os.path.exists(options.conf):
        conf_file = os.path.abspath(options.conf)
    else:
        conf_file = os.path.join(BASEDIR, 'astro-coffee.conf')

    # this call does the following
    # - copies over the conf file to the basedir and updates it
    # - makes the authnzerver auth DB
    # - makes the astro-coffee DB
    # - copies over the template subdir to the basedir
    # - copies over the static directory to the basedir
    if not os.path.exists(firstrun_file):
        CONF = firstrun.setup_coffee_server(BASEDIR,
                                            PORT,
                                            LISTEN)
    elif os.path.exists(conf_file):
        CONF = firstrun.load_config(conf_file)

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
    EXECUTOR = ProcessPoolExecutor(max_workers=CONF['max_workers'],
                                   initializer=setup_worker,
                                   initargs=(CONF['database_url'],),
                                   finalizer=close_database)

    #########################
    ## IMPORT URL HANDLERS ##
    #########################

    from . import coffee_handlers as coffee
    from . import auth_handlers as auth
    from . import admin_handlers as admin
    from .arxivupdate import periodic_arxiv_update

    #####################
    ## DEFINE HANDLERS ##
    #####################

    HANDLERS = [

        ###################
        ## PAGE HANDLERS ##
        ###################

        # index page
        (r'/astro-coffee',
         coffee.IndexHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),
        (r'/astro-coffee/',
         coffee.IndexHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        # the local author list page
        (r'/astro-coffee/local-authors',
         coffee.LocalListHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),
        (r'/astro-coffee/local-authors/',
         coffee.LocalListHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        # the about page
        (r'/astro-coffee/about',
         coffee.AboutHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),
        (r'/astro-coffee/about/',
         coffee.AboutHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        # - /papers/today directs to today
        # - /papers/some-date directs to papers on that date
        # - /papers directs to the archive of papers
        (r'/astro-coffee/papers/?(.*)',
         coffee.CoffeeHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        ##################
        ## API HANDLERS ##
        ##################

        (r'/astro-coffee/api/vote',
         coffee.VoteHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        (r'/astro-coffee/api/reserve',
         coffee.ReserveHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        (r'/astro-coffee/api/present',
         coffee.PresentHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        ###################
        ## AUTH HANDLERS ##
        ###################

        # this is the login page
        (r'/astro-coffee/users/login',
         auth.LoginHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        # this is the logout page
        (r'/astro-coffee/users/logout',
         auth.LogoutHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        # this is the new user page
        (r'/astro-coffee/users/new',
         auth.NewUserHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        # this is the verification page for verifying email addresses
        (r'/astro-coffee/users/verify',
         auth.VerifyUserHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        # this is step 1 page for forgotten passwords
        (r'/astro-coffee/users/forgot-password-step1',
         auth.ForgotPassStep1Handler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        # this is the verification page for verifying email addresses
        (r'/astro-coffee/users/forgot-password-step2',
         auth.ForgotPassStep2Handler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        # this is the password change page
        (r'/astro-coffee/users/password-change',
         auth.ChangePassHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        # this is the user-prefs page
        (r'/astro-coffee/users/home',
         auth.UserHomeHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        # this is the user-delete page
        (r'/astro-coffee/users/delete',
         auth.DeleteUserHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        ####################
        ## ADMIN HANDLERS ##
        ####################

        # this is the admin index page
        (r'/astro-coffee/czar',
         admin.AdminIndexHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        # this handles email settings updates
        (r'/astro-coffee/czar/email',
         admin.EmailSettingsHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        # this handles user updates
        (r'/astro-coffee/czar/users',
         admin.UserAdminHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

        # this handles arxiv settings updates
        (r'/astro-coffee/czar/arxiv',
         admin.ArxivSettingsHandler,
         {'basedir': BASEDIR, 'conf':CONF, 'executor':EXECUTOR}),

    ]

    ########################
    ## APPLICATION SET UP ##
    ########################

    app = tornado.web.Application(
        static_path=CONF['asset_path'],
        handlers=HANDLERS,
        template_path=CONF['template_path'],
        static_url_prefix='/astro-coffee/static/',
        compress_response=True,
        cookie_secret=CONF['session_secret'],
        xsrf_cookies=True,
        xsrf_cookie_kwargs={'samesite':'Lax'},
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
    serverport = options.port
    maxtries = 10
    thistry = 0
    while not portok and thistry < maxtries:
        try:
            http_server.listen(serverport, options.serve)
            portok = True
        except socket.error:
            LOGGER.warning('%s:%s is already in use, trying port %s' %
                           (options.serve, serverport, serverport + 1))
            serverport = serverport + 1

    if not portok:
        LOGGER.error('could not find a free port after %s tries, giving up' %
                     maxtries)
        sys.exit(1)

    LOGGER.info('Started coffee-server. listening on http://%s:%s' %
                (options.serve, serverport))
    LOGGER.info('Background worker processes: %s, IOLoop in use: %s' %
                (CONF['max_workers'], IOLOOP_SPEC))
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
        # runs every 15 minutes
        periodic_arxiv_updater = loop.PeriodicCallback(
            periodic_arxiv_update_fn,
            86400000.0,
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
