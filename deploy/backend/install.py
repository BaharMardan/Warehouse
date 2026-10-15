#!/usr/bin/python3
"""One-time installation on Ubuntu 1; never recreates containers or changes Oracle."""
import argparse
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tempfile

from deploy_backend import MARKER, STATE, CONFIG, write_json


def docker(*args):
    return subprocess.check_output(["/usr/bin/docker", *map(str, args)], text=True)


def main():
    if os.geteuid() != 0:
        raise SystemExit("Run with sudo python3 deploy/backend/install.py")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deploy-dir", default="/home/parsa/warehouse-deploy")
    args = parser.parse_args()
    folder = Path(args.deploy_dir).resolve()
    candidates = [folder / name for name in ("compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml")]
    base = next((path for path in candidates if path.is_file()), None)
    if base is None or not (folder / "backend.env").is_file():
        raise SystemExit("Production Compose file and backend.env must already exist.")
    override = folder / "compose.override.yaml"
    for name in ("compose.override.yaml", "compose.override.yml", "docker-compose.override.yml", "docker-compose.override.yaml"):
        path = folder / name
        if path.exists():
            try:
                managed = path == override and json.loads(path.read_text()).get(MARKER) is True
            except (ValueError, AttributeError):
                managed = False
            if not managed:
                raise SystemExit(f"Existing override needs review before installation: {path}")
    api = json.loads(docker("inspect", "warehouse-api"))[0]
    labels = api["Config"].get("Labels") or {}
    if labels.get("com.docker.compose.project") != "warehouse" or labels.get("com.docker.compose.service") != "api":
        raise SystemExit("Expected the existing warehouse/api Compose container.")
    if any(mount["Destination"] in ("/code", "/code/app") for mount in api.get("Mounts", [])):
        raise SystemExit("Production API has a source bind mount; review before enabling image deployment.")
    rendered = json.loads(docker("compose", "--project-directory", folder, "-p", "warehouse",
                                 "-f", base, "config", "--format", "json"))
    if rendered["services"]["api"].get("environment", {}).get("ORACLE_USER") != "WAREHOUSE_LIVE":
        raise SystemExit("Production api must use WAREHOUSE_LIVE; configuration values were not printed.")
    docker("network", "inspect", "warehouse_default")
    try:
        account = pwd.getpwnam("warehouse-backend")
    except KeyError:
        subprocess.run(["useradd", "--system", "--create-home", "--home-dir",
                        "/opt/warehouse-backend-runner", "--shell", "/bin/bash", "warehouse-backend"], check=True)
        account = pwd.getpwnam("warehouse-backend")
    for path, mode, uid, gid in (
        (STATE, 0o755, 0, 0),
        (STATE / "incoming", 0o700, account.pw_uid, account.pw_gid),
        (Path("/opt/warehouse-backend-runner"), 0o755, account.pw_uid, account.pw_gid),
        (CONFIG.parent, 0o700, 0, 0),
    ):
        path.mkdir(parents=True, exist_ok=True)
        os.chown(path, uid, gid)
        path.chmod(mode)
    destination = Path("/usr/local/sbin/warehouse-deploy-backend")
    shutil.copyfile(Path(__file__).with_name("deploy_backend.py"), destination)
    os.chown(destination, 0, 0)
    destination.chmod(0o755)
    config = {"deploy_dir": str(folder), "compose_file": str(base), "override_file": str(override),
              "project": "warehouse", "network": "warehouse_default",
              "api_container": "warehouse-api", "env_file": str(folder / "backend.env")}
    write_json(CONFIG, config)
    if not override.exists():
        write_json(override, {MARKER: True, "services": {"api": {
            "image": api["Config"]["Image"], "pull_policy": "never"}}}, 0o644)
    rule = "warehouse-backend ALL=(root) NOPASSWD: /usr/local/sbin/warehouse-deploy-backend\n"
    with tempfile.NamedTemporaryFile(mode="w", prefix="warehouse-sudoers-", delete=False) as handle:
        handle.write(rule)
        temporary = Path(handle.name)
    try:
        subprocess.run(["/usr/sbin/visudo", "-cf", str(temporary)], check=True)
        target = Path("/etc/sudoers.d/warehouse-backend-deploy")
        shutil.copyfile(temporary, target)
        os.chown(target, 0, 0)
        target.chmod(0o440)
    finally:
        temporary.unlink()
    print("Backend deploy helper installed; running API and Oracle were not restarted.")
    print("Production backend.env and Oracle volumes were retained.")
    print("Next: register the runner as warehouse-backend with label warehouse-backend.")
    print("The runner has no Docker group membership; sudo is limited to the deploy helper.")


if __name__ == "__main__":
    main()
