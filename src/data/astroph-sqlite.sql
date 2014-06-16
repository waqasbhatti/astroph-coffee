create table local_people (
       author text,
       email text,
       primary key (email)
);

create table arxiv (
       date_utc date,
       day_serial integer,
       title text,
       article_type text,
       authors text,
       comments text,
       abstract text,
       link text,
       pdf text,
       nvotes integer,
       voters text,
       presenters text,
       primary key(date_utc, day_serial, title)
);

create table users (
       useremail text,
       registered boolean,
       primary key (useremail)
);

create table sessions (
       token text,
       username text,
       login_utc double precision,
       logout_utc double precision,
       primary key (token)
);


-- SQLite specific settings
pragma journal_mode = wal;
pragma journal_size_limit = 52428800;
