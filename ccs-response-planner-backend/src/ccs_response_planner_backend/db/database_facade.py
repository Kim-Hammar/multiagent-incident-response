"""
Database facade for managing users and session tokens.
"""
import json
import os
from typing import Any, Optional

import bcrypt
import psycopg

from ccs_response_planner_backend.constants.constants import DB


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
            f"user={user} password={password}"
        )

    @staticmethod
    def create_tables() -> None:
        """
        Create the management_users and session_tokens tables if they do not exist.
        """
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {DB.MANAGEMENT_USERS_TABLE} (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        salt VARCHAR(255) NOT NULL
                    )
                """)
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {DB.SESSION_TOKENS_TABLE} (
                        token VARCHAR(255) PRIMARY KEY,
                        username VARCHAR(255) NOT NULL
                            REFERENCES {DB.MANAGEMENT_USERS_TABLE}(username),
                        timestamp TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """)
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS
                        {DB.DIGITAL_TWIN_CONFIGS_TABLE} (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) UNIQUE NOT NULL DEFAULT 'default',
                        config JSONB NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """)
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS
                        {DB.AGENT_REPORTS_TABLE} (
                        id SERIAL PRIMARY KEY,
                        agent_type VARCHAR(50) NOT NULL,
                        username VARCHAR(255) NOT NULL,
                        report JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
            conn.commit()

    @staticmethod
    def get_user_by_username(username: str) -> Optional[dict[str, Any]]:
        """
        Look up a user by username.

        :param username: the username to search for
        :return: a dict with id, username, password, salt or None
        """
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
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
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {DB.SESSION_TOKENS_TABLE}"
                )
                cur.execute(
                    f"DELETE FROM {DB.MANAGEMENT_USERS_TABLE}"
                )
            conn.commit()

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
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {DB.MANAGEMENT_USERS_TABLE} "
                    f"(username, password, salt) "
                    f"VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (username, hashed.decode("utf-8"), salt.decode("utf-8")),
                )
            conn.commit()

    @staticmethod
    def get_session_token_by_token(token: str) -> Optional[dict[str, Any]]:
        """
        Look up a session token.

        :param token: the token string to search for
        :return: a dict with token, username, timestamp or None
        """
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
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
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {DB.SESSION_TOKENS_TABLE} "
                    f"(token, username) VALUES (%s, %s)",
                    (new_token, username),
                )
            conn.commit()

    @staticmethod
    def get_digital_twin_config() -> Optional[dict[str, Any]]:
        """
        Load the saved digital twin configuration.

        :return: the config dict or None if no config is saved
        """
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT config FROM "
                    f"{DB.DIGITAL_TWIN_CONFIGS_TABLE} LIMIT 1"
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
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {DB.DIGITAL_TWIN_CONFIGS_TABLE} "
                    f"(name, config) VALUES ('default', %s) "
                    f"ON CONFLICT (name) DO UPDATE "
                    f"SET config = EXCLUDED.config, "
                    f"updated_at = NOW()",
                    (json.dumps(config),),
                )
            conn.commit()

    @staticmethod
    def delete_digital_twin_config() -> None:
        """
        Delete all saved digital twin configurations.
        """
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {DB.DIGITAL_TWIN_CONFIGS_TABLE}"
                )
            conn.commit()

    @staticmethod
    def save_agent_report(
        agent_type: str, username: str, report: Any
    ) -> dict[str, Any]:
        """
        Insert a new agent report and return the created row.

        :param agent_type: the type of agent (e.g. information, pentest, validation)
        :param username: the username who created the report
        :param report: the report data (stored as JSONB)
        :return: a dict with id, agent_type, username, report, created_at
        """
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {DB.AGENT_REPORTS_TABLE} "
                    f"(agent_type, username, report) "
                    f"VALUES (%s, %s, %s) "
                    f"RETURNING id, agent_type, username, "
                    f"report, created_at",
                    (agent_type, username, json.dumps(report)),
                )
                row = cur.fetchone()
            conn.commit()
            if row is None:
                return {}
            return {
                "id": row[0],
                "agent_type": row[1],
                "username": row[2],
                "report": row[3],
                "created_at": str(row[4]),
            }

    @staticmethod
    def list_agent_reports(
        agent_type: Optional[str] = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        List agent reports, optionally filtered by agent_type.

        :param agent_type: if provided, filter by this agent type
        :param limit: maximum number of reports to return
        :return: a list of report dicts ordered by created_at DESC
        """
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
            with conn.cursor() as cur:
                if agent_type:
                    cur.execute(
                        f"SELECT id, agent_type, username, "
                        f"report, created_at "
                        f"FROM {DB.AGENT_REPORTS_TABLE} "
                        f"WHERE agent_type = %s "
                        f"ORDER BY created_at DESC "
                        f"LIMIT %s",
                        (agent_type, limit),
                    )
                else:
                    cur.execute(
                        f"SELECT id, agent_type, username, "
                        f"report, created_at "
                        f"FROM {DB.AGENT_REPORTS_TABLE} "
                        f"ORDER BY created_at DESC "
                        f"LIMIT %s",
                        (limit,),
                    )
                rows = cur.fetchall()
                return [
                    {
                        "id": r[0],
                        "agent_type": r[1],
                        "username": r[2],
                        "report": r[3],
                        "created_at": str(r[4]),
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
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id, agent_type, username, "
                    f"report, created_at "
                    f"FROM {DB.AGENT_REPORTS_TABLE} "
                    f"WHERE id = %s",
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
                }

    @staticmethod
    def delete_agent_report(report_id: int) -> bool:
        """
        Delete an agent report by id.

        :param report_id: the report id to delete
        :return: True if a row was deleted, False otherwise
        """
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {DB.AGENT_REPORTS_TABLE} "
                    f"WHERE id = %s",
                    (report_id,),
                )
                deleted = cur.rowcount > 0
            conn.commit()
            return deleted
