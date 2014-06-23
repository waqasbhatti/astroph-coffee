#!/usr/bin/env python

'''
arxivdb - Waqas Bhatti (wbhatti@astro.princeton.edu) - Jun 2014

Contains utilities for astroph-coffee server SQLite database manipulation for
the webserver.

'''

import sqlite3
import os
import os.path
import ConfigParser
from pytz import utc
from hashlib import sha256
from os import urandom
import time
from datetime import datetime


CONF = ConfigParser.ConfigParser()
CONF.read('conf/astroph.conf')

DBPATH = CONF.get('sqlite3','database')

def opendb():
    '''
    This just opens a connection to the database and returns it + a cursor.

    '''

    db = sqlite3.connect(
        DBPATH, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES
        )

    cur = db.cursor()

    return db, cur


## ADDING LOCAL PEOPLE
def add_local_authors(user_data_file, database=None):
    '''
    This is used to add local users to the database, importing from the text CSV
    file user_data_file. The file must have the following format:

    # authorname,authoremail
    Example Name One,authorone@astro.example.edu
    Example Name Two,authortwo@astro.example.edu
    Example Name Three,authorthree@astro.example.edu
    ... etc.

    This is used to highlight local authors in the listings and optionally
    restrict signups for the astroph-coffee server to only these authors.

    '''

    # open the database if needed and get a cursor
    if not database:
        database, cursor = opendb()
        closedb = True
    else:
        cursor = database.cursor()
        closedb = False

    query = 'insert into local_authors (author, email) values (?, ?)'

    with open(user_data_file,'rb') as fd:
        for line in fd:
            # ignore comments and empty lines
            if not line.startswith('#') and len(line) > 10:
                try:
                    author, email = line.split(',')
                    author, email = author.strip(), email.lower().strip()
                    print('inserting %s with email %s' % (author, email))
                    cursor.execute(query, (author, email))
                except Exception as e:
                    print('could not process line: %s, skipping' % line)
                    print('error was: %s' % e)
                    database.rollback()
                    continue

    database.commit()

    # at the end, close the cursor and DB connection
    if closedb:
        cursor.close()
        database.close()


## SESSIONS

def gen_token(ipaddress, clientheader, tokenvalue):
    '''
    This generates a session token.

    tokenvalue is either 'initial' or the user's email address if they're logged
    in/signed up.

    '''

    tokenbase = '%s-%s-%s-%.4f-%s' % (ipaddress, clientheader, tokentype,
                                      time.time(), urandom(12))

    return sha256(tokenbase).hexdigest()


def session_check(sessiontoken, database=None):
    '''
    This checks if a sessiontoken is present in the sessions table of the DB.

    '''

    # open the database if needed and get a cursor
    if not database:
        database, cursor = opendb()
        closedb = True
    else:
        cursor = database.cursor()
        closedb = False

    try:

        query = ("select token, useremail from sessions where token = ?")
        params = (sessiontoken,)
        cursor.execute(query, params)
        row = cursor.fetchone()

        if row and len(row) > 0:
            results = (True, row[0], row[1], 'token_found')
        else:
            results = (False, None, None, 'unknown_token')

    except:

        print('could not get database results for sessiontoken: %s'
              % sessiontoken)
        results = (False, None, None, 'database_error')

    # at the end, close the cursor and DB connection
    if closedb:
        cursor.close()
        database.close()

    return results



def session_initiate(ipaddress,
                     clientheader,
                     useremail,
                     onlylocals=False,
                     onlydomains=None,
                     database=None):
    '''
    This initiates a user signup and returns a session token for this
    user. Optionally, can restrict signups to domain names in the list
    onlydomains (e.g. ['astro.princeton.edu', 'princeton.edu', 'ias.edu']). Can
    also optionally restrict signups to people in the local_authors table of the
    DB by setting onlylocals = True.

    The workflow is:

    - user hits the website

    - website checks if a astroph_coffee_session cookie is set

    - if it is set:
      - get the value of the cookie and compare with sessions table in DB
      - if there's an existing session, allow user to save selections
      - if there is not an existing session, then:
        - when the user hits save, ask for email
        - generate a new session token with user's email and send back a cookie
          with this session token

    - if it is not set:

      - generate an 'initial' session token and send it back in cookie with
        response

      - when the user hits save, ask for email
      - generate a new session token with user's email and send back a cookie
        with this session token

     - if the user attempts to sign up with an email that's in use already:

       - if the ipaddress is the same as the existing session's ipaddress,
         return the same session token in the cookie, and don't ask for a new
         email

       - if not, then ask for a new email, and generate a new session token and
         cookie


    '''

    # open the database if needed and get a cursor
    if not database:
        database, cursor = opendb()
        closedb = True
    else:
        cursor = database.cursor()
        closedb = False






    # at the end, close the cursor and DB connection
    if closedb:
        cursor.close()
        database.close()
