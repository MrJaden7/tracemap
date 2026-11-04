"""Database connection helper."""

import psycopg

from tracemap.config import get_settings


def connect() -> psycopg.Connection:
    return psycopg.connect(get_settings().conninfo)
