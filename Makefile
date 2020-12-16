SHELL := /bin/bash

BUILDAH_ISOLATION := chroot
export BUILDAH_ISOLATION

git_rev := $(shell git rev-parse --short HEAD)
# remove leading 'v'
# the currently checked out tag or 0.0.0=
git_tag := $(shell git describe --tags 2> /dev/null | cut -c 2- | grep -E '.+')

ci_image_name := quay.io/declarativesystems/k53certbot
K53CERTBOT_VERSION := $(shell python k53certbot/version.py)
ifdef git_tag
	# on a release tag
	final_version = $(git_tag)
else
	# snapshot build
	final_version = $(K53CERTBOT_VERSION)-$(git_rev)
endif


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

image_build: package
	buildah bud --format docker -t $(ci_image_name):$(final_version) --build-arg K53CERTBOT_VERSION=$(K53CERTBOT_VERSION) .

shell:
	podman run --rm -v $(shell pwd):/mnt --entrypoint /bin/bash -ti $(IMAGE_VERSION)

print_version:
	@python k53certbot/version.py

ci_image_push:
	podman push $(ci_image_name):$(final_version)