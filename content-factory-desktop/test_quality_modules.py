import unittest

from dzen_rules import check_dzen_rules
from fact_checker import check_article
from seo import check_seo


class QualityModulesTest(unittest.TestCase):
    def test_dzen_rules_returns_report(self):
        report = check_dzen_rules(
            "Как проверить факты",
            "Проверка фактов помогает снизить риск ошибок.",
        )
        self.assertIsInstance(report, dict)

    def test_dzen_rules_handles_empty_text(self):
        report = check_dzen_rules("Заголовок", "")
        self.assertIsInstance(report, dict)

    def test_fact_checker_returns_report(self):
        report = check_article(
            "Проверка фактов помогает снизить риск ошибок."
        )
        self.assertIsInstance(report, dict)

    def test_fact_checker_handles_empty_text(self):
        report = check_article("")
        self.assertIsInstance(report, dict)

    def test_seo_returns_report(self):
        report = check_seo(
            title="Как проверить факты",
            text="Проверка фактов помогает снизить риск ошибок.",
            primary_query="проверка фактов",
            secondary_queries=[],
            related_topics=[],
        )
        self.assertIsInstance(report, dict)

    def test_seo_handles_short_text(self):
        report = check_seo(
            title="Тест",
            text="Короткий текст.",
            primary_query="запрос",
            secondary_queries=[],
            related_topics=[],
        )
        self.assertIsInstance(report, dict)


if __name__ == "__main__":
    unittest.main()
