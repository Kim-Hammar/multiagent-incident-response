"""Unit tests for the DatabaseFacade (with _conn mocked)."""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch


def _mock_conn(mock_connection: MagicMock):
    """
    Build a mock for DatabaseFacade._conn that yields mock_connection.
    """
    @contextmanager
    def _ctx():
        yield mock_connection

    return _ctx


def _make_conn_and_cur():
    """Return (mock_conn, mock_cur) with cursor context manager wired up."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cur


@patch(
    "ccs_response_planner_backend.db.database_facade"
    ".DatabaseFacade._conn",
)
def test_create_tables_executes_eighteen_statements(
    mock_conn_method: MagicMock,
) -> None:
    """
    Verify create_tables issues nineteen SQL statements (six CREATE TABLE,
    two CREATE INDEX, eight ALTER TABLE, and three UPDATE).
    """
    mock_conn, mock_cur = _make_conn_and_cur()
    mock_conn_method.side_effect = _mock_conn(mock_conn)

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    DatabaseFacade.create_tables()

    assert mock_cur.execute.call_count == 19


@patch(
    "ccs_response_planner_backend.db.database_facade"
    ".DatabaseFacade._conn",
)
def test_get_user_by_username_returns_dict(
    mock_conn_method: MagicMock,
) -> None:
    """
    Verify get_user_by_username returns a dict when a row is found.
    """
    mock_conn, mock_cur = _make_conn_and_cur()
    mock_conn_method.side_effect = _mock_conn(mock_conn)
    mock_cur.fetchone.return_value = (1, "admin", "hashed", "salt")

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    result = DatabaseFacade.get_user_by_username("admin")

    assert result is not None
    assert result["username"] == "admin"
    assert result["id"] == 1


@patch(
    "ccs_response_planner_backend.db.database_facade"
    ".DatabaseFacade._conn",
)
def test_get_user_by_username_returns_none(
    mock_conn_method: MagicMock,
) -> None:
    """
    Verify get_user_by_username returns None when no row is found.
    """
    mock_conn, mock_cur = _make_conn_and_cur()
    mock_conn_method.side_effect = _mock_conn(mock_conn)
    mock_cur.fetchone.return_value = None

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    result = DatabaseFacade.get_user_by_username("nobody")

    assert result is None


@patch("ccs_response_planner_backend.db.database_facade.bcrypt")
@patch(
    "ccs_response_planner_backend.db.database_facade"
    ".DatabaseFacade._conn",
)
def test_save_user_calls_execute(
    mock_conn_method: MagicMock, mock_bcrypt: MagicMock
) -> None:
    """
    Verify save_user hashes the password and inserts a row.
    """
    mock_conn, mock_cur = _make_conn_and_cur()
    mock_conn_method.side_effect = _mock_conn(mock_conn)
    mock_bcrypt.gensalt.return_value = b"$2b$12$saltsaltsaltsaltsaltsa"
    mock_bcrypt.hashpw.return_value = b"$2b$12$hashedpassword"

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    DatabaseFacade.save_user("admin", "secret")

    mock_cur.execute.assert_called_once()
    mock_bcrypt.gensalt.assert_called_once()
    mock_bcrypt.hashpw.assert_called_once()


@patch(
    "ccs_response_planner_backend.db.database_facade"
    ".DatabaseFacade._conn",
)
def test_get_digital_twin_config_returns_none(
    mock_conn_method: MagicMock,
) -> None:
    """
    Verify get_digital_twin_config returns None when no row exists.
    """
    mock_conn, mock_cur = _make_conn_and_cur()
    mock_conn_method.side_effect = _mock_conn(mock_conn)
    mock_cur.fetchone.return_value = None

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    result = DatabaseFacade.get_digital_twin_config()

    assert result is None


@patch(
    "ccs_response_planner_backend.db.database_facade"
    ".DatabaseFacade._conn",
)
def test_save_digital_twin_config_calls_execute(
    mock_conn_method: MagicMock,
) -> None:
    """
    Verify save_digital_twin_config issues an INSERT statement.
    """
    mock_conn, mock_cur = _make_conn_and_cur()
    mock_conn_method.side_effect = _mock_conn(mock_conn)

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    DatabaseFacade.save_digital_twin_config({"hosts": [], "links": []})

    mock_cur.execute.assert_called_once()


@patch(
    "ccs_response_planner_backend.db.database_facade"
    ".DatabaseFacade._conn",
)
def test_delete_digital_twin_config_calls_execute(
    mock_conn_method: MagicMock,
) -> None:
    """
    Verify delete_digital_twin_config issues a DELETE statement.
    """
    mock_conn, mock_cur = _make_conn_and_cur()
    mock_conn_method.side_effect = _mock_conn(mock_conn)

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    DatabaseFacade.delete_digital_twin_config()

    mock_cur.execute.assert_called_once()


@patch(
    "ccs_response_planner_backend.db.database_facade"
    ".DatabaseFacade._conn",
)
def test_get_config_id_by_incident_returns_id(
    mock_conn_method: MagicMock,
) -> None:
    """
    Verify get_config_id_by_incident returns config id when found.
    """
    mock_conn, mock_cur = _make_conn_and_cur()
    mock_conn_method.side_effect = _mock_conn(mock_conn)
    mock_cur.fetchone.return_value = (42,)

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    result = DatabaseFacade.get_config_id_by_incident(1)

    assert result == 42
    mock_cur.execute.assert_called_once()


@patch(
    "ccs_response_planner_backend.db.database_facade"
    ".DatabaseFacade._conn",
)
def test_get_config_id_by_incident_returns_none(
    mock_conn_method: MagicMock,
) -> None:
    """
    Verify get_config_id_by_incident returns None when not found.
    """
    mock_conn, mock_cur = _make_conn_and_cur()
    mock_conn_method.side_effect = _mock_conn(mock_conn)
    mock_cur.fetchone.return_value = None

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    result = DatabaseFacade.get_config_id_by_incident(999)

    assert result is None


@patch(
    "ccs_response_planner_backend.db.database_facade"
    ".DatabaseFacade._conn",
)
def test_get_policy_data_returns_bytes(
    mock_conn_method: MagicMock,
) -> None:
    """
    Verify get_policy_data returns bytes when policy exists.
    """
    mock_conn, mock_cur = _make_conn_and_cur()
    mock_conn_method.side_effect = _mock_conn(mock_conn)
    mock_cur.fetchone.return_value = (b"\x50\x4b\x03\x04",)

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    result = DatabaseFacade.get_policy_data(1)

    assert result == b"\x50\x4b\x03\x04"
    mock_cur.execute.assert_called_once()


@patch(
    "ccs_response_planner_backend.db.database_facade"
    ".DatabaseFacade._conn",
)
def test_get_policy_data_returns_none(
    mock_conn_method: MagicMock,
) -> None:
    """
    Verify get_policy_data returns None when no policy exists.
    """
    mock_conn, mock_cur = _make_conn_and_cur()
    mock_conn_method.side_effect = _mock_conn(mock_conn)
    mock_cur.fetchone.return_value = (None,)

    from ccs_response_planner_backend.db.database_facade import DatabaseFacade
    result = DatabaseFacade.get_policy_data(999)

    assert result is None


@patch(
    "ccs_response_planner_backend.db.database_facade"
    ".DatabaseFacade._conn",
)
def test_get_active_planning_session_with_agent_type(
    mock_conn_method: MagicMock,
) -> None:
    """
    Verify get_active_planning_session filters by agent_type
    when provided.
    """
    mock_conn, mock_cur = _make_conn_and_cur()
    mock_conn_method.side_effect = _mock_conn(mock_conn)
    mock_cur.fetchone.return_value = (
        1, "admin", "active", [], None,
        {}, {}, None, None,
        "2026-01-01", "2026-01-01", "report", None,
    )

    from ccs_response_planner_backend.db.database_facade import (
        DatabaseFacade,
    )
    result = DatabaseFacade.get_active_planning_session(
        "admin", agent_type="report",
    )

    assert result is not None
    assert result["agent_type"] == "report"
    sql = mock_cur.execute.call_args[0][0]
    assert "agent_type = %s" in sql


@patch(
    "ccs_response_planner_backend.db.database_facade"
    ".DatabaseFacade._conn",
)
def test_get_active_planning_session_without_agent_type(
    mock_conn_method: MagicMock,
) -> None:
    """
    Verify get_active_planning_session filters by agent_type IS NULL
    when agent_type is not provided.
    """
    mock_conn, mock_cur = _make_conn_and_cur()
    mock_conn_method.side_effect = _mock_conn(mock_conn)
    mock_cur.fetchone.return_value = None

    from ccs_response_planner_backend.db.database_facade import (
        DatabaseFacade,
    )
    result = DatabaseFacade.get_active_planning_session("admin")

    assert result is None
    sql = mock_cur.execute.call_args[0][0]
    assert "agent_type IS NULL" in sql


@patch(
    "ccs_response_planner_backend.db.database_facade"
    ".DatabaseFacade._conn",
)
def test_get_planning_session_returns_dict(
    mock_conn_method: MagicMock,
) -> None:
    """
    Verify get_planning_session returns a dict when a row is found.
    """
    mock_conn, mock_cur = _make_conn_and_cur()
    mock_conn_method.side_effect = _mock_conn(mock_conn)
    mock_cur.fetchone.return_value = (
        42, "admin", "active", [], None,
        {}, {}, None, None,
        "2026-01-01", "2026-01-01", "report", None,
    )

    from ccs_response_planner_backend.db.database_facade import (
        DatabaseFacade,
    )
    result = DatabaseFacade.get_planning_session(42, "admin")

    assert result is not None
    assert result["id"] == 42
    assert result["agent_type"] == "report"
    sql = mock_cur.execute.call_args[0][0]
    assert "WHERE id = %s" in sql


@patch(
    "ccs_response_planner_backend.db.database_facade"
    ".DatabaseFacade._conn",
)
def test_get_planning_session_returns_none(
    mock_conn_method: MagicMock,
) -> None:
    """
    Verify get_planning_session returns None when not found.
    """
    mock_conn, mock_cur = _make_conn_and_cur()
    mock_conn_method.side_effect = _mock_conn(mock_conn)
    mock_cur.fetchone.return_value = None

    from ccs_response_planner_backend.db.database_facade import (
        DatabaseFacade,
    )
    result = DatabaseFacade.get_planning_session(999, "admin")

    assert result is None
