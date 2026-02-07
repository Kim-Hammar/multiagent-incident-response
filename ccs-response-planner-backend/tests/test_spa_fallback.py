"""Integration tests for static file serving and the SPA root route."""
import os

from flask.testing import FlaskClient


def test_root_serves_index_html(
    client: FlaskClient, static_dir: str
) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert b"<html><body>test</body></html>" in response.data


def test_existing_static_file_served_directly(
    client: FlaskClient, static_dir: str
) -> None:
    css_path = os.path.join(static_dir, "style.css")
    with open(css_path, "w") as f:
        f.write("body { color: red; }")
    response = client.get("/style.css")
    assert response.status_code == 200
    assert b"body { color: red; }" in response.data


def test_nonexistent_static_file_returns_404(
    client: FlaskClient, static_dir: str
) -> None:
    response = client.get("/no-such-file.js")
    assert response.status_code == 404
