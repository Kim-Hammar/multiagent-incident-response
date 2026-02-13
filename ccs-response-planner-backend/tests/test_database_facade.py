"""Unit tests for the DatabaseFacade (with psycopg mocked)."""
from unittest.mock import MagicMock, patch


@patch("ccs_response_planner_backend.db.database_facade.psycopg")
def test_create_tables_executes_eleven_statements(mock_psycopg: MagicMock) -> None:
    """
    Verify create_tables issues eleven SQL statements (five CREATE TABLE,
    five ALTER TABLE, and one UPDATE for agent_type migration).
    """
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_psycopg.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_psycopg.connect.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    DatabaseFacade.create_tables()

    assert mock_cur.execute.call_count == 11


@patch("ccs_response_planner_backend.db.database_facade.psycopg")
def test_get_user_by_username_returns_dict(mock_psycopg: MagicMock) -> None:
    """
    Verify get_user_by_username returns a dict when a row is found.
    """
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_psycopg.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_psycopg.connect.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchone.return_value = (1, "admin", "hashed", "salt")

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    result = DatabaseFacade.get_user_by_username("admin")

    assert result is not None
    assert result["username"] == "admin"
    assert result["id"] == 1


@patch("ccs_response_planner_backend.db.database_facade.psycopg")
def test_get_user_by_username_returns_none(mock_psycopg: MagicMock) -> None:
    """
    Verify get_user_by_username returns None when no row is found.
    """
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_psycopg.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_psycopg.connect.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchone.return_value = None

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    result = DatabaseFacade.get_user_by_username("nobody")

    assert result is None


@patch("ccs_response_planner_backend.db.database_facade.bcrypt")
@patch("ccs_response_planner_backend.db.database_facade.psycopg")
def test_save_user_calls_execute(
    mock_psycopg: MagicMock, mock_bcrypt: MagicMock
) -> None:
    """
    Verify save_user hashes the password and inserts a row.
    """
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_psycopg.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_psycopg.connect.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_bcrypt.gensalt.return_value = b"$2b$12$saltsaltsaltsaltsaltsa"
    mock_bcrypt.hashpw.return_value = b"$2b$12$hashedpassword"

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    DatabaseFacade.save_user("admin", "secret")

    mock_cur.execute.assert_called_once()
    mock_bcrypt.gensalt.assert_called_once()
    mock_bcrypt.hashpw.assert_called_once()


@patch("ccs_response_planner_backend.db.database_facade.psycopg")
def test_get_digital_twin_config_returns_none(
    mock_psycopg: MagicMock,
) -> None:
    """
    Verify get_digital_twin_config returns None when no row exists.
    """
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_psycopg.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_psycopg.connect.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchone.return_value = None

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    result = DatabaseFacade.get_digital_twin_config()

    assert result is None


@patch("ccs_response_planner_backend.db.database_facade.psycopg")
def test_save_digital_twin_config_calls_execute(
    mock_psycopg: MagicMock,
) -> None:
    """
    Verify save_digital_twin_config issues an INSERT statement.
    """
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_psycopg.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_psycopg.connect.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    DatabaseFacade.save_digital_twin_config({"hosts": [], "links": []})

    mock_cur.execute.assert_called_once()


@patch("ccs_response_planner_backend.db.database_facade.psycopg")
def test_delete_digital_twin_config_calls_execute(
    mock_psycopg: MagicMock,
) -> None:
    """
    Verify delete_digital_twin_config issues a DELETE statement.
    """
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_psycopg.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_psycopg.connect.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    DatabaseFacade.delete_digital_twin_config()

    mock_cur.execute.assert_called_once()


@patch("ccs_response_planner_backend.db.database_facade.psycopg")
def test_get_config_id_by_incident_returns_id(
    mock_psycopg: MagicMock,
) -> None:
    """
    Verify get_config_id_by_incident returns config id when found.
    """
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_psycopg.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_psycopg.connect.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchone.return_value = (42,)

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    result = DatabaseFacade.get_config_id_by_incident(1)

    assert result == 42
    mock_cur.execute.assert_called_once()


@patch("ccs_response_planner_backend.db.database_facade.psycopg")
def test_get_config_id_by_incident_returns_none(
    mock_psycopg: MagicMock,
) -> None:
    """
    Verify get_config_id_by_incident returns None when not found.
    """
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_psycopg.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_psycopg.connect.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchone.return_value = None

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    result = DatabaseFacade.get_config_id_by_incident(999)

    assert result is None


@patch("ccs_response_planner_backend.db.database_facade.psycopg")
def test_get_policy_data_returns_bytes(
    mock_psycopg: MagicMock,
) -> None:
    """
    Verify get_policy_data returns bytes when policy exists.
    """
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_psycopg.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_psycopg.connect.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchone.return_value = (b"\x50\x4b\x03\x04",)

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    result = DatabaseFacade.get_policy_data(1)

    assert result == b"\x50\x4b\x03\x04"
    mock_cur.execute.assert_called_once()


@patch("ccs_response_planner_backend.db.database_facade.psycopg")
def test_get_policy_data_returns_none(
    mock_psycopg: MagicMock,
) -> None:
    """
    Verify get_policy_data returns None when no policy exists.
    """
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_psycopg.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_psycopg.connect.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchone.return_value = (None,)

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    result = DatabaseFacade.get_policy_data(999)

    assert result is None
