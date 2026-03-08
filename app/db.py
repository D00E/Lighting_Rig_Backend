import os
from contextlib import contextmanager
from typing import Iterator

import psycopg


DEFAULT_DATABASE_URL = "postgresql://lighting_user:lighting_password@localhost:5433/lighting_dev"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    connection = psycopg.connect(get_database_url())
    try:
        yield connection
    finally:
        connection.close()
