#!/usr/bin/env bash
# One-time preparation on Ubuntu 2. Registration uses GitHub's private token locally.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

apt-get -o Acquire::ForceIPv4=true update
apt-get -o Acquire::ForceIPv4=true install -y curl git rsync
id warehouse-deploy >/dev/null 2>&1 ||
  useradd --system --create-home --home-dir /opt/warehouse-runner \
    --shell /bin/bash warehouse-deploy

install -d -o warehouse-deploy -g warehouse-deploy -m 755 /opt/warehouse-runner
install -d -o warehouse-deploy -g warehouse-deploy -m 755 /var/www/warehouse
chown -R warehouse-deploy:warehouse-deploy /var/www/warehouse
install -d -o warehouse-deploy -g warehouse-deploy -m 700 /var/lib/warehouse-frontend
install -o root -g root -m 755 "$HERE/publish.sh" /usr/local/bin/warehouse-publish-frontend

echo "Frontend publisher installed. Existing frontend files were retained."
echo "Next: register the GitHub runner as warehouse-deploy with label warehouse-frontend."
echo "No sudo privileges or Docker access were granted to warehouse-deploy."
