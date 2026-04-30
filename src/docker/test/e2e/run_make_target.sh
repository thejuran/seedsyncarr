#!/usr/bin/env bash
# Run Docker-image end-to-end tests from Makefile with explicit shell state.
# This keeps the target portable on hosts whose make does not support .ONESHELL.
set -euo pipefail

red=$(tput setaf 1 2>/dev/null || true)
green=$(tput setaf 2 2>/dev/null || true)
reset=$(tput sgr0 2>/dev/null || true)

: "${SOURCEDIR:?SOURCEDIR must be set}"
: "${DEFAULT_STAGING_REGISTRY:?DEFAULT_STAGING_REGISTRY must be set}"
: "${E2E_SSH_KEY:?E2E_SSH_KEY must be set}"

if [[ -z "${STAGING_VERSION:-}" ]]; then
  echo "${red}ERROR: STAGING_VERSION must be set${reset}"
  exit 1
fi
if [[ -z "${SEEDSYNCARR_ARCH:-}" ]]; then
  echo "${red}ERROR: SEEDSYNCARR_ARCH is required (amd64 or arm64)${reset}"
  exit 1
fi
if [[ "${SEEDSYNCARR_ARCH}" != "amd64" && "${SEEDSYNCARR_ARCH}" != "arm64" ]]; then
  echo "${red}ERROR: SEEDSYNCARR_ARCH must be amd64 or arm64${reset}"
  exit 1
fi

STAGING_REGISTRY="${STAGING_REGISTRY:-${DEFAULT_STAGING_REGISTRY}}"
SEEDSYNCARR_PLATFORM="linux/${SEEDSYNCARR_ARCH}"
export STAGING_REGISTRY STAGING_VERSION SEEDSYNCARR_ARCH SEEDSYNCARR_PLATFORM E2E_SSH_KEY

echo "${green}STAGING_REGISTRY=${STAGING_REGISTRY}${reset}"
echo "${green}SEEDSYNCARR_PLATFORM=${SEEDSYNCARR_PLATFORM}${reset}"

docker_cmd() {
  DOCKER_BUILDKIT=1 docker "$@"
}

docker_compose() {
  COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 docker compose "$@"
}

# Removing and pulling is the only way to select the arch from a multi-arch image.
docker_cmd rmi -f "${STAGING_REGISTRY}:${STAGING_VERSION}" || true
docker_cmd pull "${STAGING_REGISTRY}:${STAGING_VERSION}" --platform "linux/${SEEDSYNCARR_ARCH}"

echo "${green}Building remote container for platform ${SEEDSYNCARR_PLATFORM}${reset}"
# DOCKSEC-05: Generate ephemeral SSH key pair for E2E test (always fresh).
rm -f "${E2E_SSH_KEY}" "${E2E_SSH_KEY}.pub"
ssh-keygen -t ed25519 -N "" -f "${E2E_SSH_KEY}" -q || {
  echo "${red}ERROR: ssh-keygen failed${reset}" >&2
  exit 1
}

# The app image runs as uid/gid 1000; keep the private key 0600 but readable by that user when bind-mounted.
chmod 600 "${E2E_SSH_KEY}"
if command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
  sudo chown 1000:1000 "${E2E_SSH_KEY}"
elif chown 1000:1000 "${E2E_SSH_KEY}" 2>/dev/null; then
  true
else
  echo "${red}WARNING: could not chown ${E2E_SSH_KEY} to uid/gid 1000; continuing for non-Linux Docker hosts${reset}" >&2
fi
E2E_SSH_PUBKEY=$(cat "${E2E_SSH_KEY}.pub")

docker_cmd buildx build \
  --platform "${SEEDSYNCARR_PLATFORM}" \
  --load \
  -t seedsyncarr/test/e2e/remote \
  --build-arg "SSH_PUBKEY=${E2E_SSH_PUBKEY}" \
  -f "${SOURCEDIR}/docker/test/e2e/remote/Dockerfile" \
  .

compose_files=(
  -f "${SOURCEDIR}/docker/test/e2e/compose.yml"
  -f "${SOURCEDIR}/docker/stage/docker-image/compose.yml"
)
compose_run_flags=()
if [[ "${DEV:-}" == "1" ]]; then
  compose_files+=( -f "${SOURCEDIR}/docker/test/e2e/compose-dev.yml" )
else
  compose_run_flags+=( -d )
fi
printf '%sCOMPOSE_FILES=%s%s\n' "${green}" "${compose_files[*]}" "${reset}"

tear_down() {
  docker_compose "${compose_files[@]}" stop || true
}
trap tear_down EXIT

echo "${green}Building the tests${reset}"
docker_compose "${compose_files[@]}" build tests configure

# This suppresses the docker-compose error that image has changed.
docker_compose "${compose_files[@]}" rm -f myapp

echo "${green}Running the tests${reset}"
docker_compose "${compose_files[@]}" up --force-recreate "${compose_run_flags[@]}"

if [[ "${DEV:-}" != "1" ]]; then
  docker logs -f seedsyncarr_test_e2e
fi

echo "${green}=== Logs from myapp container ===${reset}"
docker logs seedsyncarr_test_e2e_myapp 2>&1 || echo "No myapp logs found"

exit_code=$(docker inspect seedsyncarr_test_e2e | jq '.[].State.ExitCode')
if [[ "${exit_code}" != "0" ]]; then
  false
fi
