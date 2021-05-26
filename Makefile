ID6_DOCKER_TAG = docker-push.ocf.berkeley.edu/synapse:latest

.PHONY: cook-image
cook-image:
	docker build --pull -f Dockerfile -t $(ID6_DOCKER_TAG) .

.PHONY: push-image
push-image:
	docker push $(ID6_DOCKER_TAG)