# Nightly backup on Ubuntu 3

- Ubuntu 1, 192.168.1.31: backend and Oracle; Oracle stays bound to localhost.
- Ubuntu 2, 192.168.1.32: frontend.
- Ubuntu 3, 192.168.1.33: backup job and archive storage.
- SSH login on all VMs: parsa.

This is a Python logical export, not Oracle Data Pump. It needs no Oracle client.
Database-stored uploads (BLOBs), Persian text (CLOBs), users/password hashes,
and all FA_* application tables are included. No separate application upload
directories exist in the current code. OS settings, application secrets, external
files and non-table objects such as stored packages are not included.
Preserve server configuration separately.

Rows are read in a single READ ONLY transaction. Schema DDL is captured separately:
avoid schema migrations during a backup. Reads need sufficient Oracle undo retention;
a snapshot-too-old error fails the job without pruning previous backups.

Archives are checksummed and re-opened before publication. Existing archive names
are never overwritten. Retention keeps the newest 30 archives plus the first backup
from each of the newest 12 months containing backups. Failed exports do not prune
published archives. One lock prevents overlapping runs.

The backup VM initiates an SSH tunnel to Ubuntu 1. Oracle port 1521 stays private.
The SSH key is restricted to forwarding to Oracle and cannot open a shell.
Ubuntu 1 receives only a public key. No key granting access to Ubuntu 3 is installed
on Ubuntu 1. The Oracle schema-owner credential is needed for USER_* and
DBMS_METADATA: the code is read-only, but that credential itself can write.
Keep it and the archives private.

## 1. Prepare Ubuntu 3

Power on Ubuntu 3 and enable its ESXi autostart.
Connect from Windows with ssh parsa@192.168.1.33.

On Ubuntu 3:

~~~bash
sudo cp -an /etc/apt/sources.list /etc/apt/sources.list.before-backup
sudo sed -i '\|^[[:space:]]*deb .*file:/*cdrom|s|^|# disabled: |' /etc/apt/sources.list
sudo apt -o Acquire::ForceIPv4=true update
sudo apt -o Acquire::ForceIPv4=true install -y python3.12-venv tzdata openssh-client
timedatectl status
mkdir -p ~/warehouse-backup-setup
chmod 700 ~/warehouse-backup-setup
~~~

Stop if installation fails. Ubuntu 24.04 supplies Python 3.12.
The offline wheels target Linux x86-64/Python 3.12.

## 2. Transfer and install

The deployment archive contains only backup code/configuration and wheels,
not .env files or migration exports. From Windows PowerShell:

~~~powershell
scp "$env:USERPROFILE\Downloads\warehouse-backup-setup.tar.gz" parsa@192.168.1.33:/home/parsa/
~~~

On Ubuntu 3:

~~~bash
tar -xzf ~/warehouse-backup-setup.tar.gz -C ~/warehouse-backup-setup
cd ~/warehouse-backup-setup
sudo bash deploy/backup/install.sh
~~~

Installation does not enable or start a new timer before configuration.
Existing enabled timers are preserved during updates.
Rerunning updates code while preserving credentials and SSH keys.

## 3. Authorize the restricted SSH tunnel

On Ubuntu 3:

~~~bash
sudo cat /etc/warehouse-backup/ssh_key.pub
~~~

Copy this PUBLIC key (never ssh_key).
On Ubuntu 1, logged in as parsa, append one line to ~/.ssh/authorized_keys:

~~~text
from="192.168.1.33",restrict,port-forwarding,permitopen="127.0.0.1:1521",command="/bin/false" ssh-ed25519 REPLACE_WITH_PUBLIC_KEY_DATA warehouse-backup-oracle
~~~

Use the actual public key data from Ubuntu 3. Preserve existing keys.
Prepare directory/file permissions:

~~~bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
nano ~/.ssh/authorized_keys
~~~

On Ubuntu 1, obtain its host fingerprint:

~~~bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
~~~

On Ubuntu 3, obtain the candidate host key:

~~~bash
ssh-keyscan -T 10 -t ed25519 192.168.1.31 > ~/backend-host-key
ssh-keygen -lf ~/backend-host-key
~~~

Compare fingerprints. Only if they match:

~~~bash
sudo install -o root -g warehouse-backup -m 640 ~/backend-host-key /etc/warehouse-backup/ssh_known_hosts
sudo systemctl enable --now warehouse-backup-tunnel.service
sudo systemctl status warehouse-backup-tunnel.service --no-pager
~~~

If it fails, use sudo journalctl -u warehouse-backup-tunnel -n 40 --no-pager.
Keep Ubuntu 1's Oracle port mapping at 127.0.0.1:1521:1521.

## 4. Configure and test

On Ubuntu 1, print only the ACTIVE backend schema:

~~~bash
cd ~/warehouse-deploy
python3 - <<'PY'
from pathlib import Path
values = dict(line.split("=", 1) for line in Path("backend.env").read_text().splitlines() if "=" in line)
print("Active schema:", values["ORACLE_USER"])
PY
~~~

On Ubuntu 3:

~~~bash
sudo nano /etc/warehouse-backup/backup.env
~~~

Set ORACLE_USER to the active schema (normally WAREHOUSE_LIVE). Enter its Oracle
password privately: this is the database password in backend.env, not the bahar
web-login password. Keep ORACLE_DSN=127.0.0.1:11521/FREEPDB1 through the SSH tunnel.
Do not paste the config or password in chat or commit it.

~~~bash
sudo systemctl start warehouse-backup.service
sudo journalctl -u warehouse-backup.service -n 80 --no-pager
sudo cat /var/backups/warehouse/last_success.json
~~~

Require BACKUP OK and expected live table counts.
Checksums validate archive bytes, not a real restore. Perform a restore drill in
an empty WAREHOUSE_RESTORE schema before relying on the backups.

After the first real backup succeeds:

~~~bash
sudo systemctl enable --now warehouse-backup.timer
systemctl list-timers warehouse-backup.timer --no-pager
systemd-analyze calendar '*-*-* 21:00:00 Asia/Tehran'
~~~

Daily schedule: 21:00 Asia/Tehran (17:30 UTC with current timezone rules).
Persistent=true catches a missed run after reboot. NEXT may display the VM's
timezone; calendar output confirms the scheduled timezone.
Ensure NTP/time synchronization and current tzdata are working.
The service retries failed jobs every five minutes, including while Oracle starts
following an ESXi reboot. Stop it while fixing configuration if needed.

## Restore drill and recovery

Restore into a NEW EMPTY WAREHOUSE_RESTORE schema in the current Oracle instance,
or WAREHOUSE_RESTORE_202610 for a dated monthly drill. Do not DROP the live user.
The importer checks ORACLE_USER against --target-schema and refuses a destination
with ANY existing objects. It never changes backend.env or switches the backend.

1. Create the chosen restore schema on Ubuntu 1 using the container's createAppUser
   command, with a privately generated password. It needs CREATE SESSION, CREATE
   TABLE, CREATE SEQUENCE, CREATE TRIGGER and storage quota.
2. Check the archive checksum with sha256sum -c and extract to a fresh private
   directory (mode 700) readable by warehouse-backup. Do not extract into production
   paths. Database uploads/password hashes are inside the bundle.
3. Create /etc/warehouse-backup/restore.env privately (root-owned, mode 600):
   ORACLE_USER=WAREHOUSE_RESTORE, its new ORACLE_PASSWORD, and
   ORACLE_DSN=127.0.0.1:11521/FREEPDB1. The SSH tunnel must be running.
4. Run on Ubuntu 3, replacing the bundle path:

~~~bash
sudo systemd-run --wait --pipe --collect \
  -p User=warehouse-backup -p Group=warehouse-backup \
  -p EnvironmentFile=/etc/warehouse-backup/restore.env \
  /opt/warehouse-backup/venv/bin/python \
  /opt/warehouse-backup/backend/import_live_migration.py \
  --bundle /var/backups/warehouse/restore-drill/EXTRACTED_BUNDLE \
  --target-schema WAREHOUSE_RESTORE
~~~

Use the same dated schema name in ORACLE_USER and --target-schema if applicable.
Require RESTORE VERIFIED, then test login and application queries against the
restored schema using a separate test backend. Production keeps using its existing
schema throughout the drill.

5. For actual recovery, switch backend.env's ORACLE_USER and ORACLE_PASSWORD to
   the verified restored schema, then recreate the API container. Keep the original
   schema and a private copy of backend.env for rollback. Never rename or delete
   the live schema as a prerequisite for validation.

The legacy default target remains WAREHOUSE_LIVE for compatibility, and it must
still be empty. New drills should explicitly use --target-schema WAREHOUSE_RESTORE.
Monthly drills are manual; no automatic monthly restore timer is installed.

## Object coverage check

Run as the active Oracle schema owner:

~~~sql
SELECT object_type, COUNT(*) FROM user_objects GROUP BY object_type ORDER BY object_type;
~~~

TABLE, INDEX, TRIGGER and standalone SEQUENCE are captured for the application.
Internal LOB objects are represented by their owning columns, with CLOB/BLOB
contents in the row files. Non-FA tables, views, procedures, functions, packages,
synonyms, jobs, and grants are not captured. Table-only objects do not prove grants
are absent. Review object inventory before relying on this as the only backup.
If application code depends on omitted objects or grants, extend the exporter or
add a separately configured Oracle Data Pump backup; that layer is not installed.

## Another storage location

Ubuntu 3 on the same ESXi datastore does not protect against loss of that datastore.
Copy archives to another machine/storage at least weekly. They contain password
hashes and customer data: use private access and encrypted transport.
Do not store the SSH private key on Ubuntu 1 or publish the archive directory.
