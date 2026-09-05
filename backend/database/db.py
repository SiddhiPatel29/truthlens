"""
Database Module for VeraMedia AI Backend.
Initializes and exposes shared SQLAlchemy and Flask-Migrate instances.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Shared SQLAlchemy ORM instance
db = SQLAlchemy()

# Shared Flask-Migrate instance
migrate = Migrate()

@event.listens_for(Engine, "connect")
def enforce_sqlite_foreign_keys(dbapi_connection, connection_record):
    """
    Enforces foreign key constraints for SQLite connections.
    SQLite ignores FOREIGN KEY constraints by default unless PRAGMA foreign_keys = ON is executed.
    """
    cursor = None
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
    except Exception:
        # Ignore on non-sqlite drivers
        pass
    finally:
        if cursor:
            cursor.close()
