"""
Integration tests for tool endpoints against real external APIs.

Each test group is skipped when its API key is not set, except for
NVD (works without a key, just rate-limited) and MITRE ATT&CK
(uses a local STIX bundle, no key needed).
"""
import os

import pytest
from flask.testing import FlaskClient

_TAVILY_KEY = os.environ.get("TAVILY_API_KEY", "")
_NVD_KEY = os.environ.get("NVD_API_KEY", "")
_VIRUSTOTAL_KEY = os.environ.get("VIRUSTOTAL_API_KEY", "")
_ABUSEIPDB_KEY = os.environ.get("ABUSEIPDB_API_KEY", "")
_OTX_KEY = os.environ.get("OTX_API_KEY", "")


# ── Tavily ──────────────────────────────────────────────────────────

@pytest.mark.skipif(not _TAVILY_KEY, reason="TAVILY_API_KEY not set")
class TestTavilyIntegration:
    """Integration tests for the Tavily Search API."""

    def test_connection(
        self, client: FlaskClient, auth_headers: dict[str, str],
    ) -> None:
        resp = client.get("/api/tavily", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["status"] == "connected"

    def test_search(
        self, client: FlaskClient, auth_headers: dict[str, str],
    ) -> None:
        resp = client.post(
            "/api/tavily/search",
            json={"query": "OWASP top 10", "max_results": 2},
            headers=auth_headers,
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert "results" in data
        assert len(data["results"]) > 0


# ── NVD ─────────────────────────────────────────────────────────────

class TestNvdIntegration:
    """Integration tests for the NVD / CVE Database (no key required)."""

    def test_connection(
        self, client: FlaskClient, auth_headers: dict[str, str],
    ) -> None:
        resp = client.get("/api/nvd", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["status"] == "connected"
        assert data["cve_count"] >= 1

    def test_search_by_cve_id(
        self, client: FlaskClient, auth_headers: dict[str, str],
    ) -> None:
        resp = client.post(
            "/api/nvd/search",
            json={"cve_id": "CVE-2021-44228"},
            headers=auth_headers,
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert len(data["results"]) == 1
        assert data["results"][0]["id"] == "CVE-2021-44228"
        assert data["results"][0]["score"] is not None

    def test_search_by_keyword(
        self, client: FlaskClient, auth_headers: dict[str, str],
    ) -> None:
        resp = client.post(
            "/api/nvd/search",
            json={"keyword": "log4j", "results_per_page": 3},
            headers=auth_headers,
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert len(data["results"]) > 0


# ── MITRE ATT&CK ───────────────────────────────────────────────────

class TestMitreIntegration:
    """Integration tests for MITRE ATT&CK (no key required)."""

    def test_connection(
        self, client: FlaskClient, auth_headers: dict[str, str],
    ) -> None:
        resp = client.get("/api/mitre", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["status"] == "connected"
        assert data["technique_count"] > 100

    def test_search_by_id(
        self, client: FlaskClient, auth_headers: dict[str, str],
    ) -> None:
        resp = client.post(
            "/api/mitre/search",
            json={"technique_id": "T1110"},
            headers=auth_headers,
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert len(data["results"]) == 1
        assert data["results"][0]["id"] == "T1110"
        assert data["results"][0]["name"] == "Brute Force"

    def test_search_by_keyword(
        self, client: FlaskClient, auth_headers: dict[str, str],
    ) -> None:
        resp = client.post(
            "/api/mitre/search",
            json={"search": "phishing"},
            headers=auth_headers,
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert len(data["results"]) > 0


# ── VirusTotal ──────────────────────────────────────────────────────

@pytest.mark.skipif(
    not _VIRUSTOTAL_KEY, reason="VIRUSTOTAL_API_KEY not set",
)
class TestVirusTotalIntegration:
    """Integration tests for the VirusTotal API."""

    def test_connection(
        self, client: FlaskClient, auth_headers: dict[str, str],
    ) -> None:
        resp = client.get("/api/virustotal", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["status"] == "connected"

    def test_scan_domain(
        self, client: FlaskClient, auth_headers: dict[str, str],
    ) -> None:
        resp = client.post(
            "/api/virustotal/scan",
            json={"type": "domain", "value": "google.com"},
            headers=auth_headers,
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["result"]["type"] == "domain"
        assert data["result"]["value"] == "google.com"
        assert data["result"]["last_analysis_stats"] is not None

    def test_scan_ip(
        self, client: FlaskClient, auth_headers: dict[str, str],
    ) -> None:
        resp = client.post(
            "/api/virustotal/scan",
            json={"type": "ip", "value": "8.8.8.8"},
            headers=auth_headers,
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["result"]["type"] == "ip"


# ── AbuseIPDB ───────────────────────────────────────────────────────

@pytest.mark.skipif(
    not _ABUSEIPDB_KEY, reason="ABUSEIPDB_API_KEY not set",
)
class TestAbuseIPDBIntegration:
    """Integration tests for the AbuseIPDB API."""

    def test_connection(
        self, client: FlaskClient, auth_headers: dict[str, str],
    ) -> None:
        resp = client.get("/api/abuseipdb", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["status"] == "connected"

    def test_check_ip(
        self, client: FlaskClient, auth_headers: dict[str, str],
    ) -> None:
        resp = client.post(
            "/api/abuseipdb/check",
            json={"ip": "8.8.8.8"},
            headers=auth_headers,
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["result"]["ip"] == "8.8.8.8"
        assert data["result"]["abuse_confidence_score"] is not None
        assert data["result"]["country_code"] == "US"


# ── OTX ─────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _OTX_KEY, reason="OTX_API_KEY not set")
class TestOtxIntegration:
    """Integration tests for the AlienVault OTX API."""

    def test_connection(
        self, client: FlaskClient, auth_headers: dict[str, str],
    ) -> None:
        resp = client.get("/api/otx", headers=auth_headers)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["status"] == "connected"

    def test_search_ipv4(
        self, client: FlaskClient, auth_headers: dict[str, str],
    ) -> None:
        resp = client.post(
            "/api/otx/search",
            json={"type": "IPv4", "value": "8.8.8.8"},
            headers=auth_headers,
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["result"]["type"] == "IPv4"
        assert data["result"]["value"] == "8.8.8.8"
        assert data["result"]["pulse_count"] is not None

    def test_search_domain(
        self, client: FlaskClient, auth_headers: dict[str, str],
    ) -> None:
        resp = client.post(
            "/api/otx/search",
            json={"type": "domain", "value": "google.com"},
            headers=auth_headers,
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["result"]["type"] == "domain"
