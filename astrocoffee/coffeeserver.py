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
import json
import multiprocessing as mp
from datetime import datetime
import subprocess
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
             "templates, and CSS files."),
       type=str)
