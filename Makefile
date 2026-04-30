# Copyright 2017, Inderpreet Singh, All rights reserved.

# Catch sigterms
# See: https://stackoverflow.com/a/52159940
export SHELL:=/bin/bash
export SHELLOPTS:=$(if $(SHELLOPTS),$(SHELLOPTS):)pipefail:errexit
.ONESHELL:

# Color outputs
red=`tput setaf 1`
green=`tput setaf 2`
reset=`tput sgr0`

ROOTDIR:=$(shell realpath .)
SOURCEDIR:=$(shell realpath ./src)
BUILDDIR:=$(shell realpath ./build)
DEFAULT_STAGING_REGISTRY:=localhost:5000

#DOCKER_BUILDKIT_FLAGS=BUILDKIT_PROGRESS=plain
DOCKER=${DOCKER_BUILDKIT_FLAGS} DOCKER_BUILDKIT=1 docker
DOCKER_COMPOSE=${DOCKER_BUILDKIT_FLAGS} COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 docker compose
E2E_SSH_KEY=/tmp/e2e_test_key

.PHONY: docker-image clean coverage-python

all: docker-image

docker-buildx:
	$(DOCKER) run --rm --privileged multiarch/qemu-user-static --reset -p yes

docker-image: docker-buildx
	@if [[ -z "${STAGING_REGISTRY}" ]] ; then \
		export STAGING_REGISTRY="${DEFAULT_STAGING_REGISTRY}"; \
	fi;
	echo "${green}STAGING_REGISTRY=$${STAGING_REGISTRY}${reset}";
	@if [[ -z "${STAGING_VERSION}" ]] ; then \
		export STAGING_VERSION="latest"; \
	fi;
	echo "${green}STAGING_VERSION=$${STAGING_VERSION}${reset}";

	# Single-step build — docker-image/Dockerfile is self-contained
	$(DOCKER) buildx build \
		-f ${SOURCEDIR}/docker/build/docker-image/Dockerfile \
		--target seedsyncarr_run \
		--tag $${STAGING_REGISTRY}:$${STAGING_VERSION} \
		--cache-to=type=registry,ref=$${STAGING_REGISTRY}:cache,mode=max \
		--cache-from=type=registry,ref=$${STAGING_REGISTRY}:cache \
		--platform linux/amd64,linux/arm64 \
		--push \
		${ROOTDIR}

docker-image-release:
	@if [[ -z "${STAGING_REGISTRY}" ]] ; then \
		export STAGING_REGISTRY="${DEFAULT_STAGING_REGISTRY}"; \
	fi;
	echo "${green}STAGING_REGISTRY=$${STAGING_REGISTRY}${reset}";
	@if [[ -z "${STAGING_VERSION}" ]] ; then \
		export STAGING_VERSION="latest"; \
	fi;
	echo "${green}STAGING_VERSION=$${STAGING_VERSION}${reset}";
	@if [[ -z "${RELEASE_REGISTRY}" ]] ; then \
		echo "${red}ERROR: RELEASE_REGISTRY is required${reset}"; exit 1; \
	fi
	@if [[ -z "${RELEASE_VERSION}" ]] ; then \
		echo "${red}ERROR: RELEASE_VERSION is required${reset}"; exit 1; \
	fi
	echo "${green}RELEASE_REGISTRY=${RELEASE_REGISTRY}${reset}"
	echo "${green}RELEASE_VERSION=${RELEASE_VERSION}${reset}"

	# Single-step build — docker-image/Dockerfile is self-contained
	$(DOCKER) buildx build \
		-f ${SOURCEDIR}/docker/build/docker-image/Dockerfile \
		--target seedsyncarr_run \
		--tag ${RELEASE_REGISTRY}/seedsyncarr:${RELEASE_VERSION} \
		--cache-from=type=registry,ref=$${STAGING_REGISTRY}:cache \
		--platform linux/amd64,linux/arm64 \
		--push \
		${ROOTDIR}

tests-python:
	# python run
	@CACHE_FLAGS=""; \
	if [ -n "$(PYTHON_TEST_CACHE_REGISTRY)" ]; then \
		CACHE_FLAGS="--cache-from type=registry,ref=$(PYTHON_TEST_CACHE_REGISTRY):cache-python-test --cache-to type=registry,ref=$(PYTHON_TEST_CACHE_REGISTRY):cache-python-test,mode=max"; \
	fi; \
	$(DOCKER) buildx build \
		-f ${SOURCEDIR}/docker/build/docker-image/Dockerfile \
		--target seedsyncarr_run_python_devenv \
		--tag seedsyncarr/run/python/devenv \
		--load \
		$$CACHE_FLAGS \
		${ROOTDIR}
	# python tests — force default builder so compose can see the locally-loaded base image
	BUILDX_BUILDER=default $(DOCKER_COMPOSE) \
		-f ${SOURCEDIR}/docker/test/python/compose.yml \
		build

run-tests-python: tests-python
	BUILDX_BUILDER=default $(DOCKER_COMPOSE) \
		-f ${SOURCEDIR}/docker/test/python/compose.yml \
		up --force-recreate --exit-code-from tests

tests-angular:
	# angular build
	$(DOCKER) build \
		-f ${SOURCEDIR}/docker/build/docker-image/Dockerfile \
		--target seedsyncarr_build_angular_env \
		--tag seedsyncarr/build/angular/env \
		${ROOTDIR}
	# angular tests
	$(DOCKER_COMPOSE) \
		-f ${SOURCEDIR}/docker/test/angular/compose.yml \
		build

run-tests-angular: tests-angular
	$(DOCKER_COMPOSE) \
		-f ${SOURCEDIR}/docker/test/angular/compose.yml \
		up --force-recreate --exit-code-from tests

run-tests-e2e:
	STAGING_VERSION="$(STAGING_VERSION)" \
	SEEDSYNCARR_ARCH="$(SEEDSYNCARR_ARCH)" \
	STAGING_REGISTRY="$(STAGING_REGISTRY)" \
	DEV="$(DEV)" \
	SOURCEDIR="${SOURCEDIR}" \
	DEFAULT_STAGING_REGISTRY="${DEFAULT_STAGING_REGISTRY}" \
	E2E_SSH_KEY="$(E2E_SSH_KEY)" \
		bash ${SOURCEDIR}/docker/test/e2e/run_make_target.sh

run-remote-server:
	$(DOCKER) container rm -f seedsyncarr_test_e2e_remote-dev
	$(DOCKER) run \
		-it --init \
		-p 1234:1234 \
		--name seedsyncarr_test_e2e_remote-dev \
		seedsyncarr/test/e2e/remote

coverage-python:
	cd ${SOURCEDIR}/python && poetry run pytest --cov --cov-report=term-missing --cov-report=html

clean:
	rm -rf ${BUILDDIR}
