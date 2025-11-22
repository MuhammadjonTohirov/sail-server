#!/usr/bin/env bash

set -euo pipefail

# Start or (re)create an OpenSearch container on a fixed host port.
#
# Usage:
#   ./scripts/opensearch_up.sh [CONTAINER_NAME] [HOST_PORT]
# Defaults:
#   CONTAINER_NAME = opensearch-dev
#   HOST_PORT = 9200

CONTAINER_ID_OR_NAME=${1:-opensearch-dev}
HOST_PORT=${2:-9200}
CONTAINER_PORT=9200
DIAG_PORT=9600

echo "Target container: ${CONTAINER_ID_OR_NAME}"
echo "Desired host port: ${HOST_PORT} -> ${CONTAINER_PORT}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker is not installed or not in PATH" >&2
  exit 1
fi

# Check if the container exists, if not create a new one
if ! docker inspect "${CONTAINER_ID_OR_NAME}" >/dev/null 2>&1; then
  echo "Container '${CONTAINER_ID_OR_NAME}' not found. Creating new OpenSearch container..."
  IMAGE="opensearchproject/opensearch:latest"
  NAME="${CONTAINER_ID_OR_NAME}"
  RUNNING="false"
  CURRENT_HOST_PORT=""
else
  IMAGE=$(docker inspect -f '{{.Config.Image}}' "${CONTAINER_ID_OR_NAME}")
  NAME=$(docker inspect -f '{{.Name}}' "${CONTAINER_ID_OR_NAME}" | sed 's#^/##')
  RUNNING=$(docker inspect -f '{{.State.Running}}' "${CONTAINER_ID_OR_NAME}" 2>/dev/null || echo false)
  CURRENT_HOST_PORT=$(docker inspect -f '{{with (index .HostConfig.PortBindings "9200/tcp")}}{{(index . 0).HostPort}}{{end}}' "${CONTAINER_ID_OR_NAME}" 2>/dev/null || true)
fi

echo "Base image: ${IMAGE}"
echo "Container name: ${NAME} (running=${RUNNING})"
echo "Current 9200 mapping: ${CURRENT_HOST_PORT:-<none>}"

# If mapping already matches and container can just be started, do that.
if [[ -n "${CURRENT_HOST_PORT}" && "${CURRENT_HOST_PORT}" == "${HOST_PORT}" ]]; then
  if [[ "${RUNNING}" != "true" ]]; then
    echo "Starting existing container '${NAME}' with correct port mapping..."
    docker start "${CONTAINER_ID_OR_NAME}"
  else
    echo "Container '${NAME}' already running on port ${HOST_PORT}."
  fi
  echo "OK: OpenSearch should be available at http://localhost:${HOST_PORT}"
  exit 0
fi

if [[ -n "${CURRENT_HOST_PORT}" ]]; then
  echo "Existing container does not have desired port mapping."
  echo "Creating a new container with a stable mapping to host port ${HOST_PORT}..."
else
  echo "Creating new container with port mapping to host port ${HOST_PORT}..."
fi

# Choose a deterministic new name
if [[ -n "${CURRENT_HOST_PORT}" ]]; then
  NEW_NAME="${NAME}-p${HOST_PORT}"
  
  # If a container with NEW_NAME exists, append a timestamp
  if docker inspect "${NEW_NAME}" >/dev/null 2>&1; then
    TS=$(date +%s)
    NEW_NAME="${NEW_NAME}-${TS}"
  fi
  
  echo "New container name: ${NEW_NAME}"
  
  # Stop the old container if it's running (we won't delete it automatically)
  if [[ "${RUNNING}" == "true" ]]; then
    echo "Stopping existing container '${NAME}' (leaving it in place)..."
    docker stop "${CONTAINER_ID_OR_NAME}" >/dev/null
  fi
else
  # Container doesn't exist, use the original name
  NEW_NAME="${NAME}"
  echo "Container name: ${NEW_NAME}"
fi

set -x
docker run -d \
  --name "${NEW_NAME}" \
  -p "${HOST_PORT}:${CONTAINER_PORT}" \
  -p "${DIAG_PORT}:${DIAG_PORT}" \
  -e "discovery.type=single-node" \
  -e "OPENSEARCH_INITIAL_ADMIN_PASSWORD=\$OpenSear4" \
  -e "DISABLE_INSTALL_DEMO_CONFIG=true" \
  -e "DISABLE_SECURITY_PLUGIN=true" \
  "${IMAGE}"
set +x

echo "OK: Started '${NEW_NAME}'."
echo "OpenSearch should be reachable at: http://localhost:${HOST_PORT}"
echo "Note: Security plugin is disabled for development ease"
echo "If using this with Django, set OPENSEARCH_URL=http://localhost:${HOST_PORT} in your .env"

exit 0

