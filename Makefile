uname:=$(shell uname -s | tr [A-Z] [a-z])
bin:=venv.$(uname)/bin

build :
	$(bin)/pip install .

lint :
	$(bin)/ruff check src
	$(bin)/mypy src
	$(bin)/pylint src

.PHONY: build lint

