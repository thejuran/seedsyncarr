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
	# Check our settings
	@if [[ -z "${STAGING_VERSION}" ]] ; then \
		echo "${red}ERROR: STAGING_VERSION must be set${reset}"; exit 1; \
	fi
	@if [[ -z "${SEEDSYNCARR_ARCH}" ]] ; then \
		echo "${red}ERROR: SEEDSYNCARR_ARCH is required (amd64 or arm64)${reset}"; exit 1; \
	fi
	@if [[ -z "${STAGING_REGISTRY}" ]] ; then \
		export STAGING_REGISTRY="${DEFAULT_STAGING_REGISTRY}"; \
	fi;
	echo "${green}STAGING_REGISTRY=$${STAGING_REGISTRY}${reset}";
	export SEEDSYNCARR_PLATFORM="linux/$${SEEDSYNCARR_ARCH}";
	echo "${green}SEEDSYNCARR_PLATFORM=$${SEEDSYNCARR_PLATFORM}${reset}";
	# Removing and pulling is the only way to select the arch from a multi-arch image
	$(DOCKER) rmi -f $${STAGING_REGISTRY}:$${STAGING_VERSION}
	$(DOCKER) pull $${STAGING_REGISTRY}:$${STAGING_VERSION} --platform linux/$${SEEDSYNCARR_ARCH}
	echo "${green}Building remote container for platform $${SEEDSYNCARR_PLATFORM}${reset}";
	# DOCKSEC-05: Generate ephemeral SSH key pair for E2E test (always fresh)
	rm -f $(E2E_SSH_KEY) $(E2E_SSH_KEY).pub
	ssh-keygen -t ed25519 -N "" -f $(E2E_SSH_KEY) -q || { echo "${red}ERROR: ssh-keygen failed${reset}" >&2; exit 1; }
	E2E_SSH_PUBKEY=$$(cat $(E2E_SSH_KEY).pub)
	$(DOCKER) buildx build \
		--platform $${SEEDSYNCARR_PLATFORM} \
		--load \
		-t seedsyncarr/test/e2e/remote \
		--build-arg SSH_PUBKEY="$${E2E_SSH_PUBKEY}" \
		-f ${SOURCEDIR}/docker/test/e2e/remote/Dockerfile \
		.

	export E2E_SSH_KEY=$(E2E_SSH_KEY)
	# Set the flags
	COMPOSE_FLAGS="-f ${SOURCEDIR}/docker/test/e2e/compose.yml "
	COMPOSE_FLAGS+="-f ${SOURCEDIR}/docker/stage/docker-image/compose.yml "
	COMPOSE_RUN_FLAGS=""
	if [[ "${DEV}" = "1" ]] ; then
		COMPOSE_FLAGS+="-f ${SOURCEDIR}/docker/test/e2e/compose-dev.yml "
	else \
  		COMPOSE_RUN_FLAGS+="-d"
	fi
	echo "${green}COMPOSE_FLAGS=$${COMPOSE_FLAGS}${reset}"

	# Set up Ctrl-C handler
	function tearDown {
		$(DOCKER_COMPOSE) \
			$${COMPOSE_FLAGS} \
			stop
	}
	trap tearDown EXIT

	# Build the test (exclude remote — already built above with SSH_PUBKEY)
	echo "${green}Building the tests${reset}"
	$(DOCKER_COMPOSE) \
		$${COMPOSE_FLAGS} \
		build tests configure

	# This suppresses the docker-compose error that image has changed
	$(DOCKER_COMPOSE) \
		$${COMPOSE_FLAGS} \
		rm -f myapp

	# Run the test
	echo "${green}Running the tests${reset}"
	$(DOCKER_COMPOSE) \
		$${COMPOSE_FLAGS} \
		up --force-recreate \
		$${COMPOSE_RUN_FLAGS}

	if [[ "${DEV}" != "1" ]] ; then
		$(DOCKER) logs -f seedsyncarr_test_e2e
	fi

	# Show logs from myapp container for debugging
	echo "${green}=== Logs from myapp container ===${reset}"
	$(DOCKER) logs seedsyncarr_test_e2e_myapp 2>&1 || \
		echo "No myapp logs found"

	EXITCODE=`$(DOCKER) inspect seedsyncarr_test_e2e | jq '.[].State.ExitCode'`
	if [[ "$${EXITCODE}" != "0" ]] ; then
		false
	fi

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
