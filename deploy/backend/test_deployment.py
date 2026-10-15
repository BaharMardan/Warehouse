"""Deployment failure checks with a fake Docker adapter and private temporary files."""
import hashlib
import io
import os
from types import SimpleNamespace
from unittest.mock import patch
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

import deploy_backend
from deploy_backend import Deployment, MARKER, copy_release, validate_archive, validate_manifest

SHA = "a" * 40
IMAGE = "warehouse-api:git-" + SHA
PREVIOUS = "warehouse-api:before-" + SHA


class FakeDeployment(Deployment):
    def __init__(self, folder, pending=()):
        super().__init__({"override_file": str(folder / "override.json"),
                          "project": "warehouse", "api_container": "warehouse-api"}, folder)
        self.todo = list(pending)
        self.events = []
        self.fail_backup = False
        self.fail_apply = False
        self.fail_health = False

    def docker(self, *args, **kwargs):
        if args[0] == "inspect":
            return json.dumps([{"Image": "sha256:previous", "Config": {"Labels": {
                "com.docker.compose.project": "warehouse", "com.docker.compose.service": "api"}}}])
        return ""

    def compose(self, *args):
        self.events.append(("compose", args))

    def oneoff(self, image, arguments, extra=()):
        if "--plan" in arguments:
            return json.dumps({"pending": self.todo})
        self.events.append(("migrate", image))
        if self.fail_apply:
            raise RuntimeError("Schema migration failed")
        return "{}"

    def backup(self, image, commit):
        self.events.append(("backup", image))
        if self.fail_backup:
            raise RuntimeError("Backup failed")
        return str(self.state / "verified-private-backup")

    def start(self, image):
        super().set_image(image)
        self.active_image = image
        self.events.append(("start", image))

    def healthy(self):
        self.events.append(("health", self.active_image))
        if self.fail_health and self.active_image == IMAGE:
            raise RuntimeError("New API is unhealthy")


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.folder = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_code_only_deploy_does_not_backup_or_migrate(self):
        app = FakeDeployment(self.folder)
        app.deploy(IMAGE, SHA)
        self.assertEqual(app.events, [("start", IMAGE), ("health", IMAGE)])
        self.assertEqual(json.loads((self.folder / "override.json").read_text())["services"]["api"]["image"], IMAGE)
        self.assertTrue(json.loads((self.folder / "override.json").read_text())[MARKER])

    def test_unhealthy_code_only_release_restores_previous_image(self):
        app = FakeDeployment(self.folder)
        app.fail_health = True
        with self.assertRaises(RuntimeError):
            app.deploy(IMAGE, SHA)
        self.assertIn(("start", PREVIOUS), app.events)
        self.assertEqual(app.active_image, PREVIOUS)
        self.assertFalse(app.review.exists())

    def test_backup_precedes_migration_and_new_api(self):
        app = FakeDeployment(self.folder, ["0001_add_note.py"])
        app.deploy(IMAGE, SHA)
        names = [event[0] for event in app.events]
        self.assertLess(names.index("compose"), names.index("backup"))
        self.assertLess(names.index("backup"), names.index("migrate"))
        self.assertLess(names.index("migrate"), names.index("start"))
        self.assertFalse(app.review.exists())

    def test_failed_backup_restores_api_without_running_migration(self):
        app = FakeDeployment(self.folder, ["0001_add_note.py"])
        app.fail_backup = True
        with self.assertRaises(RuntimeError):
            app.deploy(IMAGE, SHA)
        self.assertFalse(any(event[0] == "migrate" for event in app.events))
        self.assertEqual(app.active_image, PREVIOUS)
        self.assertFalse(app.review.exists())

    def test_failed_migration_keeps_api_stopped_and_blocks_retry(self):
        app = FakeDeployment(self.folder, ["0001_add_note.py"])
        app.fail_apply = True
        with self.assertRaises(RuntimeError):
            app.deploy(IMAGE, SHA)
        self.assertFalse(any(event[0] == "start" for event in app.events))
        state = json.loads(app.review.read_text())
        self.assertEqual(state["phase"], "needs-review")
        self.assertIn("verified-private-backup", state["backup"])
        count = len(app.events)
        with self.assertRaisesRegex(RuntimeError, "review"):
            app.deploy(IMAGE, SHA)
        self.assertEqual(len(app.events), count)

    def test_unhealthy_api_after_migration_does_not_roll_back_schema_or_image(self):
        app = FakeDeployment(self.folder, ["0001_add_note.py"])
        app.fail_health = True
        with self.assertRaises(RuntimeError):
            app.deploy(IMAGE, SHA)
        self.assertTrue(app.review.exists())
        self.assertNotIn(("start", PREVIOUS), app.events)
        self.assertEqual(app.events[-1][0], "compose")


class ArchiveTests(unittest.TestCase):
    def test_metadata_must_match_commit_and_api_tag(self):
        good = {"commit": SHA, "image": IMAGE, "sha256": "b" * 64}
        self.assertEqual(validate_manifest(good, SHA), IMAGE)
        for key, value in (("commit", "c" * 40), ("image", "gvenzl/oracle-free:latest"),
                           ("sha256", "invalid")):
            with self.assertRaises(RuntimeError):
                validate_manifest(dict(good, **{key: value}), SHA)

    def archive(self, folder, tags):
        path = folder / "image.tar.gz"
        data = json.dumps([{"RepoTags": tags}]).encode()
        with tarfile.open(path, "w:gz") as archive:
            entry = tarfile.TarInfo("manifest.json")
            entry.size = len(data)
            archive.addfile(entry, io.BytesIO(data))
        return path

    def test_release_is_copied_and_checksum_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "incoming" / SHA
            source.mkdir(parents=True)
            image = self.archive(source, [IMAGE])
            metadata = {"commit": SHA, "image": IMAGE,
                        "sha256": hashlib.sha256(image.read_bytes()).hexdigest()}
            (source / "release.json").write_text(json.dumps(metadata))
            destination = root / "private"
            destination.mkdir()
            with patch.object(deploy_backend, "STATE", root), patch.object(
                    deploy_backend.pwd, "getpwnam", return_value=SimpleNamespace(pw_uid=os.getuid())):
                name, copied = copy_release(SHA, destination)
            self.assertEqual(name, IMAGE)
            self.assertEqual(copied.read_bytes(), image.read_bytes())
            copied.unlink()
            metadata["sha256"] = "0" * 64
            (source / "release.json").write_text(json.dumps(metadata))
            with patch.object(deploy_backend, "STATE", root), patch.object(
                    deploy_backend.pwd, "getpwnam", return_value=SimpleNamespace(pw_uid=os.getuid())):
                with self.assertRaisesRegex(RuntimeError, "checksum mismatch"):
                    copy_release(SHA, destination)

    def test_release_metadata_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "incoming" / SHA
            source.mkdir(parents=True)
            secret = root / "private-secret"
            secret.write_text("private test content")
            (source / "release.json").symlink_to(secret)
            with patch.object(deploy_backend, "STATE", root), patch.object(
                    deploy_backend.pwd, "getpwnam", return_value=SimpleNamespace(pw_uid=os.getuid())):
                with self.assertRaises(OSError):
                    copy_release(SHA, root)

    def test_release_directory_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incoming = root / "incoming"
            incoming.mkdir()
            (incoming / SHA).symlink_to(root, target_is_directory=True)
            with patch.object(deploy_backend, "STATE", root), patch.object(
                    deploy_backend.pwd, "getpwnam", return_value=SimpleNamespace(pw_uid=os.getuid())):
                with self.assertRaises(OSError):
                    copy_release(SHA, root)

    def test_archive_can_only_load_the_requested_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            validate_archive(self.archive(folder, [IMAGE]), IMAGE)
            with self.assertRaises(RuntimeError):
                validate_archive(self.archive(folder, [IMAGE, "gvenzl/oracle-free:latest"]), IMAGE)


if __name__ == "__main__":
    unittest.main()
