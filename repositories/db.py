"""Connection helpers for the MSSQL-backed demo application."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


class DatabaseConfigurationError(RuntimeError):
    """Raised when required database settings are missing."""


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    """Store the connection settings in one typed object.

    Keeping the settings together makes it easier to explain where the
    connection details come from and avoids passing a long list of strings
    through the entire project.
    """

    server: str
    database: str
    username: str
    password: str
    driver: str
    trust_server_certificate: bool
    app_user: str

    @property
    def connection_url(self) -> str:
        """Build a SQLAlchemy URL that internally uses the pyodbc driver."""

        odbc_string = quote_plus(
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
            "Encrypt=Yes;"
            f"TrustServerCertificate={'Yes' if self.trust_server_certificate else 'No'};"
            "Connection Timeout=30;"
        )
        return f"mssql+pyodbc:///?odbc_connect={odbc_string}"


@lru_cache(maxsize=1)
def get_database_settings() -> DatabaseSettings:
    """Load and validate the `.env` file once per Python process.

    Streamlit reruns the script whenever a widget changes. Caching prevents
    re-reading the environment file on every interaction and keeps the
    presentation layer focused on the actual UI logic.
    """

    load_dotenv()

    server = os.getenv("MSSQL_SERVER", "").strip()
    database = os.getenv("MSSQL_DATABASE", "").strip()
    username = os.getenv("MSSQL_USERNAME", "").strip()
    password = os.getenv("MSSQL_PASSWORD", "").strip()
    driver = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server").strip()
    trust_server_certificate = (
        os.getenv("TRUST_SERVER_CERTIFICATE", "true").strip().lower() == "true"
    )
    app_user = os.getenv("APP_USER", username).strip()

    if not all([server, database, username, password]):
        raise DatabaseConfigurationError(
            "The database settings are incomplete. Create a .env file before starting the app."
        )

    return DatabaseSettings(
        server=server,
        database=database,
        username=username,
        password=password,
        driver=driver,
        trust_server_certificate=trust_server_certificate,
        app_user=app_user or username,
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create one shared SQLAlchemy engine for the whole application."""

    settings = get_database_settings()
    return create_engine(settings.connection_url, future=True, pool_pre_ping=True)


def get_app_user() -> str:
    """Return the logical application user written into the audit columns."""

    return get_database_settings().app_user

