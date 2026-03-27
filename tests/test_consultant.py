"""Tests for the consultant module."""

import unittest
from pathlib import Path

from src.consultant import Consultant
from src.models import PermissionCategory, PermissionScope, RiskLevel, TaskCapability
from src.permission_config import PermissionConfig


CONFIG_DIR = Path(__file__).parent.parent / "configs"


class TestConsultant(unittest.TestCase):

    def setUp(self):
        self.consultant = Consultant()

    def _load_overpermissioned(self) -> PermissionConfig:
        return PermissionConfig.from_json_file(CONFIG_DIR / "overpermissioned.json")

    def _load_minimal(self) -> PermissionConfig:
        return PermissionConfig.from_json_file(CONFIG_DIR / "minimal_research.json")

    def test_research_task_with_overpermissioned_config(self):
        """The example from the project spec."""
        config = self._load_overpermissioned()
        report = self.consultant.analyze(
            "Help me search online for information on competitors and summarize it.",
            config,
        )

        # Should detect information gathering and content creation
        self.assertIn(TaskCapability.INFORMATION_GATHERING, report.task_intents)
        self.assertIn(TaskCapability.CONTENT_CREATION, report.task_intents)

        # Should have excess permissions
        self.assertGreater(len(report.excess_permissions), 0)

        # Shell execution should be flagged as excess
        excess_categories = {p.category for p in report.excess_permissions}
        self.assertIn(PermissionCategory.SHELL_EXECUTION, excess_categories)

        # Should detect risk paths
        self.assertGreater(len(report.risk_paths), 0)

        # Should have suggestions
        self.assertGreater(len(report.suggestions), 0)

        # Deviation index should be high
        self.assertGreater(report.deviation_index, 0.3)

        # High confidence for keyword-matched task
        self.assertEqual(report.confidence, 1.0)

    def test_research_task_with_minimal_config(self):
        """Minimal config should show no excess permissions for research."""
        config = self._load_minimal()
        report = self.consultant.analyze(
            "Help me search online for information on competitors and summarize it.",
            config,
        )

        # No risk paths should be detected (minimal config is well-aligned)
        self.assertEqual(len(report.risk_paths), 0)

        # Deviation index should be low
        self.assertLessEqual(report.deviation_index, 0.3)

    def test_suggestions_disable_before_restrict(self):
        """Disable suggestions should come before restrict suggestions."""
        config = self._load_overpermissioned()
        report = self.consultant.analyze("Search for information online.", config)

        saw_restrict = False
        for sug in report.suggestions:
            if sug.recommended_scope == PermissionScope.LIMITED:
                saw_restrict = True
            if sug.recommended_scope == PermissionScope.DISABLED and saw_restrict:
                self.fail("DISABLE suggestion appeared after RESTRICT suggestion")

    def test_report_has_summary_note(self):
        config = self._load_overpermissioned()
        report = self.consultant.analyze("Search for competitor data online.", config)
        self.assertTrue(len(report.summary_note) > 0)

    def test_all_risk_paths_involve_excess(self):
        """Every risk path should involve at least one excess permission."""
        config = self._load_overpermissioned()
        report = self.consultant.analyze("Search online for information.", config)

        required_categories = {p.category for p in report.required_permissions}
        for rp in report.risk_paths:
            excess_in_path = [c for c in rp.involved_permissions if c not in required_categories]
            self.assertGreater(
                len(excess_in_path), 0,
                f"Risk path '{rp.name}' has no excess permissions",
            )

    def test_code_execution_task(self):
        config = self._load_overpermissioned()
        report = self.consultant.analyze("Run the test suite.", config)
        self.assertIn(TaskCapability.CODE_EXECUTION, report.task_intents)
        # Shell should be required, not flagged as excess
        required_cats = {p.category for p in report.required_permissions}
        self.assertIn(PermissionCategory.SHELL_EXECUTION, required_cats)

    def test_ambiguous_task_has_low_confidence(self):
        """An unrecognized task should have low confidence and dampened deviation."""
        config = self._load_overpermissioned()
        report = self.consultant.analyze("Help me with something.", config)
        self.assertLess(report.confidence, 0.5)

    def test_ambiguous_task_dampens_deviation(self):
        """Ambiguous tasks should have lower deviation than recognized tasks."""
        config = self._load_overpermissioned()
        ambiguous = self.consultant.analyze("Help me with something.", config)
        specific = self.consultant.analyze("Search online for information.", config)
        # Ambiguous gets dampened, so it should be lower (or at most equal)
        self.assertLessEqual(ambiguous.deviation_index, specific.deviation_index)

    def test_excess_permissions_preserve_original_details(self):
        """Excess permissions should keep original details, not overwrite them."""
        config = self._load_overpermissioned()
        report = self.consultant.analyze("Search online for information.", config)

        for perm in report.excess_permissions:
            # details should be from the original config, not implementation logic
            self.assertNotIn("Scope is UNRESTRICTED but task only needs", perm.details)
            # excess_reason should carry the explanation
            self.assertTrue(len(perm.excess_reason) > 0)

    def test_no_duplicate_risk_paths(self):
        """No two risk paths should have the same involved_permissions set."""
        config = self._load_overpermissioned()
        report = self.consultant.analyze("Search online for information.", config)

        seen = set()
        for rp in report.risk_paths:
            key = frozenset(rp.involved_permissions)
            self.assertNotIn(key, seen, f"Duplicate risk path permissions: {rp.name}")
            seen.add(key)


if __name__ == "__main__":
    unittest.main()
