"""Tests for the risk engine module."""

import unittest

from src.models import Permission, PermissionCategory, PermissionScope, RiskLevel
from src.permission_config import PermissionConfig
from src.risk_engine import RiskEngine


def _make_config(categories_and_scopes: list[tuple[PermissionCategory, PermissionScope]]) -> PermissionConfig:
    """Helper to create a PermissionConfig from category-scope pairs."""
    perms = [Permission(cat, scope) for cat, scope in categories_and_scopes]
    return PermissionConfig(perms)


class TestRiskEngine(unittest.TestCase):

    def setUp(self):
        self.engine = RiskEngine()

    def test_data_exfiltration_detected(self):
        config = _make_config([
            (PermissionCategory.FILE_READ, PermissionScope.UNRESTRICTED),
            (PermissionCategory.NETWORK_OUTBOUND, PermissionScope.UNRESTRICTED),
        ])
        risks = self.engine.evaluate(config)
        risk_names = [r.name for r in risks]
        self.assertIn("Data Exfiltration", risk_names)

    def test_data_exfiltration_via_skills(self):
        config = _make_config([
            (PermissionCategory.FILE_READ, PermissionScope.UNRESTRICTED),
            (PermissionCategory.SKILL_CONNECTIONS, PermissionScope.UNRESTRICTED),
        ])
        risks = self.engine.evaluate(config)
        risk_names = [r.name for r in risks]
        self.assertIn("Data Exfiltration via Skills", risk_names)

    def test_remote_code_execution_detected(self):
        config = _make_config([
            (PermissionCategory.WEB_ACCESS, PermissionScope.UNRESTRICTED),
            (PermissionCategory.SHELL_EXECUTION, PermissionScope.UNRESTRICTED),
        ])
        risks = self.engine.evaluate(config)
        risk_names = [r.name for r in risks]
        self.assertIn("Remote Code Execution", risk_names)

    def test_supply_chain_requires_three_permissions(self):
        config = _make_config([
            (PermissionCategory.WEB_ACCESS, PermissionScope.UNRESTRICTED),
            (PermissionCategory.FILE_WRITE, PermissionScope.UNRESTRICTED),
            (PermissionCategory.SHELL_EXECUTION, PermissionScope.UNRESTRICTED),
        ])
        risks = self.engine.evaluate(config)
        risk_names = [r.name for r in risks]
        self.assertIn("Supply Chain Attack", risk_names)

    def test_no_risk_when_disabled(self):
        config = _make_config([
            (PermissionCategory.FILE_READ, PermissionScope.UNRESTRICTED),
            (PermissionCategory.NETWORK_OUTBOUND, PermissionScope.DISABLED),
        ])
        risks = self.engine.evaluate(config)
        risk_names = [r.name for r in risks]
        self.assertNotIn("Data Exfiltration", risk_names)

    def test_excess_filter(self):
        """Risk paths not involving excess permissions should be filtered out."""
        config = _make_config([
            (PermissionCategory.WEB_ACCESS, PermissionScope.LIMITED),
            (PermissionCategory.NETWORK_OUTBOUND, PermissionScope.LIMITED),
            (PermissionCategory.SHELL_EXECUTION, PermissionScope.UNRESTRICTED),
        ])
        # Task requires web and network, shell is excess
        required = {PermissionCategory.WEB_ACCESS, PermissionCategory.NETWORK_OUTBOUND}
        risks = self.engine.evaluate(config, required)

        # Remote Code Execution (web + shell) should appear because shell is excess
        risk_names = [r.name for r in risks]
        self.assertIn("Remote Code Execution", risk_names)

    def test_no_excess_means_no_risks(self):
        """If all permissions are required, no risk paths are flagged."""
        config = _make_config([
            (PermissionCategory.WEB_ACCESS, PermissionScope.LIMITED),
            (PermissionCategory.NETWORK_OUTBOUND, PermissionScope.LIMITED),
        ])
        required = {PermissionCategory.WEB_ACCESS, PermissionCategory.NETWORK_OUTBOUND}
        risks = self.engine.evaluate(config, required)
        self.assertEqual(len(risks), 0)

    def test_risks_sorted_by_severity(self):
        config = _make_config([
            (PermissionCategory.WEB_ACCESS, PermissionScope.UNRESTRICTED),
            (PermissionCategory.FILE_READ, PermissionScope.UNRESTRICTED),
            (PermissionCategory.FILE_WRITE, PermissionScope.UNRESTRICTED),
            (PermissionCategory.SHELL_EXECUTION, PermissionScope.UNRESTRICTED),
            (PermissionCategory.NETWORK_OUTBOUND, PermissionScope.UNRESTRICTED),
        ])
        risks = self.engine.evaluate(config)
        for i in range(len(risks) - 1):
            self.assertGreaterEqual(risks[i].level.weight, risks[i + 1].level.weight)

    def test_deviation_index_zero_when_aligned(self):
        config = _make_config([
            (PermissionCategory.WEB_ACCESS, PermissionScope.LIMITED),
        ])
        required = {PermissionCategory.WEB_ACCESS}
        index = self.engine.compute_deviation_index(config, required)
        self.assertEqual(index, 0.0)

    def test_deviation_index_high_when_over_authorized(self):
        config = _make_config([
            (PermissionCategory.WEB_ACCESS, PermissionScope.UNRESTRICTED),
            (PermissionCategory.FILE_READ, PermissionScope.UNRESTRICTED),
            (PermissionCategory.FILE_WRITE, PermissionScope.UNRESTRICTED),
            (PermissionCategory.SHELL_EXECUTION, PermissionScope.UNRESTRICTED),
            (PermissionCategory.SKILL_CONNECTIONS, PermissionScope.UNRESTRICTED),
            (PermissionCategory.NETWORK_OUTBOUND, PermissionScope.UNRESTRICTED),
            (PermissionCategory.SYSTEM_MODIFICATION, PermissionScope.UNRESTRICTED),
        ])
        required = {PermissionCategory.WEB_ACCESS}
        index = self.engine.compute_deviation_index(config, required)
        self.assertGreater(index, 0.7)

    def test_deviation_index_empty_config(self):
        config = _make_config([])
        index = self.engine.compute_deviation_index(config, set())
        self.assertEqual(index, 0.0)


if __name__ == "__main__":
    unittest.main()
