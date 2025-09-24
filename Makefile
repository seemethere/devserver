.PHONY: build
build:
	$(MAKE) -C bastion build

.PHONY: deploy
deploy: build
	$(MAKE) -C bastion deploy