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
        Create all application tables if they do not exist.
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
                        {DB.EXAMPLE_INCIDENTS_TABLE} (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) UNIQUE NOT NULL,
                        system_description TEXT NOT NULL DEFAULT '',
                        system_description_image TEXT NOT NULL DEFAULT '',
                        security_alerts TEXT NOT NULL DEFAULT '',
                        operator_feedback TEXT NOT NULL DEFAULT '',
                        specification TEXT NOT NULL DEFAULT '',
                        incident_report TEXT NOT NULL DEFAULT '',
                        response_plan TEXT NOT NULL DEFAULT '',
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
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
                    ALTER TABLE {DB.DIGITAL_TWIN_CONFIGS_TABLE}
                    ADD COLUMN IF NOT EXISTS example_incident_id INTEGER
                        REFERENCES {DB.EXAMPLE_INCIDENTS_TABLE}(id)
                        ON DELETE SET NULL
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
                cur.execute(f"""
                    ALTER TABLE {DB.AGENT_REPORTS_TABLE}
                    ADD COLUMN IF NOT EXISTS incident_id INTEGER
                        REFERENCES {DB.EXAMPLE_INCIDENTS_TABLE}(id)
                        ON DELETE SET NULL
                """)
                cur.execute(f"""
                    ALTER TABLE {DB.DIGITAL_TWIN_CONFIGS_TABLE}
                    ADD COLUMN IF NOT EXISTS
                        validation_results JSONB
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
    def _get_incident_name(
        incident_id: int,
    ) -> Optional[str]:
        """
        Look up an example incident name by id.

        :param incident_id: the example incident id
        :return: the incident name or None
        """
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
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
    ) -> dict[str, Any]:
        """
        Insert a new agent report and return the created row.

        :param agent_type: the type of agent (e.g. information, pentest, validation)
        :param username: the username who created the report
        :param report: the report data (stored as JSONB)
        :param incident_id: optional FK to example_incidents
        :return: a dict with id, agent_type, username, report, created_at,
                 incident_id, incident_name
        """
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {DB.AGENT_REPORTS_TABLE} "
                    f"(agent_type, username, report, incident_id) "
                    f"VALUES (%s, %s, %s, %s) "
                    f"RETURNING id, agent_type, username, "
                    f"report, created_at, incident_id",
                    (agent_type, username, json.dumps(report),
                     incident_id),
                )
                row = cur.fetchone()
            conn.commit()
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
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
            with conn.cursor() as cur:
                base = (
                    f"SELECT ar.id, ar.agent_type, ar.username, "
                    f"ar.report, ar.created_at, ar.incident_id, "
                    f"ei.name "
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
                    f"SELECT ar.id, ar.agent_type, ar.username, "
                    f"ar.report, ar.created_at, ar.incident_id, "
                    f"ei.name "
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
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {DB.EXAMPLE_INCIDENTS_TABLE} "
                    f"(name, system_description, "
                    f"system_description_image, security_alerts, "
                    f"operator_feedback, specification, "
                    f"incident_report, response_plan) "
                    f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                    f"ON CONFLICT (name) DO NOTHING "
                    f"RETURNING id",
                    (
                        name,
                        data.get("system_description", ""),
                        data.get("system_description_image", ""),
                        data.get("security_alerts", ""),
                        data.get("operator_feedback", ""),
                        data.get("specification", ""),
                        data.get("incident_report", ""),
                        data.get("response_plan", ""),
                    ),
                )
                row = cur.fetchone()
                if row is not None and dt_config is not None:
                    incident_id = row[0]
                    cur.execute(
                        f"INSERT INTO "
                        f"{DB.DIGITAL_TWIN_CONFIGS_TABLE} "
                        f"(name, config, example_incident_id) "
                        f"VALUES (%s, %s, %s) "
                        f"ON CONFLICT (name) DO UPDATE "
                        f"SET config = EXCLUDED.config",
                        (
                            name,
                            json.dumps(dt_config),
                            incident_id,
                        ),
                    )
            conn.commit()

    @staticmethod
    def list_example_incidents() -> list[dict[str, Any]]:
        """
        List all example incidents (summary only).

        :return: a list of dicts with id and name
        """
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
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
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
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
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
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
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
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
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
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
        with psycopg.connect(
            DatabaseFacade._connection_string(),
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {DB.DIGITAL_TWIN_CONFIGS_TABLE} "
                    f"SET validation_results = %s "
                    f"WHERE id = %s",
                    (json.dumps(payload), config_id),
                )
            conn.commit()

    @staticmethod
    def get_validation_results(
        config_id: int,
    ) -> Optional[dict[str, Any]]:
        """
        Get the stored validation results for a config.

        :param config_id: the config id
        :return: a dict with results and tested_at, or None
        """
        with psycopg.connect(
            DatabaseFacade._connection_string(),
        ) as conn:
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
