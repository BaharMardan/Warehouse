import oracledb

oracledb.defaults.fetch_lobs = False   # return CLOB/BLOB as plain text/bytes
from app.core.config import settings

# ONE connection pool for the whole app, created once and reused everywhere.
# python-oracledb "thin" mode needs no Oracle client install.
pool = oracledb.create_pool(
    user=settings.oracle_user,
    password=settings.oracle_password,
    dsn=settings.oracle_dsn,
    min=1,
    max=4,
    increment=1,
)


def get_connection():
    """Borrow a connection from the pool. Use it as a context manager."""
    return pool.acquire()
