"""Loads schema.sql."""
from pathlib import Path


def load_schema() -> str:
    schema_path = Path(__file__).parent / "schema.sql"
    return schema_path.read_text(encoding="utf-8")