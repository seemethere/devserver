IMAGE_NAME=devserver/bastion
IMAGE_TAG=phase2
FULL_IMAGE=$(IMAGE_NAME):$(IMAGE_TAG)

.PHONY: build
build:
	docker build -f Dockerfile -t $(FULL_IMAGE) ../

.PHONY: push
push: build
	docker push $(FULL_IMAGE)

.PHONY: clean
clean:
	docker rmi $(FULL_IMAGE)

.PHONY: deploy
deploy: build
	./scripts/deploy-bastion.sh

.PHONY: test
test: deploy
	./scripts/test-ssh.sh

.PHONY: expose-bastion
expose-bastion:
	kubectl port-forward -n devserver-bastion services/bastion 2222:22

ssh-bastion:
	ssh -i ../.demo-keys/bastion_demo testuser@localhost -p 2222
