# -*- coding: utf-8 -*-

'''This handles the database bits.

'''

#############
## LOGGING ##
#############

import logging
LOGGER = logging.getLogger(__name__)

LOGDEBUG = LOGGER.debug
LOGINFO = LOGGER.info
LOGWARNING = LOGGER.warning
LOGERROR = LOGGER.error
LOGEXCEPTION = LOGGER.exception


#############
## IMPORTS ##
#############

from textwrap import dedent
import sqlite3
import os.path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    Text,
    Boolean,
    JSON
)
from sqlalchemy.types import DATE, Enum


#########################
## DATABASE TABLE DEFS ##
#########################

ASTROCOFFEE = MetaData()

LocalAuthors = Table(
    "local_authors",
    ASTROCOFFEE,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("name", Text, unique=True, nullable=False),
    Column("email", Text, nullable=False),
    # this contains any other info associated with this author
    # - affiliation
    # - server user ID
    # - server user role
    Column("info", JSON),
)

ArxivListings = Table(
    "arxiv_listings",
    ASTROCOFFEE,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("utcdate", DATE, nullable=False, index=True),
    Column("day_serial", Integer, nullable=False),
    Column("title", Text, nullable=False),
    Column("article_type", Enum("newarticle",
                                "crosslist",
                                "replacement",
                                name="article_type_enum"),
           index=True, nullable=False, default="newarticle"),
    Column("arxiv_id", Text, unique=True, nullable=False, index=True),
    # this contains the list of authors
    Column("authors", JSON, nullable=False),
    Column("comments", Text),
    Column("abstract", Text),
    Column("link", Text),
    Column("pdf", Text),
    # this contains a list of the indices of the paper author list that
    # correspond to local authors. also contains corresponding lists of local
    # author affiliations
    Column("local_authors", JSON),
    Column("nvotes", Integer, nullable=False, default=0),
    # this contains a list of server userids that voted on this paper
    Column("voter_userids", JSON),
    Column("presenter_userid", Text),
    Column("reserved", Boolean, nullable=False, default=False),
    Column("reserved_by_userid", Text),
    Column("reserved_on", DATE),
    Column("reserved_until", DATE),
)


#######################
## DATABASE CREATION ##
#######################

WAL_SCRIPT = dedent(
    """\
    pragma journal_mode=WAL;
    pragma journal_size_limit=5242880;
    """
)

FTS_SCRIPT = dedent(
    """\
    -- create the FTS5 index
    create virtual table arxiv_fts using fts5(
        utcdate,
        title,
        article_type,
        arxiv_id,
        authors,
        abstract,
        link,
        pdf,
        voter_userids,
        presenter_userid,
        reserved_by_userid,
        content="arxiv_listings",
        tokenize="unicode61"
    );

    -- create the required triggers to update the FTS index whenever stuff is
    -- inserted, updated, or deleted from the arxiv table.
    create trigger fts_before_update before update on arxiv_listings begin
        delete from arxiv_fts where rowid=old.rowid;
    end;

    create trigger fts_before_delete before delete on arxiv_listings begin
        delete from arxiv_fts where rowid=old.rowid;
    end;

    create trigger fts_after_update after update on arxiv_listings begin
        insert into arxiv_fts(rowid, utcdate, title, article_type,
                              arxiv_id, authors, abstract, link, pdf,
                              voter_userids, presenter_userid,
                              reserved_by_userid)
            values (new.rowid, new.utcdate,
                    new.title, new.article_type, new.arxiv_id,
                    new.authors, new.abstract, new.link, new.pdf,
                    new.voter_userids, new.presenter_userid,
                    new.reserved_by_userid);
        end;

    create trigger fts_after_insert after insert on arxiv_listings begin
        insert into arxiv_fts(rowid, utcdate, title, article_type,
                              arxiv_id, authors, abstract, link, pdf,
                              voter_userids, presenter_userid,
                              reserved_by_userid)
            values (new.rowid, new.utcdate,
                    new.title, new.article_type, new.arxiv_id,
                    new.authors, new.abstract, new.link, new.pdf,
                    new.voter_userids, new.presenter_userid,
                    new.reserved_by_userid);
        end;
    """
)


def new_astrocoffee_db(
        database_url,
        database_metadata=ASTROCOFFEE,
        echo=False,
):
    '''
    This makes a new Astro-Coffee SQLite database.

    Parameters
    ----------

    database_url : str
        A valid SQLAlchemy database connection string.

    database_metadata : sqlalchemy.MetaData object
        The metadata object to bind to the engine.

    echo : bool
        If True, will echo the DDL lines used for creation of the database.

    Returns
    -------

    db_path : str
        The path to the database file.

    '''

    engine = create_engine(database_url, echo=echo)
    database_metadata.create_all(engine)
    engine.dispose()
    del engine

    # add in the WAL pragma and FTS indices
    db_path = database_url.replace('sqlite:///','')
    db = sqlite3.connect(db_path)
    cur = db.cursor()
    cur.executescript(WAL_SCRIPT)
    cur.executescript(FTS_SCRIPT)
    db.commit()
    db.close()

    return os.path.abspath(db_path)


def get_astrocoffee_db(database_url,
                       database_metadata=ASTROCOFFEE,
                       use_engine=None,
                       engine_dispose=False,
                       engine_kwargs=None,
                       echo=False):
    '''This returns a database connection.

    Parameters
    ----------

    database_url : str
        A valid SQLAlchemy database connection string.

    database_metadata : sqlalchemy.MetaData object
        The metadata object to bind to the engine.

    use_engine : `sqlalchemy.engine.Engine` object or None
        If provided, will use this existing engine object to get a connection.

    engine_dispose : bool
        If True, will run the `Engine.dispose()` method before binding to
        it. This can help get rid any existing connections.

    engine_kwargs : dict or None
        This contains any kwargs to pass to the `create_engine` call. One
        specific use-case is passing `use_batch_mode=True` to a PostgreSQL
        engine to enable fast `executemany` statements.

    echo : bool
        If True, will echo the DDL lines used for creation of the database.

    Returns
    -------

    (engine, connection, metadata) : tuple
        This function will return the engine, the DB connection generated, and
        the metadata object as a tuple.

    '''

    # enable foreign key support
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    if not use_engine:
        if isinstance(engine_kwargs, dict):
            database_engine = create_engine(database_url,
                                            echo=echo,
                                            **engine_kwargs)
        else:
            database_engine = create_engine(database_url,
                                            echo=echo)

    else:
        database_engine = use_engine
        if engine_dispose:
            database_engine.dispose()

    database_metadata.bind = database_engine
    conn = database_engine.connect()

    return database_engine, conn, database_metadata
