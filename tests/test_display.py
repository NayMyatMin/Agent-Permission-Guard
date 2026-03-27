"""Tests for the display module."""

import unittest

from src.display import ConsultantDisplay


class TestConsultantDisplay(unittest.TestCase):

    def setUp(self):
        # Force no color for predictable output
        self.display = ConsultantDisplay(use_color=False)

    def test_visible_len_plain_text(self):
        self.assertEqual(self.display._visible_len("hello"), 5)

    def test_visible_len_with_ansi(self):
        text = "\033[91mhello\033[0m"
        self.assertEqual(self.display._visible_len(text), 5)

    def test_box_line_has_right_border(self):
        line = self.display._box_line("test", 78)
        self.assertTrue(line.endswith("│"))
        self.assertTrue(line.startswith("│"))

    def test_box_line_consistent_width(self):
        """All box lines should have the same visible width."""
        width = 78
        top = self.display._box_top(width)
        sep = self.display._box_separator(width)
        bottom = self.display._box_bottom(width)
        line = self.display._box_line("short content", width)

        expected_width = width + 2  # border chars on each side
        self.assertEqual(len(top), expected_width)
        self.assertEqual(len(sep), expected_width)
        self.assertEqual(len(bottom), expected_width)
        self.assertEqual(self.display._visible_len(line), expected_width)

    def test_box_line_long_content_still_closes(self):
        """Very long content should still get a right border."""
        line = self.display._box_line("x" * 200, 78)
        self.assertTrue(line.endswith("│"))


if __name__ == "__main__":
    unittest.main()
