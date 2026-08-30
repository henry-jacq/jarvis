import sys
import os
import pymysql
from urllib.parse import urlparse

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.db import engine, Base
import app.models  # Load models metadata

def ensure_mysql_database_exists():
    url = settings.DATABASE_URL
    if url.startswith("mysql"):
        parsed = urlparse(url)
        db_name = parsed.path.lstrip("/")
        user = parsed.username or "root"
        password = parsed.password or ""
        host = parsed.hostname or "localhost"
        port = parsed.port or 3306

        print(f"Ensuring MySQL database '{db_name}' exists on {host}:{port}...")
        try:
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password
            )
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4;")
            conn.commit()
            conn.close()
            print(f"Database '{db_name}' verified/created.")
        except Exception as e:
            print(f"Notice: Could not automatically create MySQL database '{db_name}': {e}")

def init_db():
    ensure_mysql_database_exists()
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database initialization complete.")

if __name__ == "__main__":
    init_db()
