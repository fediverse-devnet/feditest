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
BRANCH:=$(shell git branch --show-current)
VENV:=venv.$(UNAME).$(BRANCH)
PYTHON:=python

build : venv
	$(VENV)/bin/pip install .

venv : $(VENV)

$(VENV) :
	@which $(PYTHON) || echo 'No executable called "python". Run with "PYTHON=your-python"'
	$(PYTHON) -mvenv $(VENV)
	$(VENV)/bin/pip install ruff mypy pylint

lint : venv
	$(VENV)/bin/ruff check src
	$(VENV)/bin/mypy src
	$(VENV)/bin/pylint src

test : venv
	$(VENV)/bin/pytest -v


release :
	@which $(PYTHON) || echo 'No executable called "python". Run with "PYTHON=your-python"'
	[[ -d venv.release ]] && rm -rf venv.release || true
	[[ -d dist ]] && rm -rf dist || true
	$(PYTHON) -mvenv venv.release
	venv.release/bin/pip install twine
	venv.release/bin/pip install --upgrade build
	venv.release/bin/python -m build
	@echo WARNING: YOU ARE NOT DONE YET
	@echo The actual push to pypi.org you need to do manually. Enter:
	@echo venv.release/bin/twine upload dist/*

.PHONY: venv build lint test release
