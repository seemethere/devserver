.PHONY: deploy clean deploy-operator deploy-bastion

deploy:
	make -C bastion deploy
	make -C devserver-operator deploy

TEST_VENV := .venv-e2e
PYTHON := $(TEST_VENV)/bin/python
PIP := $(TEST_VENV)/bin/pip

$(PYTHON):
	@echo "--> Setting up virtual environment for E2E tests..."
	@rm -rf $(TEST_VENV)
	@python3 -m venv $(TEST_VENV)
	@echo "--> Installing dependencies..."
	@$(PIP) install --upgrade pip
	@$(PIP) install -r tests/requirements.txt
	@$(PIP) install -e cli
	@echo "--> Setup complete. Run 'make test-e2e' to start the tests."

.PHONY: test-e2e
test-e2e: $(PYTHON)
	@echo "--> Running E2E tests..."
	@$(PYTHON) -m pytest -v tests/e2e/test_lifecycle.py
	@echo "--> E2E tests finished."

.PHONY: test-e2e-clean
test-e2e-clean:
	@echo "--> Cleaning up E2E test virtual environment..."
	@rm -rf $(TEST_VENV)
	@echo "--> Cleanup complete."
