.PHONY: deploy
deploy:
	$(MAKE) -C bastion deploy
	$(MAKE) -C devserver-operator deploy
