.PHONY: help install-dev lint format typecheck test check pre-commit-install clean

PYTHON ?= python3.12
VENV ?= .venv
VENV_BIN = $(VENV)/bin

# Determine active binary directory (prefers active venv, then .venv, then PATH)
ifneq ($(VIRTUAL_ENV),)
	BIN := $(VIRTUAL_ENV)/bin/
else ifneq ($(wildcard $(CURDIR)/$(VENV_BIN)/python),)
	BIN := $(CURDIR)/$(VENV_BIN)/
else ifneq ($(wildcard $(VENV_BIN)/python),)
	BIN := $(CURDIR)/$(VENV_BIN)/
else
	BIN :=
endif

PYTHON_EXEC = $(BIN)python3
RUFF = $(BIN)ruff
MYPY = $(BIN)mypy
PYTEST = $(BIN)pytest
PRE_COMMIT = $(BIN)pre-commit

help:
	@echo "Agency Development Targets:"
	@echo "  make install-dev        - Initialize virtual environment and install backend dev dependencies"
	@echo "  make lint               - Run Ruff lint checks"
	@echo "  make format             - Run Ruff formatter"
	@echo "  make typecheck          - Run mypy strict type checks"
	@echo "  make test               - Run unit tests with pytest"
	@echo "  make check              - Run lint, typecheck, and test checks sequentially"
	@echo "  make pre-commit-install - Install Git pre-commit hooks"
	@echo "  make clean              - Remove virtualenv and temporary cache artifacts"

$(VENV):
	$(PYTHON) -m venv $(VENV)

UV := $(shell which uv 2>/dev/null)

install-dev: $(VENV)
ifneq ($(UV),)
	$(UV) pip install -e "backend[dev]" --python $(VENV_BIN)/python
else
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install -e "backend[dev]"
endif

lint:
	$(RUFF) check backend

format:
	$(RUFF) format backend

typecheck:
	cd backend && $(MYPY) src tests

test:
	cd backend && $(PYTEST) tests

check: lint typecheck test

pre-commit-install:
	$(PRE_COMMIT) install

clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
