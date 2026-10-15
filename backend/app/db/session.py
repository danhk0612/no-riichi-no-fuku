from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker


class LocalRuntimeSession(Session):
    """Marker class for transactions owned by the local SQLite runtime."""


def mark_write_intent(session: Session) -> None:
    session.info["sqlite_write_intent"] = True
    if isinstance(session, LocalRuntimeSession):
        # Apply the execution option before Session acquires its first connection.
        session.connection(execution_options={"sqlite_begin_immediate": True})


def create_database_engine(
    database_url: str | URL,
    *,
    sqlite_begin_immediate_by_intent: bool = False,
) -> Engine:
    engine = create_engine(database_url, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

        @event.listens_for(engine, "begin")
        def begin_sqlite_write_transaction(connection) -> None:
            if not sqlite_begin_immediate_by_intent or connection.get_execution_options().get(
                "sqlite_begin_immediate"
            ):
                connection.exec_driver_sql("BEGIN IMMEDIATE")

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
