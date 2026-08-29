from app.core.config import Settings
from app.db.session import create_database_engine, create_session_factory
from app.services.bootstrap import bootstrap_superadmin, seed_cpu_characters


def main() -> None:
    settings = Settings()
    database_url = settings.require_database_url()
    login_id, initial_password = settings.require_superadmin_credentials()
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)

    with session_factory.begin() as session:
        created_superadmin = bootstrap_superadmin(
            session,
            login_id,
            initial_password,
        )
        created_cpu_count = seed_cpu_characters(session)

    print(
        "bootstrap complete: "
        f"superadmin_created={created_superadmin}, "
        f"cpu_characters_created={created_cpu_count}"
    )


if __name__ == "__main__":
    main()
