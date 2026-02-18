"""Build the SQLite database from schema.sql and seed.sql."""

import sqlite3
import pathlib

db_dir = pathlib.Path(__file__).parent
db_path = db_dir / "database.db"
schema_path = db_dir / "schema.sql"
seed_path = db_dir / "seed.sql"

schema = schema_path.read_text(encoding="utf-8")
seed = seed_path.read_text(encoding="utf-8")

# Remove existing DB if any
if db_path.exists():
    db_path.unlink()

conn = sqlite3.connect(str(db_path))
conn.execute("PRAGMA foreign_keys = ON")
conn.executescript(schema)
conn.executescript(seed)

# Verify
tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()
for t in tables:
    count = conn.execute(f"SELECT COUNT(*) FROM [{t[0]}]").fetchone()[0]
    print(f"  {t[0]}: {count} rows")

conn.close()
print("\nDatabase created successfully at:", db_path)
