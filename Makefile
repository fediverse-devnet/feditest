#
# make venv
#     Create a python environment for your platform and install the required dependencies int
#     it. It will be in ./venv.$(uname -s)
#
# make build
#     run pip install in your venv
#
# make lint
#     Run several linters on the code
#
# make test
#     Run unit tests
#
# NOTE: This does not add the venv to your $PATH. You have to do that yourself if you want that.
#

UNAME:=$(shell uname -s | tr [A-Z] [a-z])
VENV:=venv.$(UNAME)
PYTHON:=python

build : venv
	$(VENV)/bin/pip install .

venv : venv.$(UNAME)

venv.$(UNAME) :
	@which $(PYTHON) || echo 'No executable called "python". Run with "PYTHON=your-python"'
	$(PYTHON) -mvenv $(VENV)
	$(VENV)/bin/pip install ruff mypy pylint

lint : venv
	$(VENV)/bin/ruff check src
	$(VENV)/bin/mypy src
	$(VENV)/bin/pylint src

test : venv
	$(VENV)/bin/pytest -v

.PHONY: venv build lint test

