"""Tests for Streamlit access control module.

Tests the pure logic functions without requiring a running Streamlit app.
Session state is mocked where needed.
"""

import os
import unittest
from unittest.mock import patch, MagicMock


class TestVoucherParsing(unittest.TestCase):
    """Test parsing of KOMPOSOS_VOUCHER_CODES env var."""

    def _load(self, env_val):
        with patch.dict(os.environ, {"KOMPOSOS_VOUCHER_CODES": env_val}):
            from streamlit_app.access_control import _load_voucher_codes
            return _load_voucher_codes()

    def test_empty_string(self):
        result = self._load("")
        self.assertEqual(result, {})

    def test_single_voucher_with_limit(self):
        result = self._load("ATEIOS2026:20")
        self.assertEqual(result, {"ATEIOS2026": 20})

    def test_multiple_vouchers(self):
        result = self._load("CODE1:10,CODE2:5,CODE3:30")
        self.assertEqual(result, {"CODE1": 10, "CODE2": 5, "CODE3": 30})

    def test_voucher_without_limit_defaults_to_20(self):
        result = self._load("TESTCODE")
        self.assertEqual(result, {"TESTCODE": 20})

    def test_mixed_with_and_without_limits(self):
        result = self._load("CODE1:10,CODE2")
        self.assertEqual(result, {"CODE1": 10, "CODE2": 20})

    def test_whitespace_handling(self):
        result = self._load(" CODE1 : 10 , CODE2 : 5 ")
        self.assertEqual(result, {"CODE1": 10, "CODE2": 5})

    def test_invalid_limit_defaults_to_20(self):
        result = self._load("CODE1:abc")
        self.assertEqual(result, {"CODE1": 20})


class TestAdminPassword(unittest.TestCase):
    """Test admin password loading."""

    def test_default_password(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove the key if it exists
            os.environ.pop("KOMPOSOS_ADMIN_PASSWORD", None)
            from streamlit_app.access_control import _load_admin_password
            result = _load_admin_password()
            self.assertEqual(result, "komposos-admin")

    def test_custom_password(self):
        with patch.dict(os.environ, {"KOMPOSOS_ADMIN_PASSWORD": "my-secret"}):
            from streamlit_app.access_control import _load_admin_password
            result = _load_admin_password()
            self.assertEqual(result, "my-secret")


class TestDemoLimit(unittest.TestCase):
    """Test demo limit loading."""

    def test_default_limit(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("KOMPOSOS_DEMO_LIMIT", None)
            from streamlit_app.access_control import _load_demo_limit
            result = _load_demo_limit()
            self.assertEqual(result, 3)

    def test_custom_limit(self):
        with patch.dict(os.environ, {"KOMPOSOS_DEMO_LIMIT": "10"}):
            from streamlit_app.access_control import _load_demo_limit
            result = _load_demo_limit()
            self.assertEqual(result, 10)

    def test_invalid_limit_returns_default(self):
        with patch.dict(os.environ, {"KOMPOSOS_DEMO_LIMIT": "abc"}):
            from streamlit_app.access_control import _load_demo_limit
            result = _load_demo_limit()
            self.assertEqual(result, 3)


if __name__ == "__main__":
    unittest.main()
