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

.PHONY: test
test:
	.venv/bin/python3 -m pytest -v tests