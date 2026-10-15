"""Migration policy checks against an in-memory DB adapter; never connects to Oracle."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("warehouse_migrations", ROOT / "backend/run_migrations.py")
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, sql, values=None):
        db = self.connection
        db.commands.append(sql)
        if sql == "SELECT USER FROM dual":
            self.rows = [(db.user,)]
        elif sql.startswith("SELECT table_name"):
            self.rows = [(name,) for name in db.tables]
        elif sql.startswith("SELECT COUNT(*)"):
            self.rows = [(int(db.ledger),)]
        elif sql.startswith("SELECT version"):
            self.rows = [tuple(row) for row in db.history]
        elif sql.lstrip().startswith("CREATE TABLE FA_SCHEMA_MIGRATIONS"):
            if db.ledger:
                raise RuntimeError("Ledger already exists")
            db.ledger = True
        elif sql.startswith("INSERT INTO FA_SCHEMA_MIGRATIONS"):
            db.history.append([values["version"], values["name"], values["sha256"], "RUNNING"])
        elif sql.startswith("UPDATE FA_SCHEMA_MIGRATIONS"):
            status = "APPLIED" if "status='APPLIED'" in sql else "FAILED"
            next(row for row in db.history if row[0] == values["version"])[3] = status
        elif sql.startswith("SELECT object_name"):
            self.rows = db.invalid
        elif sql == "FAIL":
            raise RuntimeError("Deliberate migration failure")

    def fetchone(self):
        return self.rows[0]

    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self):
        self.user = "WAREHOUSE_LIVE"
        self.tables = {"FA_USERS", "FA_TALI_HEADER"}
        self.ledger = False
        self.history = []
        self.commands = []
        self.invalid = []

    def cursor(self):
        return Cursor(self)

    def commit(self):
        pass

    def rollback(self):
        pass


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.folder = Path(self.directory.name)
        self.db = Connection()

    def tearDown(self):
        self.directory.cleanup()

    def version(self, name="0001_add_note.py", body='cursor.execute("ALTER TABLE example ADD note VARCHAR2(10)")'):
        path = self.folder / name
        path.write_text("def upgrade(cursor):\n    " + body + "\n")
        return migration.discover(self.folder)

    def test_empty_release_performs_no_writes(self):
        self.assertEqual(migration.apply(self.db, []), [])
        self.assertFalse(self.db.ledger)
        self.assertTrue(all(sql.startswith("SELECT ") for sql in self.db.commands))

    def test_wrong_owner_or_missing_sentinel_is_refused_before_writes(self):
        versions = self.version()
        for invalid in ("user", "tables"):
            db = Connection()
            setattr(db, invalid, "HR" if invalid == "user" else {"FA_USERS"})
            with self.assertRaises(RuntimeError):
                migration.apply(db, versions, backup_confirmed=True)
            self.assertFalse(db.ledger)

    def test_restore_testing_requires_explicit_matching_owner(self):
        self.db.user = "WAREHOUSE_RESTORE"
        versions = self.version()
        with self.assertRaisesRegex(RuntimeError, "Unexpected schema"):
            migration.apply(self.db, versions, backup_confirmed=True)
        self.assertEqual(migration.apply(self.db, versions, expected_user="WAREHOUSE_RESTORE",
                                        backup_confirmed=True), ["0001_add_note.py"])

    def test_backup_required_before_ledger_or_migration(self):
        with self.assertRaisesRegex(RuntimeError, "backup"):
            migration.apply(self.db, self.version())
        self.assertFalse(self.db.ledger)

    def test_apply_once_then_only_new_version_runs(self):
        first = self.version()
        self.assertEqual(migration.apply(self.db, first, backup_confirmed=True), ["0001_add_note.py"])
        before = len([sql for sql in self.db.commands if sql.startswith("ALTER TABLE")])
        self.assertEqual(migration.apply(self.db, first), [])
        self.assertEqual(len([sql for sql in self.db.commands if sql.startswith("ALTER TABLE")]), before)
        second = self.version("0002_another.py")
        self.assertEqual(migration.apply(self.db, second, backup_confirmed=True), ["0002_another.py"])

    def test_empty_existing_ledger_can_be_used(self):
        self.db.ledger = True
        migration.apply(self.db, self.version(), backup_confirmed=True)
        self.assertFalse(any(sql.lstrip().startswith("CREATE TABLE") for sql in self.db.commands))

    def test_changed_removed_or_inserted_history_is_refused(self):
        versions = self.version("0002_note.py")
        migration.apply(self.db, versions, backup_confirmed=True)
        with self.assertRaises(RuntimeError):
            migration.apply(self.db, [], backup_confirmed=True)
        self.version("0001_earlier.py")
        with self.assertRaises(RuntimeError):
            migration.apply(self.db, migration.discover(self.folder), backup_confirmed=True)
        (self.folder / "0001_earlier.py").unlink()
        self.version("0002_note.py", 'cursor.execute("different SQL")')
        with self.assertRaises(RuntimeError):
            migration.apply(self.db, migration.discover(self.folder), backup_confirmed=True)

    def test_failure_is_recorded_and_not_replayed(self):
        versions = self.version(body='cursor.execute("FAIL")')
        with self.assertRaisesRegex(RuntimeError, "may be committed"):
            migration.apply(self.db, versions, backup_confirmed=True)
        self.assertEqual(self.db.history[0][3], "FAILED")
        with self.assertRaisesRegex(RuntimeError, "FAILED"):
            migration.apply(self.db, versions, backup_confirmed=True)
        self.assertEqual(self.db.commands.count("FAIL"), 1)

    def test_interrupted_running_version_blocks_next_run(self):
        versions = self.version()
        self.db.ledger = True
        item = versions[0]
        self.db.history = [[item["version"], item["name"], item["sha256"], "RUNNING"]]
        with self.assertRaisesRegex(RuntimeError, "RUNNING"):
            migration.apply(self.db, versions, backup_confirmed=True)

    def test_invalid_objects_mark_migration_failed(self):
        self.db.invalid = [("BAD_TRIGGER", "TRIGGER")]
        with self.assertRaises(RuntimeError):
            migration.apply(self.db, self.version(), backup_confirmed=True)
        self.assertEqual(self.db.history[0][3], "FAILED")

    def test_duplicate_versions_and_missing_upgrade_are_refused(self):
        self.version()
        with self.assertRaises(RuntimeError):
            self.version("0001_duplicate.py")
        (self.folder / "0001_duplicate.py").unlink()
        (self.folder / "0001_add_note.py").write_text("pass\n")
        with self.assertRaisesRegex(RuntimeError, "upgrade"):
            migration.discover(self.folder)


if __name__ == "__main__":
    unittest.main()
