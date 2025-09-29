# The name of our k3d cluster
CLUSTER_NAME := devserver-operator-dev

.PHONY: up
up:
	@echo "🚀 Creating k3d cluster '$(CLUSTER_NAME)'..."
	@k3d cluster create $(CLUSTER_NAME) --wait
	@echo "✅ Cluster '$(CLUSTER_NAME)' is ready."

.PHONY: down
down:
	@echo "🔥 Deleting k3d cluster '$(CLUSTER_NAME)'..."
	@k3d cluster delete $(CLUSTER_NAME)
	@echo "✅ Cluster '$(CLUSTER_NAME)' deleted."

.PHONY: kubeconfig
kubeconfig:
	@echo "📋 Getting kubeconfig for cluster '$(CLUSTER_NAME)'..."
	@k3d kubeconfig get $(CLUSTER_NAME)

# Conditional pytest flags based on VERBOSE environment variable
PYTEST_VERBOSE = $(if $(filter 1,$(VERBOSE)),-s,)
PYTHON = .venv/bin/python3
PYTEST = $(PYTHON) -m pytest

$(PYTHON):
	@echo "🐍 No virtual environment found, creating one..."
	uv venv -p 3.13 .venv
	uv pip install -e .

.PHONY: test
test:
	@echo "🧪 Running tests$(if $(filter 1,$(VERBOSE)), with verbose output,) (use VERBOSE=1 for detailed output)..."
	timeout 90 $(PYTEST) -v $(PYTEST_VERBOSE) tests