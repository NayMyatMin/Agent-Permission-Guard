"""Tests for the task analyzer module."""

import unittest

from src.models import PermissionCategory, PermissionScope, TaskCapability
from src.task_analyzer import TaskAnalyzer


class TestTaskAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = TaskAnalyzer()

    def test_research_task(self):
        result = self.analyzer.analyze(
            "Help me search online for information on competitors and summarize it."
        )
        self.assertIn(TaskCapability.INFORMATION_GATHERING, result.intents)
        self.assertIn(TaskCapability.CONTENT_CREATION, result.intents)
        self.assertIn(PermissionCategory.WEB_ACCESS, result.required_categories)
        self.assertIn(PermissionCategory.FILE_WRITE, result.required_categories)

    def test_code_execution_task(self):
        result = self.analyzer.analyze("Run the test suite and fix any failing tests.")
        self.assertIn(TaskCapability.CODE_EXECUTION, result.intents)
        self.assertIn(PermissionCategory.SHELL_EXECUTION, result.required_categories)

    def test_communication_task(self):
        result = self.analyzer.analyze("Send an email to the team with the status update.")
        self.assertIn(TaskCapability.COMMUNICATION, result.intents)
        self.assertIn(PermissionCategory.SKILL_CONNECTIONS, result.required_categories)

    def test_file_management_task(self):
        result = self.analyzer.analyze("Download the dataset and save it locally.")
        self.assertIn(TaskCapability.FILE_MANAGEMENT, result.intents)
        self.assertIn(PermissionCategory.FILE_READ, result.required_categories)
        self.assertIn(PermissionCategory.FILE_WRITE, result.required_categories)

    def test_system_modification_task(self):
        result = self.analyzer.analyze("Configure the CI/CD pipeline and update settings.")
        self.assertIn(TaskCapability.SYSTEM_MODIFICATION, result.intents)
        self.assertIn(PermissionCategory.SYSTEM_MODIFICATION, result.required_categories)

    def test_fallback_for_unrecognized_task(self):
        result = self.analyzer.analyze("Do something vague and unspecific.")
        self.assertIn(TaskCapability.INFORMATION_GATHERING, result.intents)
        self.assertIn(PermissionCategory.FILE_READ, result.required_categories)

    def test_fallback_has_zero_confidence(self):
        result = self.analyzer.analyze("Do something vague and unspecific.")
        self.assertEqual(result.confidence, 0.0)
        self.assertTrue(result.is_ambiguous)

    def test_matched_task_has_full_confidence(self):
        result = self.analyzer.analyze("Search online for information.")
        self.assertEqual(result.confidence, 1.0)
        self.assertFalse(result.is_ambiguous)

    def test_multiple_intents(self):
        result = self.analyzer.analyze(
            "Search for data online, download it, and send the report via email."
        )
        self.assertIn(TaskCapability.INFORMATION_GATHERING, result.intents)
        self.assertIn(TaskCapability.FILE_MANAGEMENT, result.intents)
        self.assertIn(TaskCapability.COMMUNICATION, result.intents)

    def test_intent_labels(self):
        result = self.analyzer.analyze("Search for competitor information.")
        self.assertIn("Information Gathering", result.intent_labels)

    def test_required_permissions_have_limited_scope(self):
        result = self.analyzer.analyze("Search online for information.")
        for perm in result.required_permissions:
            self.assertEqual(perm.scope, PermissionScope.LIMITED)

    def test_duplicate_categories_resolved(self):
        """When multiple rules match the same category, it should appear only once."""
        result = self.analyzer.analyze(
            "Search for data online, download it, and save it."
        )
        cats = [p.category for p in result.required_permissions]
        # No duplicate categories
        self.assertEqual(len(cats), len(set(cats)))


if __name__ == "__main__":
    unittest.main()
