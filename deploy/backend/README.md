# Backend deployment and future Oracle migrations

Ubuntu 1 runs API + Oracle; Ubuntu 2 runs Nginx/frontend; Ubuntu 3 pulls nightly backups.
GitHub builds an API image using the existing Linux Python 3.12 wheels. A dedicated
runner on Ubuntu 1 downloads it, then calls a root-owned restricted deploy helper.
No production .env, database exports, or credentials are sent to GitHub.

The development backend/docker-compose.yml and backend/Dockerfile are unchanged.
Production keeps /home/parsa/warehouse-deploy/compose.yaml and backend.env.
The installer adds a managed compose.override.yaml for the API image only.
It checks the current project, live schema, and absence of development source mounts.
An existing unmanaged Compose override makes installation stop for review.

## One-time installation

Windows PowerShell, with LAN access (turn off the VPN if it intercepts 192.168.1.*):

~~~powershell
scp "$env:USERPROFILE\Downloads\warehouse-backend-actions-setup.tar.gz" parsa@192.168.1.31:/home/parsa/
ssh parsa@192.168.1.31
~~~

Ubuntu 1, as parsa:

~~~bash
mkdir -p ~/warehouse-backend-actions-setup
tar -xzf ~/warehouse-backend-actions-setup.tar.gz -C ~/warehouse-backend-actions-setup
cd ~/warehouse-backend-actions-setup
sudo python3 deploy/backend/install.py
~~~

The installer creates warehouse-backend (/opt/warehouse-backend-runner), config
/etc/warehouse-backend-deploy/config.json and the root-owned deployment helper.
It does not recreate API/Oracle, import a database, edit backend.env, or install Docker.
Its sudo rule allows only that helper, which takes a full Git commit SHA.

## Register Ubuntu 1's runner

GitHub repository Settings > Actions > Runners > New self-hosted runner > Linux / x64.
Use the current download/checksum commands displayed by GitHub.

~~~bash
sudo -iu warehouse-backend
~~~

Run the Download commands in this shell. Run the Configure command with these
options appended: --name warehouse-backend --labels warehouse-backend
Accept Default for the runner group and _work for the work folder.
Keep registration tokens private. Do not run ./run.sh.

Run exit by itself, wait until the prompt returns to parsa, then run:

~~~bash
cd /opt/warehouse-backend-runner/actions-runner
sudo ./svc.sh install warehouse-backend
sudo ./svc.sh start
sudo ./svc.sh status
~~~

The runner must show Idle/online with warehouse-backend label in GitHub.
The service is enabled after reboot. No inbound internet port is needed for
Actions; the VM needs outbound HTTPS access to GitHub and artifact endpoints.
Only trusted maintainers should control this runner's repository workflows/code.

## Releases

Push backend app, dependency, new versioned migration or deploy/backend changes
to main. Deploy backend builds on GitHub, uploads a checksummed image, then
deploys on the warehouse-backend runner. Manual workflow dispatch is supported.
The runner intentionally does not have unrestricted Docker group membership.

API replacement causes a brief backend interruption. Schema releases pause API
writes while the backup and migrations run.

An API release uses Compose up --no-deps --no-build api with the managed image
override. Oracle is not recreated and its volume is not removed.
Production environment variables/passwords remain in the existing backend.env.
Do not replace production Compose with the development Compose file.
Do not run compose down -v or rebuild the old server-side Dockerfile to update.

For dependency changes, also refresh the Linux CPython 3.12 wheels in deploy-wheels.
The image build fails if those offline wheels cannot satisfy requirements.txt.
The normal container runs as uid/gid 65532. Application uploads currently live
in Oracle BLOB/CLOB columns; no new host upload directory is introduced.

## Migrations and recovery

Read backend/migrations/README.md. Historical add_*.py/migrate_*.py files are never
automatically replayed. No versioned migrations are initially installed.
Regular code-only releases perform a read-only migration plan and recreate API.
An unhealthy code-only release restores the previous image and fails the job.

When new versions are pending:
1. Check owner/history and pause API writes.
2. Write a verified logical schema/row backup into a NEW private folder under
   /var/lib/warehouse-backend-deploy/pre-migration on Ubuntu 1.
3. Apply new versions once, recording immutable hashes and status.
4. Start the new API and check /health/db inside its container.

A failed backup restores the previous API without executing migrations.
After migrations start, a failure leaves API stopped and writes needs-review.json.
Oracle DDL commits implicitly; image rollback cannot undo it. Do not delete the
review marker or rewrite history to force a retry. Inspect the failed change,
restore into WAREHOUSE_RESTORE and verify, or prepare an explicit forward fix.
Never drop the live user before proving a restore.

Pre-migration backups are on Ubuntu 1 and supplement the existing Ubuntu 3 nightly
backup. They are not automatically copied off-host or pruned. Monitor disk space
and retain/copy the required recovery archives. Avoid overlapping schema releases
with the 21:00 Tehran nightly backup; its DDL/row snapshot must remain consistent.
There is no automatic monthly restore drill or automatic rollback of database data.

After a safe test restore, migration testing can use the release image and a
private restore.env whose owner is WAREHOUSE_RESTORE:

~~~bash
sudo docker run --rm --network warehouse_default \
  --env-file /path/to/private/restore.env \
  warehouse-api:git-REPLACE_WITH_FULL_COMMIT \
  python /code/run_migrations.py --plan --target-schema WAREHOUSE_RESTORE
~~~

Apply to that disposable restored schema only after its backup is verified, with
--apply --backup-confirmed --target-schema WAREHOUSE_RESTORE. Check the resulting
schema/data and application behavior before releasing real migration files.

## Verification

GitHub Actions > Deploy backend: both jobs must pass.
On Ubuntu 1:

~~~bash
sudo cat /var/lib/warehouse-backend-deploy/last_success.json
cd ~/warehouse-deploy
sudo docker compose ps
~~~

From the frontend VM, check the full proxy path:
curl --noproxy '*' -fsS -H 'Host: falatwarehouse.ir' http://127.0.0.1/api/health/db

If the deploy helper or installer changes, install the updated setup package on
Ubuntu 1. The unprivileged runner cannot replace its root-owned helper automatically.

## IP changes

Public modem IP changes do not require a new database migration or runner
registration. LAN access continues if the local network/VM addresses stay the
same. For internet access, update the domain A record to the new public IPv4
(or use a DNS provider's dynamic DNS), and verify modem TCP 80/443 forwarding.
The registrar nameserver fields contain DNS-provider hostnames, not the web IP.
Behind ISP carrier-grade NAT, DNS alone cannot provide inbound connectivity.

If local VM addresses change, review:
- Ubuntu 2 /etc/nginx/sites-available/warehouse: proxy_pass backend address;
  server_name local IP if the frontend changes. nginx -t, then reload.
- Ubuntu 1 production compose.yaml API port binding if it names 192.168.1.31.
  Update relevant host firewall source allowlists if present.
- Ubuntu 3 /etc/warehouse-backup/ssh_config: HostName backend address.
  Update ssh_known_hosts after verifying the same backend host fingerprint.
- Ubuntu 1 parsa's authorized_keys restricted backup key: from=192.168.1.33
  if the backup VM's source address changes.
- ESXi management address, VM netplan addresses/gateway/DNS and modem forwarding
  destinations when moving to a different LAN subnet.
- GitHub frontend environment URL is a display link; update it if frontend IP changes.

The frontend calls relative /api, so changing IP does not itself require a new
frontend build. Oracle uses Docker's oracle service name internally.
Keep/reserve stable LAN addresses .31, .32 and .33 where possible. If moving the
physical ESXi server, a different modem may use a different LAN subnet/gateway.
