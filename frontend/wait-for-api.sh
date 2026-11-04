#!/bin/sh
set -eu

api_target="${API_HOST:-}"
case "$api_target" in
  *:*)
    api_host="${api_target%:*}"
    api_port="${api_target##*:}"
    ;;
  *)
    echo "API_HOST must be set as hostname:port" >&2
    exit 1
    ;;
esac

if [ -z "$api_host" ] || [ -z "$api_port" ]; then
  echo "API_HOST must be set as hostname:port" >&2
  exit 1
fi

echo "Waiting for API at ${api_host}:${api_port}"
until nc -z -w 2 "$api_host" "$api_port"; do
  sleep 2
done
echo "API is reachable at ${api_host}:${api_port}"