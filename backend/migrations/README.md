# Production schema migrations

Only versions/0001_description.py, 0002_description.py, ... are discovered.
The initial directory is empty: installing deployment does not replay historical
add_*.py or migrate_*.py scripts or import development data.

Each file defines upgrade(cursor), using the supplied python-oracledb cursor.
Do not open another connection or commit in the migration. Keep module-level
code free of database work. Example (illustration, not an installed migration):

~~~python
def upgrade(cursor):
    cursor.execute('ALTER TABLE "FA_TALI_HEADER" ADD ("EXAMPLE_NOTE" VARCHAR2(100 CHAR))')
~~~

Test real migrations against a separate restored schema before release.
Prefer additive, backward-compatible changes. A migration can contain arbitrary
SQL; this framework cannot prove that SQL preserves data. Never add destructive
SQL or copy the development database over production as a routine release.

The runner checks the live owner and sentinel tables. Applied filenames, order,
and SHA256 hashes are immutable. Do not delete/edit released migrations or insert
a version before existing versions. Add a new migration instead.

For pending migrations, the deploy helper pauses API writes, creates and verifies
a private backup, then applies each new version once. FA_SCHEMA_MIGRATIONS records
history, which nightly FA_* backups also capture. A code-only release with no
pending versions creates no ledger and changes no database data.

Oracle DDL commits implicitly. A failure may leave partial schema changes. FAILED
or interrupted RUNNING records block later deployment; the API stays stopped.
There is no automatic database rollback or automatic DROP USER.
Use the existing restore workflow into WAREHOUSE_RESTORE, verify it,
then plan recovery or a forward fix. Keep the pre-migration backup.

If DDL invalidates a dependent trigger, compile/check it explicitly in upgrade;
invalid objects cause the migration to fail.
Concurrent deployment is serialized by the host deploy lock. Run production
migrations through the deploy helper, not standalone competing processes.
