import unittest

from app.ui.theme import Theme


class ThemeApiTests(unittest.TestCase):
    def test_theme_supports_terminal_style_helpers(self):
        theme = Theme("light")

        self.assertIn("Cost & Profit Calculator", theme.header("Cost & Profit Calculator"))
        self.assertIn("OK", theme.status("OK", True))
        self.assertIn("System Overview", theme.box("System Overview", ["A", "B"]))
        self.assertIn("db", theme.ICONS["db"])


if __name__ == "__main__":
    unittest.main()
