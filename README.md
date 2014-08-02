### astroph-coffee - A simple platform for astro-ph arXiv discussion

This server helps organize astro-ph discussion by providing a way for people to
see local papers and vote on papers they want to talk about. It has the
following components:

* backend with arxiv scraping
* article abstract and metadata storage in sqlite3
* frontend built with tornado for viewing and voting on papers
* an archive of previous astro-ph discussions


Everyone gets five votes to use in total per day, with one per paper. The server
generally operates in two modes:

1. Vote mode: this is active whenever the voting period is active (defined in
   `src/conf/astroph.conf`). Papers are shown in their serial number order as on
   the astro-ph list page, and users can vote on papers they'd like to see
   talked about.

   ![Voting mode image](src/static/images/voting-th.png?raw=true)


2. Display mode: this is active outside the voting period. Local papers are
   highlighted at the top of the page with their full abstracts. Papers with at
   least one vote are shown below papers with local authors, in order of the
   number of votes they received. Finally, all other papers are listed below the
   local and voted papers.

   ![Display mode image](src/static/images/listing-th.png?raw=true)


An archive of all paper astracts is also provided in reverse chronological
order, grouped by month and year to make it easy to see what people were
interested in talking about on previous days.

See the INSTALL.md file for instructions on how to install and run the
server. If you have questions or problems, please let me know.
