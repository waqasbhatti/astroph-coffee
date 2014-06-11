# set this to the directory where you want lcserver modules installed
BINDIR=./run

ACTIVATE_SCRIPT=$(BINDIR)/bin/activate
DEACTIVATE_SCRIPT=$(BINDIR)/bin/deactivate

.PHONY: install uninstall compile clean update

all: compile

install:
	# create python virtualenv in the run directory
	# no system-site packages to keep all requirements in-house
	virtualenv $(BINDIR)

	# create the logs and pids directories
	mkdir -p $(BINDIR)/logs
	mkdir -p $(BINDIR)/pids
	mkdir -p $(BINDIR)/cache


	# copy over our files
	rsync -au ./src/* $(BINDIR)

	# install our python dependencies
	./shell/install_extern.sh $(BINDIR)

	@echo 'astroph-coffee modules installed to:'
	@echo $(value BINDIR)
	@echo 'use the following script to activate the environment:'
	@echo $(ACTIVATE_SCRIPT)
	@echo 'use the following script to deactivate the environment:'
	@echo $(DEACTIVATE_SCRIPT)

uninstall:
	# remove stuff from the run directory
	rm -rf $(BINDIR)*

compile:

clean:
	rm -f $(BINDIR)/*.pyc
	# run python setup.py clean on the extern directories

update:
	# copy over the source files
	rsync -au ./src/* $(BINDIR)
