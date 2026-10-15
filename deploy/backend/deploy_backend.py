#!/usr/bin/python3
"""Root-owned deploy helper. Its only caller-controlled argument is a Git commit SHA."""
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time

STATE = Path("/var/lib/warehouse-backend-deploy")
CONFIG = Path("/etc/warehouse-backend-deploy/config.json")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
MARKER = "x-warehouse-backend-managed"


def write_json(path, value, mode=0o600):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".warehouse-")
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_manifest(manifest, commit):
    image = "warehouse-api:git-" + commit
    if manifest.get("commit") != commit or manifest.get("image") != image:
        raise RuntimeError("Release does not match requested commit/image.")
    if not re.fullmatch("[0-9a-f]{64}", manifest.get("sha256", "")):
        raise RuntimeError("Invalid image checksum.")
    return image


def validate_archive(path, expected_image):
    # Do not let docker load replace arbitrary tags such as the Oracle image.
    with tarfile.open(path, "r:gz") as archive:
        member = archive.getmember("manifest.json")
        if not member.isfile() or member.size > 65536:
            raise RuntimeError("Invalid Docker image manifest.")
        manifest = json.load(archive.extractfile(member))
        if len(manifest) != 1 or manifest[0].get("RepoTags") != [expected_image]:
            raise RuntimeError("Archive must contain exactly the requested API image tag.")


def copy_release(commit, destination):
    owner = pwd.getpwnam("warehouse-backend").pw_uid
    incoming = STATE / "incoming"
    # Open directories/files without following links, retaining descriptors across
    # renames by the unprivileged runner. Only these two fixed filenames are read.
    parent = os.open(incoming, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        folder = os.open(commit, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        def source(name):
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=folder)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != owner:
                os.close(fd)
                raise RuntimeError("Release files must be regular files owned by the runner.")
            return os.fdopen(fd, "rb")
        with source("release.json") as handle:
            metadata = handle.read(8193)
            if len(metadata) > 8192:
                raise RuntimeError("Release metadata too large.")
            manifest = json.loads(metadata)
        image = validate_manifest(manifest, commit)
        target = Path(destination) / "image.tar.gz"
        digest = hashlib.sha256()
        total = 0
        with source("image.tar.gz") as src, target.open("xb") as dst:
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                total += len(chunk)
                if total > 4 * 1024**3:
                    raise RuntimeError("Image archive exceeds 4 GiB.")
                digest.update(chunk)
                dst.write(chunk)
        if digest.hexdigest() != manifest["sha256"]:
            raise RuntimeError("Image archive checksum mismatch.")
        validate_archive(target, image)
        return image, target
    finally:
        os.close(folder)


class Deployment:
    def __init__(self, config, state=STATE):
        self.config = config
        self.state = Path(state)
        self.review = self.state / "needs-review.json"

    def docker(self, *args, capture=False, timeout=900):
        result = subprocess.run(["/usr/bin/docker", *map(str, args)], check=True,
                                capture_output=capture, text=True, timeout=timeout)
        return result.stdout.strip() if capture else ""

    def compose(self, *args):
        cfg = self.config
        return self.docker("compose", "--project-directory", cfg["deploy_dir"],
                           "-p", cfg["project"], "-f", cfg["compose_file"],
                           "-f", cfg["override_file"], *args)

    def set_image(self, image):
        write_json(self.config["override_file"],
                   {MARKER: True, "services": {"api": {"image": image, "pull_policy": "never"}}}, 0o644)

    def start(self, image):
        self.set_image(image)
        self.compose("up", "-d", "--no-deps", "--no-build", "--pull", "never", "api")

    def oneoff(self, image, arguments, extra=()):
        return self.docker("run", "--rm", "--pull", "never",
                           "--network", self.config["network"],
                           "--env-file", self.config["env_file"],
                           *extra, "--entrypoint", "python", image, *arguments, capture=True)

    def healthy(self):
        code = ("import json,urllib.request; "
                "d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health/db',timeout=10)); "
                "assert d.get('db')=='ok'")
        deadline = time.monotonic() + 120
        while True:
            try:
                self.docker("exec", self.config["api_container"], "python", "-c", code,
                            capture=True, timeout=15)
                return
            except (subprocess.SubprocessError, OSError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("API/database health check failed.") from None
                time.sleep(3)

    def backup(self, image, commit):
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        target = self.state / "pre-migration" / (stamp + "-" + commit[:12])
        target.mkdir(parents=True, mode=0o700)
        output = self.oneoff(image, ["/code/backup_warehouse.py"], extra=(
            "--user", "0:0", "--mount", f"type=bind,src={target},dst=/backup",
            "--env", "BACKUP_DIR=/backup", "--env", "KEEP_DAILY=1", "--env", "KEEP_MONTHLY=0"))
        if "BACKUP OK:" not in output or not (target / "last_success.json").is_file():
            raise RuntimeError("Pre-migration backup did not report verified success.")
        print(f"Verified pre-migration backup: {target}", flush=True)
        return str(target)

    def deploy(self, image, commit):
        if self.review.exists():
            raise RuntimeError(f"Previous migration/deployment needs review: {self.review}")
        inspection = json.loads(self.docker("inspect", self.config["api_container"], capture=True))[0]
        labels = inspection["Config"].get("Labels") or {}
        if labels.get("com.docker.compose.project") != self.config["project"] or labels.get(
                "com.docker.compose.service") != "api":
            raise RuntimeError("Unexpected API container/project.")
        previous = "warehouse-api:before-" + commit
        self.docker("image", "tag", inspection["Image"], previous)
        todo = json.loads(self.oneoff(image, ["/code/run_migrations.py", "--plan"]))["pending"]
        ddl_started = False
        backup = None
        try:
            if todo:
                write_json(self.review, {"commit": commit, "phase": "pausing", "pending": todo})
                self.compose("stop", "--timeout", "30", "api")
                backup = self.backup(image, commit)
                write_json(self.review, {"commit": commit, "phase": "migrating",
                                         "pending": todo, "backup": backup})
                ddl_started = True
                self.oneoff(image, ["/code/run_migrations.py", "--apply", "--backup-confirmed"])
            self.start(image)
            self.healthy()
        except BaseException:
            if ddl_started:
                # DDL may be permanent. Never claim an image rollback undoes it.
                try:
                    self.compose("stop", "--timeout", "30", "api")
                except Exception:
                    pass
                write_json(self.review, {"commit": commit, "phase": "needs-review", "backup": backup,
                                         "message": "API paused; schema may have changed. Do not blindly retry."})
                print(f"Deployment paused for review. Keep backup: {backup}", file=sys.stderr)
            else:
                self.start(previous)
                self.healthy()
                self.review.unlink(missing_ok=True)
                print("Previous API image restored; no schema migrations were executed.", file=sys.stderr)
            raise
        self.review.unlink(missing_ok=True)
        write_json(self.state / "last_success.json", {
            "commit": commit, "image": image, "previous_image": previous,
            "migrations": todo, "pre_migration_backup": backup,
            "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        })
        print(f"BACKEND DEPLOYED: {commit}; migrations: {len(todo)}", flush=True)


def main():
    if os.geteuid() != 0 or len(sys.argv) != 2 or not COMMIT.fullmatch(sys.argv[1]):
        raise SystemExit("Usage: sudo warehouse-deploy-backend FULL_GIT_COMMIT_SHA")
    # Ignore caller-controlled Docker, Python, and Compose environment settings.
    os.environ.clear()
    os.environ.update(PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", HOME="/root")
    os.umask(0o077)
    info = CONFIG.stat()
    if info.st_uid != 0 or info.st_mode & 0o022:
        raise SystemExit("Deployment config must be root-owned and not group/world-writable.")
    config = json.loads(CONFIG.read_text())
    with (STATE / "deploy.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        deployment = Deployment(config)
        if deployment.review.exists():
            raise SystemExit(f"Review required: {deployment.review}")
        with tempfile.TemporaryDirectory(prefix="release-", dir=STATE) as private:
            image, archive = copy_release(sys.argv[1], private)
            deployment.docker("load", "-i", archive, capture=True)
            label = deployment.docker("image", "inspect", image, "--format",
                                      '{{index .Config.Labels "org.opencontainers.image.revision"}}',
                                      capture=True)
            if label != sys.argv[1]:
                raise RuntimeError("Loaded image revision does not match release.")
            deployment.deploy(image, sys.argv[1])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Command arguments can contain private paths; never dump environments.
        raise SystemExit(f"Backend deployment failed: {type(exc).__name__}: {exc}") from None
