# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
NVD (National Vulnerability Database) Client

Fetches CVE data from the NVD 2.0 API using only Python stdlib.
Implements rate limiting (5 req / 30s for public API) and local file caching.
"""

import json
import logging
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("komposos.nvd")

NVD_API_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"

CACHE_DIR = Path(__file__).parent.parent / "data" / "cyber" / "nvd_cache"
CACHE_TTL_SECONDS = 3600  # 1 hour


class NVDClient:
    """Fetches CVE data from the NVD 2.0 API with rate limiting and caching."""

    def __init__(self, cache_dir: Optional[Path] = None, api_key: Optional[str] = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key
        self._last_requests: list[float] = []

    def _rate_limit(self) -> None:
        """Enforce NVD public rate limit: max 5 requests per 30 seconds."""
        now = time.time()
        window = 30.0
        max_requests = 50 if self.api_key else 5

        # Clean old entries
        self._last_requests = [t for t in self._last_requests if now - t < window]

        if len(self._last_requests) >= max_requests:
            wait = window - (now - self._last_requests[0])
            if wait > 0:
                logger.debug(f"NVD rate limit: waiting {wait:.1f}s")
                time.sleep(wait)

        self._last_requests.append(time.time())

    def _cache_path(self, key: str) -> Path:
        """Get cache file path for a key."""
        safe_key = key.replace("/", "_").replace(":", "_").replace("?", "_")
        return self.cache_dir / f"{safe_key}.json"

    def _read_cache(self, key: str) -> Optional[Dict]:
        """Read from cache if fresh."""
        path = self._cache_path(key)
        if not path.exists():
            return None
        age = time.time() - path.stat().st_mtime
        if age > CACHE_TTL_SECONDS:
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _write_cache(self, key: str, data: Dict) -> None:
        """Write data to cache."""
        path = self._cache_path(key)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError as e:
            logger.debug(f"Failed to write NVD cache: {e}")

    def _fetch(self, url: str) -> Optional[Dict]:
        """Make a rate-limited request to the NVD API."""
        self._rate_limit()
        headers = {
            "Accept": "application/json",
            "User-Agent": "KOMPOSOS-III/1.0",
        }
        if self.api_key:
            headers["apiKey"] = self.api_key

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, OSError,
                TimeoutError, json.JSONDecodeError) as e:
            logger.warning(f"NVD API request failed: {e}")
            return None

    def get_cve(self, cve_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single CVE by ID.

        Returns parsed CVE data dict or None on failure.
        """
        cache_key = f"cve_{cve_id}"
        cached = self._read_cache(cache_key)
        if cached:
            return cached

        url = f"{NVD_API_BASE}?cveId={cve_id}"
        data = self._fetch(url)
        if not data:
            return None

        vulnerabilities = data.get("vulnerabilities", [])
        if not vulnerabilities:
            return None

        result = self._parse_cve(vulnerabilities[0])
        if result:
            self._write_cache(cache_key, result)
        return result

    def search_by_keyword(self, keyword: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search CVEs by keyword.

        Returns list of parsed CVE data dicts.
        """
        cache_key = f"search_{keyword}_{max_results}"
        cached = self._read_cache(cache_key)
        if cached:
            return cached.get("results", [])

        encoded_kw = urllib.request.quote(keyword)
        url = f"{NVD_API_BASE}?keywordSearch={encoded_kw}&resultsPerPage={max_results}"
        data = self._fetch(url)
        if not data:
            return []

        results = []
        for vuln in data.get("vulnerabilities", []):
            parsed = self._parse_cve(vuln)
            if parsed:
                results.append(parsed)

        self._write_cache(cache_key, {"results": results})
        return results

    @staticmethod
    def _parse_cve(vuln: Dict) -> Optional[Dict[str, Any]]:
        """Parse a single CVE vulnerability object from the NVD response."""
        cve = vuln.get("cve", {})
        cve_id = cve.get("id", "")
        if not cve_id:
            return None

        # Description
        descriptions = cve.get("descriptions", [])
        description = ""
        for d in descriptions:
            if d.get("lang") == "en":
                description = d.get("value", "")
                break
        if not description and descriptions:
            description = descriptions[0].get("value", "")

        # CVSS score — try v3.1 first, then v3.0, then v2.0
        cvss_score = None
        severity = "unknown"
        metrics = cve.get("metrics", {})
        for version_key in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
            metric_list = metrics.get(version_key, [])
            if metric_list:
                cvss_data = metric_list[0].get("cvssData", {})
                cvss_score = cvss_data.get("baseScore")
                severity = cvss_data.get("baseSeverity", "unknown")
                break

        # Published date
        published = cve.get("published", "")

        # References
        references = []
        for ref in cve.get("references", []):
            url = ref.get("url", "")
            if url:
                references.append(url)

        return {
            "cve_id": cve_id,
            "description": description,
            "cvss_score": cvss_score,
            "severity": severity.lower() if severity else "unknown",
            "published": published,
            "references": references[:10],
        }
