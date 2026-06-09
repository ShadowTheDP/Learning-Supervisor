from __future__ import annotations

import unittest

from jinja2 import Environment, FileSystemLoader

from app.config import PROJECT_ROOT


class TemplateCompilationTests(unittest.TestCase):
    def test_key_templates_compile(self) -> None:
        environment = Environment(
            loader=FileSystemLoader(str(PROJECT_ROOT / "app" / "templates")),
        )

        for template_name in [
            "dashboard.html",
            "resource_form.html",
            "resource_detail.html",
            "task_detail.html",
            "review_detail.html",
            "settings.html",
        ]:
            with self.subTest(template=template_name):
                environment.get_template(template_name)


if __name__ == "__main__":
    unittest.main()
