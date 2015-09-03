create table local_authors (
       author text,
       email text,
       primary key (email)
);

create table arxiv (
       utctime datetime,
       utcdate date,
       day_serial integer,
       title text,
       article_type text,
       arxiv_id text,
       authors text,
       comments text,
       abstract text,
       link text,
       pdf text,
       nvotes integer,
       voters text,
       presenters text,
       local_authors boolean default false,
       reservers text,
       reserved integer default 0,
       primary key(utcdate, day_serial, article_type, arxiv_id)
);

create table users (
       useremail text,
       registered boolean,
       primary key (useremail)
);

create table sessions (
       token text,
       useremail text,
       ipaddress text,
       clientheader text,
       login_utc double precision,
       primary key (token)
);


-- SQLite specific settings
pragma journal_mode = wal;
pragma journal_size_limit = 52428800;
