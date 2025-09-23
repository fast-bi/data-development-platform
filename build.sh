#!/bin/bash
#

set -o errexit
catch() {
    echo 'catching!'
    if [ "$1" != "0" ]; then
    # error handling goes here
    echo "Error $1 occurred on $2"
    fi
}
trap 'catch $? $LINENO' EXIT

init_version="v0.0.1.2"

docker buildx build . \
  --pull \
  --tag europe-central2-docker.pkg.dev/fast-bi-common/bi-platform/tsb-fastbi-tenant-api-core:${init_version} \
  --platform linux/amd64 \
  --push
