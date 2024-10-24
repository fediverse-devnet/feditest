#
# make venv
#     Create a python environment for your platform and install the required dependencies int
#     it. It will be in ./venv.linux.default if you are Linux
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

UNAME?=$(shell uname -s | tr [A-Z] [a-z])
TAG?=default
VENV?=venv.$(UNAME).$(TAG)
PYTHON?=python3.11
FEDITEST?=$(VENV)/bin/feditest -v
DOMAIN?=--domain 1234.lan


default : lint

all : lint tests

build : venv
	$(VENV)/bin/pip install .

venv : $(VENV)

$(VENV) :
	@which $(PYTHON) || ( echo 'No executable called "python". Append your python to the make command, like "make PYTHON=your-python"' && false )
	$(PYTHON) -mvenv $(VENV)
	$(VENV)/bin/pip install ruff mypy pylint

lint : build
	$(VENV)/bin/ruff check src
	MYPYPATH=src $(VENV)/bin/mypy --namespace-packages --explicit-package-bases --install-types --non-interactive src
	@# These options should be the same flags as in .pre-commit-config.yml, except that I can't get it to
	@# work there without the "--ignore-missing-imports" flag, while it does work without it here

	@# MYPYPATH is needed because apparently some type checking ignores the directory option given as command-line argument
	@# $(VENV)/bin/pylint src

tests : tests.unit tests.smoke

tests.unit :
	$(VENV)/bin/pytest -v

tests.smoke : tests.smoke.webfinger tests.smoke.api tests.smoke.fediverse

tests.smoke.webfinger :
	$(FEDITEST) run --testsdir tests.smoke/tests --session tests.smoke/webfinger.session.json --node client=tests.smoke/imp.node.json --node server=tests.smoke/wordpress.ubos.node.json $(DOMAIN)
	$(FEDITEST) run --testsdir tests.smoke/tests --session tests.smoke/webfinger.session.json --node client=tests.smoke/imp.node.json --node server=tests.smoke/mastodon.ubos.node.json $(DOMAIN)

tests.smoke.api :
	$(FEDITEST) run --testsdir tests.smoke/tests --session tests.smoke/mastodon_api.session.json --node server=tests.smoke/wordpress.ubos.node.json $(DOMAIN)
	$(FEDITEST) run --testsdir tests.smoke/tests --session tests.smoke/mastodon_api.session.json --node server=tests.smoke/mastodon.ubos.node.json $(DOMAIN)

tests.smoke.fediverse :
	$(FEDITEST) run --testsdir tests.smoke/tests --session tests.smoke/mastodon_api_mastodon_api.session.json --node leader_node=tests.smoke/mastodon.ubos.node.json --node follower_node=tests.smoke/mastodon.ubos.node.json $(DOMAIN)
	$(FEDITEST) run --testsdir tests.smoke/tests --session tests.smoke/mastodon_api_mastodon_api.session.json --node leader_node=tests.smoke/wordpress.ubos.node.json --node follower_node=tests.smoke/mastodon.ubos.node.json $(DOMAIN)

release :
	@which $(PYTHON) || ( echo 'No executable called "python". Append your python to the make command, like "make PYTHON=your-python"' && false )
	[[ -d venv.release ]] && rm -rf venv.release || true
	[[ -d dist ]] && rm -rf dist || true
	$(PYTHON) -mvenv venv.release
	venv.release/bin/pip install twine
	venv.release/bin/pip install --upgrade build
	venv.release/bin/python -m build
	@echo WARNING: YOU ARE NOT DONE YET
	@echo The actual push to pypi.org you need to do manually. Enter:
	@echo venv.release/bin/twine upload dist/*

.PHONY: all default venv build lint tests tests.unit tests.smoke tests.smoke.webfinger tests.smoke.api tests.smoke.fediverse release
