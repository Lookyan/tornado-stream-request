PYTHON=python3
PYTHONPATH=./
SOURCE_DIR=./
TESTS_DIR=./tests
PYPI_NAME?=pypi

all: help

help:
	@echo "install      - install python package"
	@echo "test         - run tests"
	@echo "test-deps    - install test dependencies"
	@echo "upload       - upload source distribution tarball to PYPI"

install:
	$(PYTHON) setup.py install

test:
	$(PYTHON) -m unittest discover $(TESTS_DIR) -v

deps:
	pip install -r ./requirements.txt

test-deps:
	pip install -r ./test-requirements.txt

upload:
	$(PYTHON) ./setup.py sdist upload -r $(PYPI_NAME)

