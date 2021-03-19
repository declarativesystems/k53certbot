SHELL := /bin/bash

git_rev := $(shell git rev-parse --short HEAD)
# remove leading 'v'
# the currently checked out tag or nothing
git_tag := $(shell git tag --points-at HEAD 2> /dev/null | cut -c 2- | grep -E '.+')

# version number from pyproject.toml less any +GITREV
base_version := $(shell awk -F" = " '/version/  {gsub(/"/, "") ; split($$2, a, "+"); print a[1]}' pyproject.toml)

ci_image_name := quay.io/declarativesystems/k53certbot

ifdef git_tag
	# on a release tag
	final_version = $(git_tag)
	container_version = $(git_tag)
else
	# snapshot build
	final_version = $(base_version)+$(git_rev)
	container_version = $(base_version)-$(git_rev)
endif

install:
	poetry install

test: install patch_version
	poetry run pytest

clean:
	rm -rf dist
	rm k53certbot/version.py

dist: patch_version
	poetry build

image_build: dist
	buildah bud --format docker -t $(ci_image_name):$(container_version) --build-arg K53CERTBOT_VERSION=$(final_version) .

shell:
	podman run --rm -v $(shell pwd):/mnt --entrypoint /bin/bash -ti $(ci_image_name):$(container_version)

print_version:
	@echo $(final_version)

ci_image_push:
	podman push $(ci_image_name):$(container_version)

upload_artifactory: test dist
	poetry publish -vvv --repository pypi

# shell inside the CI container
ci_shell:
	@echo "project files will be available at /mnt"
	podman run --rm -v $(shell pwd):/mnt -ti \
		--privileged \
		$(shell yq e '.pipelines.[0].configuration.runtime.image.custom.name' pipelines.yml):$(shell yq e '.pipelines.[0].configuration.runtime.image.custom.tag' pipelines.yml) \
		/bin/bash

patch_version:
	# patch pyproject.toml with GITREV if not on a release tag
	sed -i '/^version =/ c\version = "$(final_version)"\' pyproject.toml

	# generate a regular version.py file so we can know our version
	echo "# generated file, do not edit!" > k53certbot/version.py
	echo "__version__ = \"$(final_version)\"" >> k53certbot/version.py
