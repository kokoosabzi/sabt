from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./sabt.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})


@event.listens_for(engine, "connect")
def _configure_sqlite(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
