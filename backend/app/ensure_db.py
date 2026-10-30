"""Create the app database inside a shared Postgres instance.

Render's free tier allows only one Postgres instance per workspace, so when
DATABASE_URL points into an existing shared instance we create our database
there at startup (via MAINTENANCE_DB, the instance's bootstrap database).
No-op when the database already exists — safe on every boot/redeploy.
"""
import os
import sys
import urllib.parse


def main() -> None:
    url = os.environ.get("DATABASE_URL", "")
    maint_db = os.environ.get("MAINTENANCE_DB", "")
    if not url or not maint_db:
        return  # dedicated DATABASE_URL — nothing to do

    import psycopg2

    clean = url.split("?", 1)[0].replace("postgresql+psycopg2://", "postgresql://")
    parts = urllib.parse.urlsplit(clean)
    target = parts.path.lstrip("/")
    admin_url = urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, f"/{maint_db}", "", ""))

    conn = psycopg2.connect(admin_url, connect_timeout=15)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target,))
    if cur.fetchone():
        print(f"database {target!r} already exists")
    else:
        cur.execute(f'CREATE DATABASE "{target}"')
        print(f"created database {target!r}")
    conn.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # don't kill the boot if already provisioned
        print(f"ensure_db warning: {exc}", file=sys.stderr)
