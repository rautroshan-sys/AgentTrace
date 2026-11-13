import sqlite3
from pathlib import Path

from agenttrace.db import SCHEMA_PATH

DEFAULT_DB_PATH = Path("agenttrace.db")


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")

    return connection


def initialize_database(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    connection = get_connection(db_path)

    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as schema_file:
            connection.executescript(schema_file.read())
        connection.commit()
    finally:
        connection.close()