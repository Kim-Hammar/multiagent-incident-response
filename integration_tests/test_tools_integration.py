"""
Integration tests for tool endpoints against real external APIs.

These tests run against a live application (started by integration_tests.sh)
and use real HTTP requests via the ``requests`` library.

Each test group is skipped when its API key is not set, except for
NVD (works without a key, just rate-limited) and MITRE ATT&CK
(uses a local STIX bundle, no key needed).

Docker-based tool tests (DT Exec, DT Logs, DT Python) are skipped
when Docker is not available.  DT Exec and DT Logs additionally
require a deployed digital twin.
"""
import os

import pytest
import requests as http


_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
_TAVILY_KEY = os.environ.get("TAVILY_API_KEY", "")
_NVD_KEY = os.environ.get("NVD_API_KEY", "")
_VIRUSTOTAL_KEY = os.environ.get("VIRUSTOTAL_API_KEY", "")
_ABUSEIPDB_KEY = os.environ.get("ABUSEIPDB_API_KEY", "")
_OTX_KEY = os.environ.get("OTX_API_KEY", "")


def _docker_available() -> bool:
    """
    Return True if the Docker daemon is reachable.
    """
    try:
        import docker
        docker.from_env().ping()
        return True
    except Exception:
        return False


def _sandbox_image_exists() -> bool:
    """
    Return True when the ``ccs-dt-python-sandbox`` image is available.
    """
    try:
        import docker
        client = docker.from_env()
        client.images.get("ccs-dt-python-sandbox:latest")
        return True
    except Exception:
        return False


# ── LLM (Gemini) ───────────────────────────────────────────────────

@pytest.mark.skipif(not _GEMINI_KEY, reason="GEMINI_API_KEY not set")
class TestLlmIntegration:
    """Integration tests for the Gemini LLM connection."""

    def test_connection(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.get(
            f"{base_url}/api/llm", headers=auth_headers,
            timeout=30,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["status"] == "connected"
        assert len(data["models"]) > 0


# ── Tavily ──────────────────────────────────────────────────────────

@pytest.mark.skipif(not _TAVILY_KEY, reason="TAVILY_API_KEY not set")
class TestTavilyIntegration:
    """Integration tests for the Tavily Search API."""

    def test_connection(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.get(
            f"{base_url}/api/tavily", headers=auth_headers,
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["status"] == "connected"

    def test_search(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.post(
            f"{base_url}/api/tavily/search",
            json={"query": "OWASP top 10", "max_results": 2},
            headers=auth_headers, timeout=30,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert "results" in data
        assert len(data["results"]) > 0


# ── NVD ─────────────────────────────────────────────────────────────

class TestNvdIntegration:
    """Integration tests for the NVD / CVE Database (no key required)."""

    def test_connection(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.get(
            f"{base_url}/api/nvd", headers=auth_headers,
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["status"] == "connected"
        assert data["cve_count"] >= 1

    def test_search_by_cve_id(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.post(
            f"{base_url}/api/nvd/search",
            json={"cve_id": "CVE-2021-44228"},
            headers=auth_headers, timeout=30,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert len(data["results"]) == 1
        assert data["results"][0]["id"] == "CVE-2021-44228"
        assert data["results"][0]["score"] is not None

    def test_search_by_keyword(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.post(
            f"{base_url}/api/nvd/search",
            json={"keyword": "log4j", "results_per_page": 3},
            headers=auth_headers, timeout=30,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert len(data["results"]) > 0


# ── MITRE ATT&CK ───────────────────────────────────────────────────

class TestMitreIntegration:
    """Integration tests for MITRE ATT&CK (no key required)."""

    def test_connection(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.get(
            f"{base_url}/api/mitre", headers=auth_headers,
            timeout=60,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["status"] == "connected"
        assert data["technique_count"] > 100

    def test_search_by_id(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.post(
            f"{base_url}/api/mitre/search",
            json={"technique_id": "T1110"},
            headers=auth_headers, timeout=30,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert len(data["results"]) == 1
        assert data["results"][0]["id"] == "T1110"
        assert data["results"][0]["name"] == "Brute Force"

    def test_search_by_keyword(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.post(
            f"{base_url}/api/mitre/search",
            json={"search": "phishing"},
            headers=auth_headers, timeout=30,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert len(data["results"]) > 0


# ── VirusTotal ──────────────────────────────────────────────────────

@pytest.mark.skipif(
    not _VIRUSTOTAL_KEY, reason="VIRUSTOTAL_API_KEY not set",
)
class TestVirusTotalIntegration:
    """Integration tests for the VirusTotal API."""

    def test_connection(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.get(
            f"{base_url}/api/virustotal", headers=auth_headers,
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["status"] == "connected"

    def test_scan_domain(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.post(
            f"{base_url}/api/virustotal/scan",
            json={"type": "domain", "value": "google.com"},
            headers=auth_headers, timeout=30,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["type"] == "domain"
        assert data["result"]["value"] == "google.com"
        assert data["result"]["last_analysis_stats"] is not None

    def test_scan_ip(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.post(
            f"{base_url}/api/virustotal/scan",
            json={"type": "ip", "value": "8.8.8.8"},
            headers=auth_headers, timeout=30,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["type"] == "ip"


# ── AbuseIPDB ───────────────────────────────────────────────────────

@pytest.mark.skipif(
    not _ABUSEIPDB_KEY, reason="ABUSEIPDB_API_KEY not set",
)
class TestAbuseIPDBIntegration:
    """Integration tests for the AbuseIPDB API."""

    def test_connection(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.get(
            f"{base_url}/api/abuseipdb", headers=auth_headers,
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["status"] == "connected"

    def test_check_ip(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.post(
            f"{base_url}/api/abuseipdb/check",
            json={"ip": "8.8.8.8"},
            headers=auth_headers, timeout=30,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["ip"] == "8.8.8.8"
        assert data["result"]["abuse_confidence_score"] is not None
        assert data["result"]["country_code"] == "US"


# ── OTX ─────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _OTX_KEY, reason="OTX_API_KEY not set")
class TestOtxIntegration:
    """Integration tests for the AlienVault OTX API."""

    def test_connection(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.get(
            f"{base_url}/api/otx", headers=auth_headers,
            timeout=60,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["status"] == "connected"

    def test_search_ipv4(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.post(
            f"{base_url}/api/otx/search",
            json={"type": "IPv4", "value": "8.8.8.8"},
            headers=auth_headers, timeout=90,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["type"] == "IPv4"
        assert data["result"]["value"] == "8.8.8.8"
        assert data["result"]["pulse_count"] is not None

    def test_search_domain(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.post(
            f"{base_url}/api/otx/search",
            json={"type": "domain", "value": "google.com"},
            headers=auth_headers, timeout=90,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["result"]["type"] == "domain"


# ── DT Execute ─────────────────────────────────────────────────────

class TestDtExecIntegration:
    """Integration tests for DT Execute (requires deployed DT)."""

    def test_connection(
        self, deploy_dt: None,
        base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.get(
            f"{base_url}/api/dt-exec", headers=auth_headers,
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["status"] == "connected"
        assert data["count"] >= 1

    def test_run_command(
        self, deploy_dt: None,
        base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.post(
            f"{base_url}/api/dt-exec/run",
            json={"container": "gateway", "command": "echo hello"},
            headers=auth_headers, timeout=30,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["exit_code"] == 0
        assert "hello" in data["output"]


# ── DT Logs ────────────────────────────────────────────────────────

class TestDtLogsIntegration:
    """Integration tests for DT Logs (requires deployed DT)."""

    def test_connection(
        self, deploy_dt: None,
        base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.get(
            f"{base_url}/api/dt-logs", headers=auth_headers,
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["status"] == "connected"
        assert data["count"] >= 1

    def test_fetch_logs(
        self, deploy_dt: None,
        base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.post(
            f"{base_url}/api/dt-logs/fetch",
            json={"container": "gateway", "tail": 10},
            headers=auth_headers, timeout=30,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["container"] == "gateway"
        assert "output" in data
        assert "lines" in data


# ── DT Python Sandbox ──────────────────────────────────────────────

@pytest.mark.skipif(
    not _docker_available() or not _sandbox_image_exists(),
    reason="Docker not available or sandbox image not built",
)
class TestDtPythonIntegration:
    """Integration tests for the DT Python Sandbox."""

    def test_connection(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.get(
            f"{base_url}/api/dt-python", headers=auth_headers,
            timeout=10,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["status"] == "connected"
        assert "container_status" in data

    def test_run_code(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.post(
            f"{base_url}/api/dt-python/run",
            json={"code": "print(2 + 2)"},
            headers=auth_headers, timeout=60,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["exit_code"] == 0
        assert "4" in data["output"]
        assert data["test"] is False

    def test_run_pytest(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.post(
            f"{base_url}/api/dt-python/run",
            json={
                "code": "def test_addition():\n    assert 1 + 1 == 2\n",
                "test": True,
            },
            headers=auth_headers, timeout=60,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["exit_code"] == 0
        assert data["test"] is True
        assert "passed" in data["output"]

    def test_run_with_numpy(
        self, base_url: str, auth_headers: dict[str, str],
    ) -> None:
        resp = http.post(
            f"{base_url}/api/dt-python/run",
            json={
                "code": (
                    "import numpy as np\n"
                    "print(np.array([1,2,3]).sum())\n"
                ),
            },
            headers=auth_headers, timeout=60,
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["exit_code"] == 0
        assert "6" in data["output"]
