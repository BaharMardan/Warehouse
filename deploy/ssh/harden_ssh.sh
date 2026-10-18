#!/usr/bin/env bash
# Limit SSH on an Ubuntu server of this project to one or two named admin users.
#
#   sudo bash deploy/ssh/harden_ssh.sh bahar            # only bahar may log in over SSH
#   sudo bash deploy/ssh/harden_ssh.sh bahar second     # two admins
#   sudo bash deploy/ssh/harden_ssh.sh bahar --tunnel-user parsa   # backend VM: keep the backup tunnel
#   sudo bash deploy/ssh/harden_ssh.sh --rollback       # undo
#
# What it does: writes /etc/ssh/sshd_config.d/00-warehouse-hardening.conf (it wins over
# 50-cloud-init.conf because sshd uses the first value it reads), checks the result with
# `sshd -t`, then RELOADS sshd. Open sessions stay alive.
#
# It refuses to run unless every listed user exists and has a public key in
# ~/.ssh/authorized_keys, because it also turns password login off.
#
# Port forwarding is left on: on the backend server the nightly backup connects as the
# admin user with a restricted key (from=, permitopen=127.0.0.1:1521) to tunnel to Oracle.
set -euo pipefail

CONF=/etc/ssh/sshd_config.d/00-warehouse-hardening.conf
BACKUP_DIR=/etc/ssh/warehouse-hardening-backup

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }

reload_ssh() {
  sshd -t
  systemctl reload ssh 2>/dev/null || systemctl reload sshd
}

if [ "${1:-}" = "--rollback" ]; then
  rm -f "$CONF"
  reload_ssh
  echo "Hardening removed. SSH is back to the previous settings."
  exit 0
fi

users=()
tunnel=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --tunnel-user) tunnel="${2:-}"; [ -n "$tunnel" ] || { echo "--tunnel-user needs a name."; exit 1; }; shift 2 ;;
    *) users+=("$1"); shift ;;
  esac
done
[ "${#users[@]}" -ge 1 ] && [ "${#users[@]}" -le 2 ] || { echo "Give one or two admin usernames."; exit 1; }

for user in "${users[@]}"; do
  [[ "$user" =~ ^[a-z_][a-z0-9_-]*$ ]] || { echo "Invalid username: $user"; exit 1; }
  [ "$user" != root ] || { echo "Do not allow root to log in over SSH."; exit 1; }
  home="$(getent passwd "$user" | cut -d: -f6)"
  [ -n "$home" ] || { echo "User $user does not exist."; exit 1; }
  # A key restricted with command= or restrict (the backup tunnel key) cannot open a shell,
  # so it does not count as a way for the admin to log in.
  { grep -Ev '^[[:space:]]*(#|$)' "$home/.ssh/authorized_keys" 2>/dev/null || true; } |
    grep -Ev 'restrict|command=' | grep -Eq '(^|[[:space:]])(ssh-|ecdsa-|sk-)' ||
    { echo "$user has no unrestricted public key in $home/.ssh/authorized_keys; refusing to turn passwords off."; exit 1; }
done

# The backup tunnel account may log in, but only with restricted keys: it must have no
# key that opens a shell, otherwise it is a second admin by accident.
if [ -n "$tunnel" ]; then
  [[ "$tunnel" =~ ^[a-z_][a-z0-9_-]*$ ]] && [ "$tunnel" != root ] || { echo "Invalid tunnel user: $tunnel"; exit 1; }
  thome="$(getent passwd "$tunnel" | cut -d: -f6)"
  [ -n "$thome" ] || { echo "User $tunnel does not exist."; exit 1; }
  { grep -Ev '^[[:space:]]*(#|$)' "$thome/.ssh/authorized_keys" 2>/dev/null || true; } | grep -q 'restrict\|command=' ||
    { echo "$tunnel has no restricted backup key in $thome/.ssh/authorized_keys."; exit 1; }
  if { grep -Ev '^[[:space:]]*(#|$)' "$thome/.ssh/authorized_keys" || true; } |
       grep -Ev 'restrict|command=' | grep -Eq '(^|[[:space:]])(ssh-|ecdsa-|sk-)'; then
    echo "WARNING: $tunnel still has an unrestricted key in $thome/.ssh/authorized_keys. Remove it so only the backup key remains."
  fi
fi

install -d -m 700 "$BACKUP_DIR"
[ ! -f "$CONF" ] || cp -a "$CONF" "$BACKUP_DIR/00-warehouse-hardening.conf.$(date +%Y%m%d%H%M%S)"

cat > "$CONF" <<EOF
# Managed by deploy/ssh/harden_ssh.sh
AllowUsers ${users[*]}${tunnel:+ $tunnel}
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
MaxAuthTries 3
LoginGraceTime 30
X11Forwarding no
AllowAgentForwarding no
EOF
chmod 644 "$CONF"

if ! sshd -t; then
  rm -f "$CONF"
  echo "sshd rejected the configuration; nothing was changed."
  exit 1
fi

# Show what sshd will really apply to each allowed user (the first value read wins).
for user in "${users[@]}"; do
  sshd -T -C "user=$user,host=localhost,addr=127.0.0.1" | grep -Ei '^(allowusers|permitrootlogin|passwordauthentication) '
done

reload_ssh
cat <<EOF

SSH is now limited to: ${users[*]}${tunnel:+ $tunnel (backup tunnel key only)}
BEFORE you close this session, open a NEW terminal and log in again as one of them.
If it fails, run here:  sudo bash deploy/ssh/harden_ssh.sh --rollback
EOF
