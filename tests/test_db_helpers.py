from app.db.session import create_db_and_tables, get_session


def test_db_helpers():
    create_db_and_tables()
    session = next(get_session())
    session.close()
