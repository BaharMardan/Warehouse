# Frontend deployment to Ubuntu 2

Current deployment:
- Frontend/Nginx: 192.168.1.32, root /var/www/warehouse.
- Backend and Oracle: 192.168.1.31; Nginx forwards /api/ to port 8000.
- Backups: 192.168.1.33.
- SSH administration login: parsa.

GitHub Actions builds on a GitHub-hosted Ubuntu machine using Node 22 and
VITE_API_URL=/api. A dedicated self-hosted runner on Ubuntu 2 downloads that
build and publishes it locally. No inbound internet port or SSH secret in
GitHub is required. Ubuntu 2 needs outbound HTTPS access to GitHub, the runner
download endpoints and artifact storage. No npm downloads happen on Ubuntu 2.

Only main pushes affecting frontend files or this deployment setup deploy.
Manual workflow dispatch is also allowed on main. Pull requests never run the
production deployment job. The runner account is warehouse-deploy, which has
no sudo or Docker privileges and can update the static frontend.
Use a private repository where possible and allow only trusted maintainers to
push/merge workflow changes to main.

## Deploy the current local build

The prepared archive is in Downloads/warehouse-frontend-update.tar.gz.
From Windows PowerShell:

~~~powershell
scp "$env:USERPROFILE\Downloads\warehouse-frontend-update.tar.gz" parsa@192.168.1.32:/home/parsa/
~~~

First complete the one-time publisher preparation below. Then on Ubuntu 2,
extract into a new deployment folder and publish as the dedicated account:

~~~bash
(
  set -e
  build_dir=$(sudo mktemp -d /var/lib/warehouse-frontend/manual.XXXXXX)
  sudo tar -xzf ~/warehouse-frontend-update.tar.gz -C "$build_dir"
  sudo chown -R warehouse-deploy:warehouse-deploy "$build_dir"
  sudo -u warehouse-deploy /usr/local/bin/warehouse-publish-frontend "$build_dir"
)
~~~

The publisher checks Nginx and restores the previous index if that check fails.
Do not chown the web root back to root after installing the publisher.
Static-file updates do not require reloading Nginx.

## One-time runner preparation

Copy the prepared Downloads/warehouse-frontend-actions-setup.tar.gz to Ubuntu 2:

~~~powershell
scp "$env:USERPROFILE\Downloads\warehouse-frontend-actions-setup.tar.gz" parsa@192.168.1.32:/home/parsa/
~~~

On Ubuntu 2:

~~~bash
mkdir -p ~/warehouse-frontend-actions-setup
tar -xzf ~/warehouse-frontend-actions-setup.tar.gz -C ~/warehouse-frontend-actions-setup
sudo bash ~/warehouse-frontend-actions-setup/deploy/frontend/install.sh
~~~

The installer prepares a dedicated service account, publication permissions,
and a root-owned publishing helper. It retains existing website files.
It does not register the runner or start deployment before registration.

## Register the runner (token stays private)

1. Open the Warehouse repository on GitHub.
2. Settings > Actions > Runners > New self-hosted runner.
3. Choose Linux / x64.
4. On Ubuntu 2, switch to the dedicated account:

~~~bash
sudo -iu warehouse-deploy
~~~

5. Run the Download commands shown by GitHub. They create actions-runner under
   /opt/warehouse-runner and download/extract the current runner release.
   Use GitHub's current commands/checksum rather than a hard-coded release.
6. Run the Configure command shown by GitHub, adding:

~~~text
--name warehouse-frontend --labels warehouse-frontend
~~~

The command should use --url https://github.com/BaharMardan/Warehouse.
The registration token expires; enter it only in this terminal, never chat or git.
Leave the default _work folder. Do not run ./run.sh if installing the service below.
If runner dependencies are missing, leave the account shell and run the
downloaded bin/installdependencies.sh using sudo, then configure again.

7. Return to parsa and install/start the service:

~~~bash
exit
cd /opt/warehouse-runner/actions-runner
sudo ./svc.sh install warehouse-deploy
sudo ./svc.sh start
sudo ./svc.sh status
~~~

Confirm the runner is Idle in GitHub and has label warehouse-frontend.
The runner service starts automatically after the VM boots.

## Enable the workflow

Commit and push .github/workflows/deploy-frontend.yml, deploy/frontend/, and the
frontend changes to main. GitHub Actions builds, uploads, then deploys.
If a build already queued the deploy job while registering the runner, it
continues once the runner is online.
Future frontend pushes to main use the same process automatically.

The publisher validates the artifact, refuses links and .env files, copies assets,
and replaces index.html atomically. Old hashed assets remain available to browsers.
It verifies Nginx serves the expected index bytes through the domain's virtual host.
If that check fails, the previous index is restored. Public files such as favicon
images are updated in place; this is not a full versioned rollback of those files.
No automatic old-asset pruning is enabled.

The current health check uses local HTTP. If Nginx later redirects all HTTP to
HTTPS, adjust the publisher's health URL/Host configuration and test locally.

## Verify

On GitHub: Actions > Deploy frontend, require both build and deploy jobs green.
In a browser open http://192.168.1.32 and refresh with Ctrl+F5.
On Ubuntu 2:

~~~bash
curl --noproxy '*' -fsS -I -H 'Host: falatwarehouse.ir' http://127.0.0.1/
curl --noproxy '*' -fsS http://127.0.0.1/api/health/db -H 'Host: falatwarehouse.ir'
~~~

If a deploy job is waiting, check runner status/labels and outbound internet access.
If the installed publisher script changes, transfer and rerun the installer;
the unprivileged workflow intentionally cannot replace the root-owned helper.
No backend, Oracle, backup credentials, or database contents are deployed by this workflow.
