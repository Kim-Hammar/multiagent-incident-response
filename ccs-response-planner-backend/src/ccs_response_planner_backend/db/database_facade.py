"""
Database facade for managing users and session tokens.
"""
import json
import logging
import os
import threading
from contextlib import contextmanager
from typing import Any, Iterator, Optional

import bcrypt
import psycopg
import psycopg_pool

from ccs_response_planner_backend.constants.constants import DB

logger = logging.getLogger(__name__)

_pool: Optional[psycopg_pool.ConnectionPool] = None
_pool_lock = threading.Lock()


def _strip_null_bytes(obj: Any) -> Any:
    """
    Recursively strip null bytes from strings in a data structure.

    PostgreSQL jsonb does not support \\u0000, so we remove
    null bytes from string values before serialization.

    :param obj: the data to sanitize
    :return: a copy with null bytes removed from all strings
    """
    if isinstance(obj, str):
        return obj.replace("\x00", "")
    if isinstance(obj, dict):
        return {k: _strip_null_bytes(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_null_bytes(i) for i in obj]
    return obj


def _sanitize_json(data: Any) -> str:
    """
    Serialize data to JSON safe for PostgreSQL jsonb.

    Strips null bytes from the data before serialization
    to avoid corrupting valid JSON escape sequences.

    :param data: the data to serialize
    :return: a JSON string safe for PostgreSQL jsonb
    """
    return json.dumps(_strip_null_bytes(data))


class DatabaseFacade:
    """
    Static-method facade for PostgreSQL database operations.
    """

    @staticmethod
    def _connection_string() -> str:
        """
        Build a PostgreSQL connection string from environment variables.

        :return: a PostgreSQL connection string
        """
        host = os.environ.get("POSTGRES_HOST", DB.DEFAULT_HOST)
        port = os.environ.get("POSTGRES_PORT", str(DB.DEFAULT_PORT))
        db_name = os.environ.get("POSTGRES_DB", DB.DEFAULT_DB_NAME)
        user = os.environ.get("POSTGRES_USER", DB.DEFAULT_USER)
        password = os.environ.get("POSTGRES_PASSWORD", "")
        return (
            f"host={host} port={port} dbname={db_name} "
            f"user={user} password={password} sslmode=disable"
        )

    @staticmethod
    def _get_pool() -> psycopg_pool.ConnectionPool:
        """
        Lazily initialize and return the shared connection pool.

        :return: the shared ConnectionPool instance
        """
        global _pool
        if _pool is not None:
            return _pool
        with _pool_lock:
            if _pool is None:
                _pool = psycopg_pool.ConnectionPool(
                    conninfo=DatabaseFacade._connection_string(),
                    min_size=20,
                    max_size=60,
                    kwargs={"autocommit": True},
                )
            return _pool

    @staticmethod
    @contextmanager
    def _conn() -> Iterator[psycopg.Connection[Any]]:
        """
        Borrow a connection from the pool.

        :return: a context-managed psycopg connection
        """
        pool = DatabaseFacade._get_pool()
        conn = pool.getconn()
        try:
            yield conn
        finally:
            pool.putconn(conn)

    @staticmethod
    def create_tables() -> None:
        """
        Create all application tables if they do not exist.
        """
        with DatabaseFacade._conn() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS
                        {DB.MANAGEMENT_USERS_TABLE} (
                            id SERIAL PRIMARY KEY,
                            username VARCHAR(255)
                                UNIQUE NOT NULL,
                            password VARCHAR(255) NOT NULL,
                            salt VARCHAR(255) NOT NULL
                        )
                    """)
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS
                        {DB.SESSION_TOKENS_TABLE} (
                            token VARCHAR(255)
                                PRIMARY KEY,
                            username VARCHAR(255) NOT NULL
                                REFERENCES
                                {DB.MANAGEMENT_USERS_TABLE}
                                (username),
                            timestamp TIMESTAMP
                                NOT NULL DEFAULT NOW()
                        )
                    """)
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS
                        {DB.EXAMPLE_INCIDENTS_TABLE} (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(255)
                                UNIQUE NOT NULL,
                            system_description TEXT
                                NOT NULL DEFAULT '',
                            system_description_image TEXT
                                NOT NULL DEFAULT '',
                            security_alerts TEXT
                                NOT NULL DEFAULT '',
                            operator_feedback TEXT
                                NOT NULL DEFAULT '',
                            specification TEXT
                                NOT NULL DEFAULT '',
                            incident_report TEXT
                                NOT NULL DEFAULT '',
                            response_plan TEXT
                                NOT NULL DEFAULT '',
                            created_at TIMESTAMP
                                NOT NULL DEFAULT NOW()
                        )
                    """)
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS
                        {DB.DIGITAL_TWIN_CONFIGS_TABLE} (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(255)
                                UNIQUE NOT NULL
                                DEFAULT 'default',
                            config JSONB NOT NULL,
                            created_at TIMESTAMP
                                NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMP
                                NOT NULL DEFAULT NOW()
                        )
                    """)
                    cur.execute(f"""
                        ALTER TABLE
                        {DB.DIGITAL_TWIN_CONFIGS_TABLE}
                        ADD COLUMN IF NOT EXISTS
                            example_incident_id INTEGER
                            REFERENCES
                            {DB.EXAMPLE_INCIDENTS_TABLE}(id)
                            ON DELETE SET NULL
                    """)
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS
                        {DB.AGENT_REPORTS_TABLE} (
                            id SERIAL PRIMARY KEY,
                            agent_type VARCHAR(50)
                                NOT NULL,
                            username VARCHAR(255)
                                NOT NULL,
                            report JSONB NOT NULL,
                            created_at TIMESTAMP
                                DEFAULT NOW()
                        )
                    """)
                    cur.execute(f"""
                        ALTER TABLE
                        {DB.AGENT_REPORTS_TABLE}
                        ADD COLUMN IF NOT EXISTS
                            incident_id INTEGER
                            REFERENCES
                            {DB.EXAMPLE_INCIDENTS_TABLE}(id)
                            ON DELETE SET NULL
                    """)
                    cur.execute(f"""
                        ALTER TABLE
                        {DB.DIGITAL_TWIN_CONFIGS_TABLE}
                        ADD COLUMN IF NOT EXISTS
                            validation_results JSONB
                    """)
                    cur.execute(f"""
                        ALTER TABLE
                        {DB.AGENT_REPORTS_TABLE}
                        ADD COLUMN IF NOT EXISTS
                            conversation_history JSONB
                    """)
                    cur.execute(f"""
                        ALTER TABLE
                        {DB.AGENT_REPORTS_TABLE}
                        ADD COLUMN IF NOT EXISTS
                            policy_data BYTEA
                    """)
                    cur.execute(f"""
                        ALTER TABLE
                        {DB.AGENT_REPORTS_TABLE}
                        ADD COLUMN IF NOT EXISTS
                            model_name VARCHAR(255)
                    """)
                    cur.execute(
                        f"UPDATE {DB.AGENT_REPORTS_TABLE}"
                        f" SET agent_type = 'planner' "
                        f"WHERE agent_type = 'mdp_planner'"
                    )
                    cur.execute(
                        f"UPDATE {DB.AGENT_REPORTS_TABLE}"
                        f" SET agent_type = 'planner' "
                        f"WHERE agent_type = 'rl'"
                    )
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS
                        {DB.PLANNING_SESSIONS_TABLE} (
                            id SERIAL PRIMARY KEY,
                            username VARCHAR(255)
                                NOT NULL,
                            status VARCHAR(20)
                                NOT NULL
                                DEFAULT 'active',
                            conversation_history JSONB
                                NOT NULL
                                DEFAULT '[]'::jsonb,
                            pending_proposal JSONB,
                            incident_inputs JSONB
                                NOT NULL,
                            agent_config JSONB NOT NULL,
                            context_usage JSONB,
                            ui_state JSONB,
                            created_at TIMESTAMP
                                NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMP
                                NOT NULL DEFAULT NOW()
                        )
                    """)
                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS
                        idx_planning_sessions_username_status
                        ON {DB.PLANNING_SESSIONS_TABLE}
                            (username, status)
                    """)
                    cur.execute(f"""
                        ALTER TABLE
                        {DB.PLANNING_SESSIONS_TABLE}
                        ADD COLUMN IF NOT EXISTS
                            agent_type VARCHAR(50)
                    """)
                    cur.execute(
                        f"UPDATE "
                        f"{DB.PLANNING_SESSIONS_TABLE} "
                        f"SET agent_type = 'planner' "
                        f"WHERE agent_type = 'rl'"
                    )
                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS
                        idx_planning_sessions_agent_type
                        ON {DB.PLANNING_SESSIONS_TABLE}
                            (username, agent_type, status)
                    """)
                    cur.execute(f"""
                        ALTER TABLE
                        {DB.PLANNING_SESSIONS_TABLE}
                        ADD COLUMN IF NOT EXISTS
                            execution_stats JSONB
                    """)

    @staticmethod
    def get_user_by_username(username: str) -> Optional[dict[str, Any]]:
        """
        Look up a user by username.

        :param username: the username to search for
        :return: a dict with id, username, password, salt or None
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id, username, password, salt "
                    f"FROM {DB.MANAGEMENT_USERS_TABLE} "
                    f"WHERE username = %s",
                    (username,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return {
                    "id": row[0],
                    "username": row[1],
                    "password": row[2],
                    "salt": row[3],
                }

    @staticmethod
    def reset_users() -> None:
        """
        Delete all session tokens and users.
        """
        with DatabaseFacade._conn() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        f"DELETE FROM "
                        f"{DB.SESSION_TOKENS_TABLE}"
                    )
                    cur.execute(
                        f"DELETE FROM "
                        f"{DB.MANAGEMENT_USERS_TABLE}"
                    )

    @staticmethod
    def save_user(username: str, password: str) -> None:
        """
        Hash a password with bcrypt and insert a new user.

        Uses ON CONFLICT DO NOTHING so the call is idempotent.

        :param username: the username to create
        :param password: the plaintext password to hash
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {DB.MANAGEMENT_USERS_TABLE} "
                    f"(username, password, salt) "
                    f"VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (username, hashed.decode("utf-8"), salt.decode("utf-8")),
                )

    @staticmethod
    def get_session_token_by_token(token: str) -> Optional[dict[str, Any]]:
        """
        Look up a session token.

        :param token: the token string to search for
        :return: a dict with token, username, timestamp or None
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT token, username, timestamp "
                    f"FROM {DB.SESSION_TOKENS_TABLE} "
                    f"WHERE token = %s",
                    (token,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return {
                    "token": row[0],
                    "username": row[1],
                    "timestamp": row[2],
                }

    @staticmethod
    def update_session_token(username: str, new_token: str) -> None:
        """
        Insert a new session token for the user.

        Multiple tokens may coexist so concurrent sessions do not
        invalidate each other.

        :param username: the username to create a token for
        :param new_token: the new token string
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {DB.SESSION_TOKENS_TABLE} "
                    f"(token, username) VALUES (%s, %s)",
                    (new_token, username),
                )

    @staticmethod
    def get_digital_twin_config() -> Optional[dict[str, Any]]:
        """
        Load the saved digital twin configuration.

        :return: the config dict or None if no config is saved
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT config FROM "
                    f"{DB.DIGITAL_TWIN_CONFIGS_TABLE} "
                    f"WHERE name = 'default' LIMIT 1"
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return row[0]  # type: ignore[no-any-return]

    @staticmethod
    def save_digital_twin_config(config: dict[str, Any]) -> None:
        """
        Upsert the digital twin configuration.

        :param config: the config dict to save
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {DB.DIGITAL_TWIN_CONFIGS_TABLE} "
                    f"(name, config) VALUES ('default', %s) "
                    f"ON CONFLICT (name) DO UPDATE "
                    f"SET config = EXCLUDED.config, "
                    f"updated_at = NOW()",
                    (_sanitize_json(config),),
                )

    @staticmethod
    def delete_digital_twin_config() -> None:
        """
        Delete all saved digital twin configurations.
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {DB.DIGITAL_TWIN_CONFIGS_TABLE}"
                )

    @staticmethod
    def _get_incident_name(
        incident_id: int,
    ) -> Optional[str]:
        """
        Look up an example incident name by id.

        :param incident_id: the example incident id
        :return: the incident name or None
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT name FROM "
                    f"{DB.EXAMPLE_INCIDENTS_TABLE} "
                    f"WHERE id = %s",
                    (incident_id,),
                )
                row = cur.fetchone()
                return row[0] if row else None

    @staticmethod
    def save_agent_report(
        agent_type: str, username: str, report: Any,
        incident_id: Optional[int] = None,
        conversation_history: Optional[list[Any]] = None,
        policy_data: Optional[bytes] = None,
        model_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Insert a new agent report and return the created row.

        :param agent_type: the type of agent (e.g. information, validation)
        :param username: the username who created the report
        :param report: the report data (stored as JSONB)
        :param incident_id: optional FK to example_incidents
        :param conversation_history: optional planning process log
        :param policy_data: optional trained RL policy bytes
        :param model_name: optional LLM name used
        :return: a dict with id, agent_type, username, report, created_at,
                 incident_id, incident_name, model_name
        """
        ch_json = (
            _sanitize_json(conversation_history)
            if conversation_history is not None else None
        )
        report_json = _sanitize_json(report)
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {DB.AGENT_REPORTS_TABLE} "
                    f"(agent_type, username, report, incident_id, "
                    f"conversation_history, policy_data, "
                    f"model_name) "
                    f"VALUES (%s, %s, %s, %s, %s, %s, %s) "
                    f"RETURNING id, agent_type, username, "
                    f"report, created_at, incident_id",
                    (agent_type, username, report_json,
                     incident_id, ch_json, policy_data,
                     model_name),
                )
                row = cur.fetchone()
        if row is None:
            return {}
        incident_name = None
        if row[5] is not None:
            incident_name = DatabaseFacade._get_incident_name(
                row[5]
            )
        return {
            "id": row[0],
            "agent_type": row[1],
            "username": row[2],
            "report": row[3],
            "created_at": str(row[4]),
            "incident_id": row[5],
            "incident_name": incident_name,
        }

    @staticmethod
    def list_agent_reports(
        agent_type: Optional[str] = None,
        incident_id: Optional[int] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        List agent reports, optionally filtered by agent_type and/or
        incident_id.

        :param agent_type: if provided, filter by this agent type
        :param incident_id: if provided, filter by this incident
        :param limit: maximum number of reports to return
        :return: a list of report dicts ordered by created_at DESC
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                base = (
                    f"SELECT ar.id, ar.agent_type, ar.username, "
                    f"ar.report, ar.created_at, ar.incident_id, "
                    f"ei.name, "
                    f"(ar.conversation_history IS NOT NULL), "
                    f"(ar.policy_data IS NOT NULL), "
                    f"ar.model_name "
                    f"FROM {DB.AGENT_REPORTS_TABLE} ar "
                    f"LEFT JOIN {DB.EXAMPLE_INCIDENTS_TABLE} ei "
                    f"ON ar.incident_id = ei.id"
                )
                conditions: list[str] = []
                params: list[Any] = []
                if agent_type:
                    conditions.append("ar.agent_type = %s")
                    params.append(agent_type)
                if incident_id is not None:
                    conditions.append("ar.incident_id = %s")
                    params.append(incident_id)
                if conditions:
                    base += " WHERE " + " AND ".join(conditions)
                base += " ORDER BY ar.created_at DESC LIMIT %s"
                params.append(limit)
                cur.execute(base, tuple(params))
                rows = cur.fetchall()
                return [
                    {
                        "id": r[0],
                        "agent_type": r[1],
                        "username": r[2],
                        "report": r[3],
                        "created_at": str(r[4]),
                        "incident_id": r[5],
                        "incident_name": r[6],
                        "has_conversation_history": r[7],
                        "has_policy": r[8],
                        "model_name": r[9],
                    }
                    for r in rows
                ]

    @staticmethod
    def get_agent_report(
        report_id: int,
    ) -> Optional[dict[str, Any]]:
        """
        Get a single agent report by id.

        :param report_id: the report id
        :return: a report dict or None if not found
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT ar.id, ar.agent_type, ar.username, "
                    f"ar.report, ar.created_at, ar.incident_id, "
                    f"ei.name, ar.conversation_history "
                    f"FROM {DB.AGENT_REPORTS_TABLE} ar "
                    f"LEFT JOIN {DB.EXAMPLE_INCIDENTS_TABLE} ei "
                    f"ON ar.incident_id = ei.id "
                    f"WHERE ar.id = %s",
                    (report_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return {
                    "id": row[0],
                    "agent_type": row[1],
                    "username": row[2],
                    "report": row[3],
                    "created_at": str(row[4]),
                    "incident_id": row[5],
                    "incident_name": row[6],
                    "conversation_history": row[7],
                }

    @staticmethod
    def delete_agent_report(report_id: int) -> bool:
        """
        Delete an agent report by id.

        :param report_id: the report id to delete
        :return: True if a row was deleted, False otherwise
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {DB.AGENT_REPORTS_TABLE} "
                    f"WHERE id = %s",
                    (report_id,),
                )
                deleted = cur.rowcount > 0
            return deleted

    @staticmethod
    def delete_all_agent_reports(agent_type: str) -> int:
        """
        Delete all agent reports for a given agent type.

        :param agent_type: the agent type to delete reports for
        :return: the number of deleted rows
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {DB.AGENT_REPORTS_TABLE} "
                    f"WHERE agent_type = %s",
                    (agent_type,),
                )
                deleted_count = cur.rowcount
            return deleted_count

    @staticmethod
    def get_policy_data(report_id: int) -> Optional[bytes]:
        """
        Retrieve the trained RL policy bytes for a report.

        :param report_id: the agent report id
        :return: the policy bytes or None if not found
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT policy_data FROM "
                    f"{DB.AGENT_REPORTS_TABLE} "
                    f"WHERE id = %s",
                    (report_id,),
                )
                row = cur.fetchone()
                if row is None or row[0] is None:
                    return None
                return bytes(row[0])

    @staticmethod
    def seed_example_incident(
        name: str, data: dict[str, Any],
        dt_config: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Idempotently insert an example incident and optional DT config.

        Uses ON CONFLICT DO NOTHING so repeated calls are safe.

        :param name: unique name for the example incident
        :param data: dict with keys matching example_incidents columns
        :param dt_config: optional digital twin config to link
        """
        with DatabaseFacade._conn() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        f"INSERT INTO "
                        f"{DB.EXAMPLE_INCIDENTS_TABLE} "
                        f"(name, system_description, "
                        f"system_description_image, "
                        f"security_alerts, "
                        f"operator_feedback, specification, "
                        f"incident_report, response_plan) "
                        f"VALUES "
                        f"(%s, %s, %s, %s, %s, %s, %s, %s) "
                        f"ON CONFLICT (name) DO NOTHING "
                        f"RETURNING id",
                        (
                            name,
                            data.get(
                                "system_description", "",
                            ),
                            data.get(
                                "system_description_image",
                                "",
                            ),
                            data.get(
                                "security_alerts", "",
                            ),
                            data.get(
                                "operator_feedback", "",
                            ),
                            data.get("specification", ""),
                            data.get(
                                "incident_report", "",
                            ),
                            data.get("response_plan", ""),
                        ),
                    )
                    row = cur.fetchone()
                    if (
                        row is not None
                        and dt_config is not None
                    ):
                        incident_id = row[0]
                        cur.execute(
                            f"INSERT INTO "
                            f"{DB.DIGITAL_TWIN_CONFIGS_TABLE}"
                            f" (name, config, "
                            f"example_incident_id) "
                            f"VALUES (%s, %s, %s) "
                            f"ON CONFLICT (name) DO UPDATE "
                            f"SET config = EXCLUDED.config",
                            (
                                name,
                                _sanitize_json(dt_config),
                                incident_id,
                            ),
                        )

    @staticmethod
    def list_example_incidents() -> list[dict[str, Any]]:
        """
        List all example incidents (summary only).

        :return: a list of dicts with id and name
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id, name FROM "
                    f"{DB.EXAMPLE_INCIDENTS_TABLE} "
                    f"ORDER BY id"
                )
                return [
                    {"id": r[0], "name": r[1]}
                    for r in cur.fetchall()
                ]

    @staticmethod
    def get_example_incident(
        incident_id: int,
    ) -> Optional[dict[str, Any]]:
        """
        Get a full example incident by id.

        :param incident_id: the example incident id
        :return: a dict with all fields or None if not found
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id, name, system_description, "
                    f"system_description_image, security_alerts, "
                    f"operator_feedback, specification, "
                    f"incident_report, response_plan "
                    f"FROM {DB.EXAMPLE_INCIDENTS_TABLE} "
                    f"WHERE id = %s",
                    (incident_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return {
                    "id": row[0],
                    "name": row[1],
                    "system_description": row[2],
                    "system_description_image": row[3],
                    "security_alerts": row[4],
                    "operator_feedback": row[5],
                    "specification": row[6],
                    "incident_report": row[7],
                    "response_plan": row[8],
                }

    @staticmethod
    def list_digital_twin_configs() -> list[dict[str, Any]]:
        """
        List all digital twin configs (summary only).

        :return: a list of dicts with id, name, example_incident_id
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id, name, example_incident_id "
                    f"FROM {DB.DIGITAL_TWIN_CONFIGS_TABLE} "
                    f"ORDER BY id"
                )
                return [
                    {
                        "id": r[0],
                        "name": r[1],
                        "example_incident_id": r[2],
                    }
                    for r in cur.fetchall()
                ]

    @staticmethod
    def get_config_id_by_incident(
        incident_id: int,
    ) -> Optional[int]:
        """
        Look up the digital twin config linked to an example incident.

        :param incident_id: the example incident id
        :return: the config id or None
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id FROM "
                    f"{DB.DIGITAL_TWIN_CONFIGS_TABLE} "
                    f"WHERE example_incident_id = %s "
                    f"LIMIT 1",
                    (incident_id,),
                )
                row = cur.fetchone()
                return row[0] if row else None

    @staticmethod
    def get_digital_twin_config_by_id(
        config_id: int,
    ) -> Optional[dict[str, Any]]:
        """
        Get a full digital twin config by id.

        :param config_id: the config id
        :return: a dict with id, name, config, example_incident_id
                 or None if not found
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id, name, config, "
                    f"example_incident_id "
                    f"FROM {DB.DIGITAL_TWIN_CONFIGS_TABLE} "
                    f"WHERE id = %s",
                    (config_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return {
                    "id": row[0],
                    "name": row[1],
                    "config": row[2],
                    "example_incident_id": row[3],
                }

    @staticmethod
    def save_validation_results(
        config_id: int, results: list[dict[str, Any]],
    ) -> None:
        """
        Save validation results for a digital twin config.

        Overwrites any previous results for this config.

        :param config_id: the config id
        :param results: list of validation result dicts
        """
        from datetime import datetime, timezone
        payload = {
            "results": results,
            "tested_at": datetime.now(timezone.utc).isoformat(),
        }
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {DB.DIGITAL_TWIN_CONFIGS_TABLE} "
                    f"SET validation_results = %s "
                    f"WHERE id = %s",
                    (_sanitize_json(payload), config_id),
                )

    @staticmethod
    def get_validation_results(
        config_id: int,
    ) -> Optional[dict[str, Any]]:
        """
        Get the stored validation results for a config.

        :param config_id: the config id
        :return: a dict with results and tested_at, or None
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT validation_results FROM "
                    f"{DB.DIGITAL_TWIN_CONFIGS_TABLE} "
                    f"WHERE id = %s",
                    (config_id,),
                )
                row = cur.fetchone()
                if row is None or row[0] is None:
                    return None
                return row[0]  # type: ignore[no-any-return]

    @staticmethod
    def get_active_planning_session(
        username: str,
        agent_type: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Get the active planning session for a user.

        :param username: the username to search for
        :param agent_type: optional agent type filter
        :return: a dict with session data or None
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                if agent_type is not None:
                    cur.execute(
                        f"SELECT id, username, status, "
                        f"conversation_history, "
                        f"pending_proposal, "
                        f"incident_inputs, "
                        f"agent_config, context_usage, "
                        f"ui_state, "
                        f"created_at, updated_at, "
                        f"agent_type, "
                        f"execution_stats "
                        f"FROM "
                        f"{DB.PLANNING_SESSIONS_TABLE} "
                        f"WHERE username = %s "
                        f"AND status = 'active' "
                        f"AND agent_type = %s "
                        f"ORDER BY created_at DESC "
                        f"LIMIT 1",
                        (username, agent_type),
                    )
                else:
                    cur.execute(
                        f"SELECT id, username, status, "
                        f"conversation_history, "
                        f"pending_proposal, "
                        f"incident_inputs, "
                        f"agent_config, context_usage, "
                        f"ui_state, "
                        f"created_at, updated_at, "
                        f"agent_type, "
                        f"execution_stats "
                        f"FROM "
                        f"{DB.PLANNING_SESSIONS_TABLE} "
                        f"WHERE username = %s "
                        f"AND status = 'active' "
                        f"AND agent_type IS NULL "
                        f"ORDER BY created_at DESC "
                        f"LIMIT 1",
                        (username,),
                    )
                row = cur.fetchone()
                if row is None:
                    return None
                return {
                    "id": row[0],
                    "username": row[1],
                    "status": row[2],
                    "conversation_history": row[3],
                    "pending_proposal": row[4],
                    "incident_inputs": row[5],
                    "agent_config": row[6],
                    "context_usage": row[7],
                    "ui_state": row[8],
                    "created_at": str(row[9]),
                    "updated_at": str(row[10]),
                    "agent_type": row[11],
                    "execution_stats": row[12],
                }

    @staticmethod
    def get_planning_session(
        session_id: int,
        username: str,
    ) -> Optional[dict[str, Any]]:
        """
        Get a specific planning session by id.

        :param session_id: the session id
        :param username: the username (ownership check)
        :return: a dict with session data or None
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id, username, status, "
                    f"conversation_history, "
                    f"pending_proposal, "
                    f"incident_inputs, "
                    f"agent_config, context_usage, "
                    f"ui_state, "
                    f"created_at, updated_at, "
                    f"agent_type, "
                    f"execution_stats "
                    f"FROM "
                    f"{DB.PLANNING_SESSIONS_TABLE} "
                    f"WHERE id = %s "
                    f"AND username = %s",
                    (session_id, username),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return {
                    "id": row[0],
                    "username": row[1],
                    "status": row[2],
                    "conversation_history": row[3],
                    "pending_proposal": row[4],
                    "incident_inputs": row[5],
                    "agent_config": row[6],
                    "context_usage": row[7],
                    "ui_state": row[8],
                    "created_at": str(row[9]),
                    "updated_at": str(row[10]),
                    "agent_type": row[11],
                    "execution_stats": row[12],
                }

    @staticmethod
    def create_planning_session(
        username: str,
        incident_inputs: dict[str, Any],
        agent_config: dict[str, Any],
        agent_type: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a new planning session for a user.

        Auto-cancels any existing active session for this user
        with the same agent_type.

        :param username: the username creating the session
        :param incident_inputs: incident description and images
        :param agent_config: model selections and configuration
        :param agent_type: optional agent type tag
        :return: the created session dict
        """
        with DatabaseFacade._conn() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    if agent_type is not None:
                        cur.execute(
                            f"UPDATE "
                            f"{DB.PLANNING_SESSIONS_TABLE} "
                            f"SET status = 'cancelled', "
                            f"updated_at = NOW() "
                            f"WHERE username = %s "
                            f"AND status = 'active' "
                            f"AND agent_type = %s",
                            (username, agent_type),
                        )
                    else:
                        cur.execute(
                            f"UPDATE "
                            f"{DB.PLANNING_SESSIONS_TABLE} "
                            f"SET status = 'cancelled', "
                            f"updated_at = NOW() "
                            f"WHERE username = %s "
                            f"AND status = 'active' "
                            f"AND agent_type IS NULL",
                            (username,),
                        )
                    cur.execute(
                        f"INSERT INTO "
                        f"{DB.PLANNING_SESSIONS_TABLE} "
                        f"(username, status, "
                        f"conversation_history, "
                        f"incident_inputs, "
                        f"agent_config, "
                        f"agent_type) "
                        f"VALUES (%s, 'active', "
                        f"'[]'::jsonb, %s, %s, %s) "
                        f"RETURNING id, username, "
                        f"status, "
                        f"conversation_history, "
                        f"pending_proposal, "
                        f"incident_inputs, "
                        f"agent_config, "
                        f"context_usage, "
                        f"ui_state, "
                        f"created_at, updated_at, "
                        f"agent_type, "
                        f"execution_stats",
                        (
                            username,
                            _sanitize_json(
                                incident_inputs,
                            ),
                            _sanitize_json(agent_config),
                            agent_type,
                        ),
                    )
                    row = cur.fetchone()
            if row is None:
                return {}
            return {
                "id": row[0],
                "username": row[1],
                "status": row[2],
                "conversation_history": row[3],
                "pending_proposal": row[4],
                "incident_inputs": row[5],
                "agent_config": row[6],
                "context_usage": row[7],
                "ui_state": row[8],
                "created_at": str(row[9]),
                "updated_at": str(row[10]),
                "agent_type": row[11],
                "execution_stats": row[12],
            }

    @staticmethod
    def update_planning_session(
        session_id: int,
        username: str,
        conversation_history: Optional[list[Any]] = None,
        append_history: Optional[list[Any]] = None,
        pending_proposal: Any = None,
        context_usage: Optional[dict[str, Any]] = None,
        status: Optional[str] = None,
        ui_state: Optional[dict[str, Any]] = None,
        execution_stats: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Update a planning session.

        Only updates fields that are not None.
        Pass pending_proposal=False to clear it.

        :param session_id: the session id to update
        :param username: the username (ownership check)
        :param conversation_history: optional full replacement
        :param append_history: optional entries to append
        :param pending_proposal: optional pending proposal
        :param context_usage: optional context usage stats
        :param status: optional new status
        :param ui_state: optional ephemeral UI state
        :param execution_stats: optional execution statistics
        :return: True if the session was updated
        """
        updates: list[str] = []
        params: list[Any] = []
        if append_history is not None and len(
            append_history
        ) > 0:
            updates.append(
                "conversation_history = "
                "COALESCE(conversation_history, "
                "'[]'::jsonb) || %s::jsonb"
            )
            params.append(
                _sanitize_json(append_history)
            )
        elif conversation_history is not None:
            updates.append(
                "conversation_history = %s"
            )
            params.append(
                _sanitize_json(conversation_history)
            )
        if pending_proposal is not None:
            if pending_proposal is False:
                updates.append(
                    "pending_proposal = NULL"
                )
            else:
                updates.append(
                    "pending_proposal = %s"
                )
                params.append(
                    _sanitize_json(pending_proposal)
                )
        if context_usage is not None:
            updates.append("context_usage = %s")
            params.append(
                _sanitize_json(context_usage)
            )
        if status is not None:
            updates.append("status = %s")
            params.append(status)
        if ui_state is not None:
            updates.append("ui_state = %s")
            params.append(
                _sanitize_json(ui_state)
            )
        if execution_stats is not None:
            updates.append(
                "execution_stats = %s"
            )
            params.append(
                _sanitize_json(execution_stats)
            )
        if not updates:
            return False
        updates.append("updated_at = NOW()")
        params.extend([session_id, username])
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE "
                    f"{DB.PLANNING_SESSIONS_TABLE} "
                    f"SET {', '.join(updates)} "
                    f"WHERE id = %s "
                    f"AND username = %s",
                    tuple(params),
                )
                updated = cur.rowcount > 0
            return updated

    @staticmethod
    def delete_planning_session(
        session_id: int,
        username: str,
    ) -> bool:
        """
        Delete a planning session.

        :param session_id: the session id to delete
        :param username: the username (ownership check)
        :return: True if the session was deleted
        """
        with DatabaseFacade._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM "
                    f"{DB.PLANNING_SESSIONS_TABLE} "
                    f"WHERE id = %s "
                    f"AND username = %s",
                    (session_id, username),
                )
                deleted = cur.rowcount > 0
            return deleted
