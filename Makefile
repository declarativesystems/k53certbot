IMAGE_TAG := latest
IMAGE_NAME := declarativesystems.jfrog.io/docker/docker-local/k53certbot
IMAGE_VERSION := $(IMAGE_NAME):$(IMAGE_TAG)
K53CERTBOT_VERSION := $(shell python k53certbot/version.py)


test:
	pipenv run pytest

package:
	python setup.py bdist_wheel

upload:
	python -m twine upload dist/*

clean:
	rm -rf build
	rm -rf dist

dev_env:
	pip install -e .

requirements.txt:
	pipenv run pip freeze >> requirements.txt

image: package
	podman build . -t $(IMAGE_VERSION) --build-arg K53CERTBOT_VERSION=$(K53CERTBOT_VERSION)

shell:
	podman run --rm -v $(shell pwd):/mnt --entrypoint /bin/bash -ti $(IMAGE_VERSION)

print_version:
	@python k53certbot/version.py
