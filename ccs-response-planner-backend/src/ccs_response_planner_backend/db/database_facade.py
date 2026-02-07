"""
Database facade for managing users and session tokens.
"""
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
        Delete any existing session token for the user and insert a new one.

        :param username: the username whose token to replace
        :param new_token: the new token string
        """
        with psycopg.connect(DatabaseFacade._connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {DB.SESSION_TOKENS_TABLE} "
                    f"WHERE username = %s",
                    (username,),
                )
                cur.execute(
                    f"INSERT INTO {DB.SESSION_TOKENS_TABLE} "
                    f"(token, username) VALUES (%s, %s)",
                    (new_token, username),
                )
            conn.commit()
