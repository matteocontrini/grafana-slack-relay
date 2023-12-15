#!/usr/bin/env bash
if [ -z "$VERSION" ]; then
  echo "VERSION is not set"
  exit 1
fi

docker build -t matteocontrini/grafana-slack-relay:$VERSION --platform linux/amd64 .
docker push matteocontrini/grafana-slack-relay:$VERSION
