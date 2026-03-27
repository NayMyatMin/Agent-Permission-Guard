"""Tests for permission config loading and validation."""

import json
import os
import tempfile
import unittest

from src.permission_config import PermissionConfig


class TestPermissionConfigValidation(unittest.TestCase):

    def test_missing_file_gives_clear_error(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            PermissionConfig.from_json_file("/nonexistent/path/config.json")
        self.assertIn("not found", str(ctx.exception))

    def test_invalid_json_gives_clear_error(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{not valid json")
            f.flush()
            try:
                with self.assertRaises(ValueError) as ctx:
                    PermissionConfig.from_json_file(f.name)
                self.assertIn("Invalid JSON", str(ctx.exception))
            finally:
                os.unlink(f.name)

    def test_missing_category_field(self):
        data = {"permissions": [{"scope": "limited"}]}
        with self.assertRaises(ValueError) as ctx:
            PermissionConfig.from_dict(data)
        self.assertIn("missing required field 'category'", str(ctx.exception))

    def test_missing_scope_field(self):
        data = {"permissions": [{"category": "web_access"}]}
        with self.assertRaises(ValueError) as ctx:
            PermissionConfig.from_dict(data)
        self.assertIn("missing required field 'scope'", str(ctx.exception))

    def test_invalid_category_value(self):
        data = {"permissions": [{"category": "laser_cannon", "scope": "limited"}]}
        with self.assertRaises(ValueError) as ctx:
            PermissionConfig.from_dict(data)
        self.assertIn("unknown category", str(ctx.exception))

    def test_invalid_scope_value(self):
        data = {"permissions": [{"category": "web_access", "scope": "maximum"}]}
        with self.assertRaises(ValueError) as ctx:
            PermissionConfig.from_dict(data)
        self.assertIn("unknown scope", str(ctx.exception))

    def test_permissions_not_a_list(self):
        data = {"permissions": "not a list"}
        with self.assertRaises(ValueError) as ctx:
            PermissionConfig.from_dict(data)
        self.assertIn("must be a list", str(ctx.exception))

    def test_valid_config_loads(self):
        data = {
            "profile_name": "test",
            "permissions": [
                {"category": "web_access", "scope": "limited", "details": "test"},
            ],
        }
        config = PermissionConfig.from_dict(data)
        self.assertEqual(config.profile_name, "test")
        self.assertEqual(len(config.permissions), 1)


if __name__ == "__main__":
    unittest.main()
