"""Linux integration checks for static frontend publication; no production access."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipUnless(shutil.which("rsync") and shutil.which("curl"), "Requires Linux rsync and curl")
class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix="warehouse-publish-test-")
        self.base = Path(self.work.name)
        self.web = self.base / "web"
        self.web.mkdir()
        self.old = b"<html>previous frontend</html>"
        (self.web / "index.html").write_bytes(self.old)
        (self.web / "assets").mkdir()
        (self.web / "assets/old.js").write_text("old")
        self.build = self.base / "build"
        self.build.mkdir()
        (self.build / "assets").mkdir()
        self.new = "<html>new frontend \u0627\u0646\u0628\u0627\u0631</html>".encode("utf-8")
        (self.build / "index.html").write_bytes(self.new)
        (self.build / "assets/new.js").write_text("new")
        (self.build / "favicon.ico").write_bytes(b"new favicon")
        handler = partial(QuietHandler, directory=str(self.web))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.env = dict(os.environ)
        self.env.update({
            "WAREHOUSE_WEB_ROOT": str(self.web),
            "WAREHOUSE_DEPLOY_STATE": str(self.base / "state"),
            "WAREHOUSE_HEALTH_URL": f"http://127.0.0.1:{self.server.server_port}/",
        })

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.work.cleanup()

    def publish(self):
        return subprocess.run(
            ["bash", str(Path(__file__).with_name("publish.sh")), str(self.build)],
            env=self.env, capture_output=True, text=True, timeout=30,
        )

    def test_publish_preserves_old_assets_and_serves_new_index(self):
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.web / "index.html").read_bytes(), self.new)
        self.assertEqual((self.base / "state/previous-index.html").read_bytes(), self.old)
        self.assertTrue((self.web / "assets/old.js").is_file())
        self.assertTrue((self.web / "assets/new.js").is_file())
        self.assertEqual((self.web / "favicon.ico").read_bytes(), b"new favicon")
        self.assertFalse(list(self.web.glob(".index.*")))

    def test_failed_health_check_restores_previous_index(self):
        self.env["WAREHOUSE_HEALTH_URL"] += "missing-page"
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.web / "index.html").read_bytes(), self.old)
        self.assertTrue((self.web / "assets/old.js").is_file())
        self.assertIn("Previous index restored", result.stdout)

    def test_missing_index_leaves_site_untouched(self):
        (self.build / "index.html").unlink()
        self.assertNotEqual(self.publish().returncode, 0)
        self.assertEqual((self.web / "index.html").read_bytes(), self.old)

    def test_symlink_is_rejected_before_publication(self):
        (self.build / "linked-file").symlink_to(self.web / "index.html")
        self.assertNotEqual(self.publish().returncode, 0)
        self.assertEqual((self.web / "index.html").read_bytes(), self.old)

    def test_failed_build_inspection_leaves_site_untouched(self):
        commands = self.base / "commands"
        commands.mkdir()
        failing_find = commands / "find"
        failing_find.write_text("#!/bin/sh\nexit 2\n")
        failing_find.chmod(0o755)
        self.env["PATH"] = str(commands) + os.pathsep + self.env["PATH"]
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Cannot inspect build", result.stderr)
        self.assertEqual((self.web / "index.html").read_bytes(), self.old)
        self.assertFalse((self.web / "assets/new.js").exists())

    def test_publish_recovers_from_inaccessible_inherited_working_directory(self):
        inherited = self.base / "inherited-working-directory"
        inherited.mkdir()
        result = subprocess.run(
            ["bash", "-c", 'cd "$1" && rmdir "$1" && exec bash "$2" "$3"',
             "_", str(inherited), str(Path(__file__).with_name("publish.sh").resolve()),
             str(self.build)],
            env=self.env, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("find:", result.stderr)
        self.assertEqual((self.web / "index.html").read_bytes(), self.new)

    def test_environment_file_is_rejected(self):
        (self.build / ".env").write_text("PRIVATE=not-a-real-secret")
        self.assertNotEqual(self.publish().returncode, 0)
        self.assertEqual((self.web / "index.html").read_bytes(), self.old)


if __name__ == "__main__":
    unittest.main()
