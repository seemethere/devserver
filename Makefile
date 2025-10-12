# Conditional pytest flags based on VERBOSE environment variable
VERBOSE ?= 0
MAX_JOBS ?= 4
PYTEST_VERBOSE = $(if $(filter 1,$(VERBOSE)),-s,)
PYTEST_PARALLEL_JOBS = $(if $(MAX_JOBS),-n $(MAX_JOBS),)
VENV_BIN = .venv/bin
PYTHON = $(VENV_BIN)/python3
PIP = $(VENV_BIN)/pip3
PRECOMMIT = $(VENV_BIN)/pre-commit
PYTEST = $(PYTHON) -m pytest

$(PYTHON):
	@echo "🐍 No virtual environment found, creating one..."
	uv venv -p 3.13 .venv
	$(PYTHON) -m ensurepip
	$(PIP) install -e .
	$(PIP) install -e .[dev]

.PHONY: test
test: $(PYTHON)
	@echo "🧪 Running tests$(if $(MAX_JOBS), with $(MAX_JOBS) parallel jobs,)$(if $(filter 1,$(VERBOSE)), with verbose output,)... (use VERBOSE=1 for detailed output, MAX_JOBS=<n> for parallel tests)"
	$(PYTEST) $(PYTEST_PARALLEL_JOBS) -v $(PYTEST_VERBOSE) tests

.PHONY: install-crds
install-crds: #TODO: List crd file glob to re-run this on file changes
	@echo "🔄 Installing CRDs..."
	kubectl apply -f crds/

.PHONY: run
run:
	@echo "🏃 Running operator..."
	$(PYTHON) -m devserver.operator

DOCKER_REGISTRY :=
DOCKER_IMAGE := $(DOCKER_REGISTRY)seemethere/devserver

.PHONY: docker-build
docker-build:
	@echo "🏗️ Building Docker image..."
	docker build -t $(DOCKER_IMAGE) .

.PHONY: docker-push
docker-push:
	@echo "🔄 Pushing Docker image..."
	docker push $(DOCKER_IMAGE)

.PHONY: pre-commit
pre-commit:
	@echo "🔄 Running pre-commit checks..."
	$(PRECOMMIT) run --all-files
