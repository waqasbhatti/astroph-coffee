# directory where you want lcserver modules installed
BINDIR=test-run

# this is the path to the final location of the fts5 extension
FTSPATH=$(BINDIR)/fts5.so

# this checks if FTS5 is already present
HAVE_FTS5=$(shell sqlite3 '' 'pragma compile_options' | grep FTS5)

# check if FTS5 is not present and compile the extension if needed
ifndef $(HAVE_FTS)
# insert the fts5 extension location into the top of the sql script
FTS_LOAD=".load $(FTSPATH)"
endif


# this are the Python activate/deactivate scripts for virtualenv
ACTIVATE_SCRIPT=$(BINDIR)/bin/activate
DEACTIVATE_SCRIPT=$(BINDIR)/bin/deactivate

.PHONY: install uninstall clean update

all: install

install:
	# create python virtualenv in the run directory
	# no system-site packages to keep all requirements in-house
	virtualenv $(BINDIR)

	# create the logs and pids directories
	mkdir -p $(BINDIR)/logs
	mkdir -p $(BINDIR)/pids
	mkdir -p $(BINDIR)/cache

	# copy over our files
	rsync -auv ./src/* $(BINDIR)

	#compile the sqlite3 fts extension
	cc -g -fPIC -shared -O2 $(BINDIR)/fts5.c -o $(BINDIR)/fts5.so

	# insert the load statement into the sql script
	echo $(FITS_LOAD) | cat - ./src/data/astroph-sqlite.sql > $(BINDIR)/data/astroph-sqlite.sql

	# make the database using the sqlite3 command
	sqlite3 $(BINDIR)/data/astroph.sqlite < $(BINDIR)/data/astroph-sqlite.sql

	# install our python dependencies
	./shell/install_extern.sh $(BINDIR)

	@echo 'astroph-coffee server installed to:'
	@echo $(value BINDIR)
	@echo 'use the following script to activate the environment:'
	@echo $(ACTIVATE_SCRIPT)
	@echo 'use the following script to deactivate the environment:'
	@echo $(DEACTIVATE_SCRIPT)
	@echo 'Read the INSTALL file to see how to run the server'

uninstall:
	# remove stuff from the run directory
	rm -rf $(BINDIR)

clean:
	rm -f $(BINDIR)/*.pyc
	# run python setup.py clean on the extern directories

update:
	# copy over the source files
	rsync -auv ./src/* $(BINDIR)
