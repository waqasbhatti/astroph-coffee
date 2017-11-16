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
       local_author_indices text,
       local_author_specaffils text,
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


-- create the FTS5 index
create virtual table arxiv_fts using fts5(
       content="arxiv",
       utcdate,
       day_serial unindexed,
       title,
       article_type,
       arxiv_id,
       authors,
       abstract,
       link unindexed,
       pdf unindexed,
       nvotes unindexed,
       tokenize="porter unicode61"
);

-- create the required triggers to update the FTS index whenever stuff is
-- inserted, updated, or deleted from the arxiv table.
create trigger fts_before_update before update on arxiv begin
       delete from arxiv_fts where docid=old.rowid;
end;

create trigger fts_before_delete before delete on arxiv begin
       delete from arxiv_fts where docid=old.rowid;
end;

create trigger fts_after_update after update on arxiv begin
       insert into arxiv_fts(docid, utcdate, day_serial, title, article_type,
                             arxiv_id, authors, abstract, link, pdf, nvotes)
              values (new.rowid, new.utcdate, new.day_serial,
                      new.title, new.article_type, new.arxiv_id,
                      new.authors,
                      new.abstract, new.link, new.pdf,
                      new.nvotes);
end;

create trigger fts_after_insert after insert on arxiv begin
       insert into arxiv_fts(docid, utcdate, day_serial, title, article_type,
                             arxiv_id, authors, abstract, link, pdf, nvotes)
              values (new.rowid, new.utcdate, new.day_serial,
                      new.title, new.article_type, new.arxiv_id,
                      new.authors,
                      new.abstract, new.link, new.pdf,
                      new.nvotes);
end;



-- SQLite specific settings
pragma journal_mode = wal;
pragma journal_size_limit = 52428800;
