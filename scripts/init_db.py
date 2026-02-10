import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import create_db_and_tables

if __name__ == "__main__":
    create_db_and_tables()
    print("DB tables created.")
