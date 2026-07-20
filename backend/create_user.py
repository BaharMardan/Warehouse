from app.core.config import settings
from app.core.security import hash_password
import oracledb


def main():
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    full_name = input("Full name (optional): ").strip() or None

    conn = oracledb.connect(
        user=settings.oracle_user,
        password=settings.oracle_password,
        dsn=settings.oracle_dsn,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO FA_USERS (username, password_hash, full_name, is_admin) "
                "VALUES (:u, :p, :f, 'yes')",
                {"u": username, "p": hash_password(password), "f": full_name},
            )
        conn.commit()
        print(f"Created admin user: {username}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()