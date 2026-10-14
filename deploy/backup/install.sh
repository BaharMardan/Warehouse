#!/usr/bin/env bash
# Install the nightly warehouse backup on the BACKUP VM.
# Run as root from the repository root:   sudo bash deploy/backup/install.sh
# Works offline: python-oracledb is installed from deploy-wheels/ (built for Python 3.12).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON="${PYTHON:-python3.12}"
APP=/opt/warehouse-backup
DATA=/var/backups/warehouse
CONF=/etc/warehouse-backup

[ "$(id -u)" -eq 0 ] || { echo "Run as root (sudo)."; exit 1; }
command -v ssh >/dev/null || { echo "Install openssh-client first."; exit 1; }
command -v "$PYTHON" >/dev/null || { echo "$PYTHON not found. deploy-wheels/ is built for Python 3.12."; exit 1; }
"$PYTHON" -c 'import venv, zoneinfo; zoneinfo.ZoneInfo("Asia/Tehran")' \
  || { echo "$PYTHON lacks venv or the Asia/Tehran zone (install python3.12-venv and tzdata)."; exit 1; }

echo "== service user and folders"
id warehouse-backup >/dev/null 2>&1 || \
  useradd --system --home-dir "$DATA" --no-create-home --shell /usr/sbin/nologin warehouse-backup
install -d -o warehouse-backup -g warehouse-backup -m 700 "$DATA"
install -d -o root -g warehouse-backup -m 750 "$CONF"
install -d -m 755 "$APP" "$APP/backend"

echo "== code (no .env, no tests)"
for f in backup_warehouse.py extract_schema.py export_live_migration.py import_live_migration.py run_sql.py; do
  install -m 644 "$REPO/backend/$f" "$APP/backend/$f"
done

echo "== python environment (offline)"
[ -x "$APP/venv/bin/python" ] || "$PYTHON" -m venv "$APP/venv"
"$APP/venv/bin/pip" install --quiet --no-index --find-links "$REPO/deploy-wheels" oracledb

echo "== configuration"
if [ ! -f "$CONF/backup.env" ]; then
  install -o root -g warehouse-backup -m 640 "$REPO/deploy/backup/backup.env.example" "$CONF/backup.env"
  echo "   created $CONF/backup.env  <-- EDIT IT (password, DB VM address) before the first run"
else
  echo "   kept existing $CONF/backup.env"
fi

echo "== restricted SSH tunnel"
if [ ! -f "$CONF/ssh_config" ]; then
  install -o root -g warehouse-backup -m 640 "$REPO/deploy/backup/ssh_config.example" "$CONF/ssh_config"
fi
if [ ! -f "$CONF/ssh_key" ]; then
  ssh-keygen -q -t ed25519 -N "" -C warehouse-backup-oracle -f "$CONF/ssh_key"
  chown warehouse-backup:warehouse-backup "$CONF/ssh_key"
  chmod 600 "$CONF/ssh_key"
fi
install -m 644 "$REPO/deploy/backup/warehouse-backup-tunnel.service" /etc/systemd/system/
echo "   authorize ssh_key.pub on Ubuntu 1 and verify its host key before starting"

echo "== systemd timer"
install -m 644 "$REPO/deploy/backup/warehouse-backup.service" /etc/systemd/system/
install -m 644 "$REPO/deploy/backup/warehouse-backup.timer" /etc/systemd/system/
systemctl daemon-reload
# Enable/start only after credentials, SSH authorization, and the first real backup work.
systemd-analyze calendar --iterations=2 '*-*-* 21:00:00 Asia/Tehran' || true
echo
echo "Clock check (must match Tehran wall-clock time): $(TZ=Asia/Tehran date '+%F %H:%M %Z')"
echo
echo "Next: edit $CONF/backup.env, then test once with:"
echo "   follow deploy/backup/README.md to authorize the tunnel, test, then start the timer"
