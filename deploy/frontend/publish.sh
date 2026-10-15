#!/usr/bin/env bash
# Run as warehouse-deploy (never sudo). Assets are copied before index.html.
set -euo pipefail
umask 022

source_dir="$(realpath "${1:?Usage: warehouse-publish-frontend BUILD_DIRECTORY}")"
web_root="${WAREHOUSE_WEB_ROOT:-/var/www/warehouse}"
state_dir="${WAREHOUSE_DEPLOY_STATE:-/var/lib/warehouse-frontend}"
health_url="${WAREHOUSE_HEALTH_URL:-http://127.0.0.1/}"
health_host="${WAREHOUSE_HEALTH_HOST:-falatwarehouse.ir}"

[ -s "$source_dir/index.html" ] || { echo "Missing or empty index.html"; exit 1; }
[ -d "$source_dir/assets" ] || { echo "Missing assets directory"; exit 1; }
# sudo may inherit parsa's private home, which warehouse-deploy cannot enter.
cd "$source_dir"
if ! symbolic_link="$(find "$source_dir" -type l -print -quit)"; then
  echo "Cannot inspect build for symbolic links; refusing to publish." >&2
  exit 1
fi
if [ -n "$symbolic_link" ]; then
  echo "Build contains symbolic links; refusing to publish."
  exit 1
fi
if ! environment_file="$(find "$source_dir" -name '.env*' -print -quit)"; then
  echo "Cannot inspect build for environment files; refusing to publish." >&2
  exit 1
fi
if [ -n "$environment_file" ]; then
  echo "Build contains an environment file; refusing to publish."
  exit 1
fi

mkdir -p "$web_root" "$state_dir"
exec 9>"$state_dir/deploy.lock"
flock -x 9
index_tmp=""
response_tmp=""
cleanup() {
  [ -z "$index_tmp" ] || rm -f -- "$index_tmp"
  [ -z "$response_tmp" ] || rm -f -- "$response_tmp"
}
trap cleanup EXIT

had_previous=false
if [ -f "$web_root/index.html" ]; then
  cp -- "$web_root/index.html" "$state_dir/previous-index.html"
  had_previous=true
fi

# Keep old hashed assets so already-open browsers can finish using the old build.
rsync -rt --chmod=D755,F644 --exclude='/index.html' --exclude='.*' \
  "$source_dir/" "$web_root/"
index_tmp="$(mktemp "$web_root/.index.XXXXXX")"
install -m 644 "$source_dir/index.html" "$index_tmp"
mv -f -- "$index_tmp" "$web_root/index.html"
index_tmp=""

response_tmp="$(mktemp "$state_dir/response.XXXXXX")"
if ! curl --noproxy '*' --fail --silent --show-error --max-time 20 \
    -H "Host: $health_host" "$health_url" > "$response_tmp" ||
   ! cmp -s "$source_dir/index.html" "$response_tmp"; then
  echo "Nginx did not serve the expected index.html."
  if "$had_previous"; then
    index_tmp="$(mktemp "$web_root/.index.XXXXXX")"
    install -m 644 "$state_dir/previous-index.html" "$index_tmp"
    mv -f -- "$index_tmp" "$web_root/index.html"
    index_tmp=""
    echo "Previous index restored; old hashed assets were preserved."
  fi
  exit 1
fi
printf 'FRONTEND DEPLOYED: %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
