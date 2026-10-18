# Limiting SSH to one or two admin users

Run on each Ubuntu server (backend 192.168.1.31, frontend 192.168.1.32, backup 192.168.1.33):

Backend VM (Ubuntu 1, it has the nightly backup tunnel coming in as `parsa`):

```bash
sudo bash deploy/ssh/harden_ssh.sh bahar --tunnel-user parsa
```

Frontend VM (Ubuntu 2) and backup VM (Ubuntu 3):

```bash
sudo bash deploy/ssh/harden_ssh.sh bahar
```

Before running it, `bahar` must exist on that VM, be in the `sudo` group and have your public key:

```bash
sudo adduser bahar && sudo usermod -aG sudo bahar
sudo install -d -m 700 -o bahar -g bahar /home/bahar/.ssh
# put your public key (one line) in /home/bahar/.ssh/authorized_keys, mode 600, owner bahar
```

`--tunnel-user parsa` keeps `parsa` allowed but only for the restricted backup key. Remove any
normal key from `/home/parsa/.ssh/authorized_keys`, so only the backup line remains.

It allows only the listed users, forbids root and password login (keys only), checks the
result with `sshd -t` and reloads sshd. Open sessions stay alive.
**Before closing your session, log in again from a new terminal.** To undo:
`sudo bash deploy/ssh/harden_ssh.sh --rollback`.

Things that keep working:

- **GitHub deployments.** The runners (`warehouse-backend`, `warehouse-deploy`) call out to
  GitHub; nobody SSHes in to deploy, so they need no SSH access.
- **The nightly backup tunnel.** Ubuntu 3 connects to Ubuntu 1 as `parsa` with a restricted key
  (`from=192.168.1.33,restrict,permitopen=127.0.0.1:1521`). Keep `parsa` in the allowed users on
  the backend server, and do not set `AllowTcpForwarding no`.

## What this does not protect

SSH limits who can log in. It does not stop anyone who already has these:

- **root or `sudo`**: remove anyone who does not need it (`getent group sudo`).
- **the `docker` group** (equivalent to root; it can read the API image with the code): `getent group docker`.
- **the GitHub repository and runner token**: keep the repo private, require two-factor sign-in,
  limit collaborators, and use branch protection on `main`.
- **the server console and the hypervisor.**
- **the frontend**: the built JavaScript is served to every browser, so it can never be secret.

Also worth doing: allow port 22 only from the admins' machines, for example
`sudo ufw allow from 192.168.1.50 to any port 22 proto tcp` (replace with the admin address).
