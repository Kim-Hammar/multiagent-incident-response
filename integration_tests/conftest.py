"""Shared fixtures for Python integration tests."""
import os
from typing import Generator

import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8888")


def _docker_available() -> bool:
    """
    Return True if the Docker daemon is reachable.

    :return: True when Docker is available
    """
    try:
        import docker
        docker.from_env().ping()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def base_url() -> str:
    """
    Return the base URL of the running application.

    :return: the base URL string
    """
    return BASE_URL


@pytest.fixture(scope="session")
def auth_headers(base_url: str) -> dict[str, str]:
    """
    Log in to the running app and return Bearer auth headers.

    :param base_url: the base URL of the running application
    :return: a dict with the Authorization header
    """
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "admin")
    resp = requests.post(
        f"{base_url}/api/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"Login failed: {resp.status_code} {resp.text}"
    )
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def deploy_dt(
    base_url: str, auth_headers: dict[str, str],
) -> Generator[None, None, None]:
    """
    Deploy the digital twin before DT tests and stop it afterwards.

    Skips all dependent tests when Docker is not available.

    :param base_url: the base URL of the running application
    :param auth_headers: Bearer auth headers
    :return: yields once the DT is deployed
    """
    if not _docker_available():
        pytest.skip("Docker not available")
    resp = requests.post(
        f"{base_url}/api/digital-twin/deploy",
        headers=auth_headers, timeout=180,
    )
    assert resp.status_code == 200, (
        f"DT deploy failed: {resp.status_code} {resp.text}"
    )
    yield
    requests.post(
        f"{base_url}/api/digital-twin/stop",
        headers=auth_headers, timeout=120,
    )
