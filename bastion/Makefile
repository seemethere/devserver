IMAGE_NAME=devserver/bastion
IMAGE_TAG=phase2
FULL_IMAGE=$(IMAGE_NAME):$(IMAGE_TAG)

build:
	docker build -f Dockerfile -t $(FULL_IMAGE) ../

push:
	docker push $(FULL_IMAGE)

clean:
	docker rmi $(FULL_IMAGE)

deploy:
	./scripts/deploy-bastion.sh

test:
	./scripts/test-ssh.sh