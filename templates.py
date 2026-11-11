from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class Testcase:
    id: str
    title: str
    category: str          # functional, boundary, exception, integration
    precondition: str
    steps: list[str]
    expected_result: str
    priority: str          # high, medium, low
    source_section: str    # bagian dokumen POC yang jadi referensi
    tags: list[str] = field(default_factory=list)
    kind: str = "generic"  # "rule" (hasil ekstraksi aturan) atau "generic" (template)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "precondition": self.precondition,
            "steps": self.steps,
            "expected_result": self.expected_result,
            "priority": self.priority,
            "source_section": self.source_section,
            "tags": self.tags,
            "kind": self.kind,
        }

    def to_markdown(self) -> str:
        markdown = f"# {self.title}\n\n"
        markdown += f"## Precondition\n{self.precondition}\n\n"
        markdown += f"## Steps\n"
        for step in self.steps:
            markdown += f"- {step}\n"
        markdown += f"\n## Expected Result\n{self.expected_result}\n\n"
        markdown += f"## Priority\n{self.priority}\n\n"
        markdown += f"## Source Section\n{self.source_section}\n\n"
        markdown += f"## Tags\n"
        for tag in self.tags:
            markdown += f"- {tag}\n"
        return markdown


def _format_table(testcases):
    table = "| ID | Title | Category | Priority |\n"
    table += "|----|-------|----------|----------|\n"
    for tc in testcases:
        table += f"| {tc.id} | {tc.title} | {tc.category} | {tc.priority} |\n"
    return table


def generate_boundary_testcases(section: object) -> list[Testcase]:
    testcases = []
    # Logic to generate boundary testcases
    return testcases


def generate_functional_testcases(section: object) -> list[Testcase]:
    testcases = []
    # Logic to generate functional testcases
    return testcases


def generate_exception_testcases(section: object) -> list[Testcase]:
    testcases = []
    # Logic to generate exception testcases
    return testcases


def generate_integration_testcases(section: object) -> list[Testcase]:
    testcases = []
    # Logic to generate integration testcases
    return testcases


def _determine_category(text: str) -> str:
    """Determine section category from content (same logic as generator.py)."""
    CATEGORY_KEYWORDS = {
        "functional": ["should", "must", "will", "perform", "execute",
                       "harus", "akan", "mampu", "melakukan"],
        "boundary": ["max", "min", "limit", "range", "maximum", "minimum",
                     "batas", "maksimal", "minimal", "ambang"],
        "exception": ["error", "fail", "invalid", "reject", "timeout",
                      "gagal", "tidak valid", "ditolak", "kesalahan"],
        "integration": ["api", "endpoint", "service", "integrate", "sync",
                        "koneks", "integrasi", "sinkron", "interface"],
    }
    text_lower = text.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return cat
    return "functional"

def generate_testcases_from_section(section: object) -> list[Testcase]:
    cat = _determine_category(getattr(section, "content", ""))
    if cat == "boundary":
        return generate_boundary_testcases(section)
    elif cat == "functional":
        return generate_functional_testcases(section)
    elif cat == "exception":
        return generate_exception_testcases(section)
    elif cat == "integration":
        return generate_integration_testcases(section)
    else:
        return []


def generate_testcases(doc):
    testcases = []
    for section in doc.sections:  # FIX: iterate over doc.sections, not doc directly
        testcases.extend(generate_testcases_from_section(section))
    return testcases
