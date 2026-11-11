from dataclasses import dataclass, field
from typing import Optional
import json
import re

from parser import _determine_category


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


def _determine_priority(text: str) -> str:
    """Determine priority from content."""
    priority_keywords = {
        "high": ["critical", "must", "harus", "fatal", "security", "auth"],
        "medium": ["should", "wajib", "normal", "standard"],
        "low": ["nice", "optional", "prefer", "saran", "rekomendasi"],
    }
    text_lower = text.lower()
    for prio, keywords in priority_keywords.items():
        if any(kw in text_lower for kw in keywords):
            return prio
    return "medium"


def _extract_keywords(section: object) -> list[str]:
    """Ekstrak kata kunci dari section using regex pattern."""
    content = getattr(section, "content", "")
    # Bahasa Indonesia stopwords
    all_stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did",
        "will", "shall", "should", "would", "could",
        "dan", "di", "ke", "dari", "untuk", "yang", "dengan",
        "ini", "itu", "saya", "kami", "anda", "mereka",
        "dengan", "oleh", "tidak", "bisa", "harus", "saat",
        "jika", "karena", "sampai", "hingga", "maka",
        "akan", "bisa", "harus", "perlu", "dapat",
        "seperti", "sebagaimana", "sehingga", "sesuai",
    }
    words = re.findall(r"[a-zA-Z\u00C0-\u017F]{3,}", content.lower())
    freq = {}
    for w in words:
        if w not in all_stopwords:
            freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: -x[1])
    return [w for w, _ in sorted_words[:10]]


def _generate_steps(section: object, keywords: list[str]) -> list[str]:
    """Generate langkah test case berdasarkan konten section dan keyword."""
    cat = _determine_category(getattr(section, "content", ""))
    base_kw = keywords[0] if keywords else "fitur"
    heading = getattr(section, "heading", "")

    step_templates = {
        "functional": [
            f"Siapkan lingkungan yang sesuai dengan syarat: {heading}",
            f"Akses modul/layanan terkita '{base_kw}'",
            f"Jalankan operasi: {heading}",
            f"Verifikasi output sesuai dengan spesifikasi POC",
        ],
        "boundary": [
            f"Siapkan data dengan nilai di batas minimum untuk '{base_kw}'",
            f"Jalankan proses dengan input pada batas bawah",
            f"Jalankan proses dengan input pada batas atas",
            f"Verifikasi sistem tetap stabil dan tidak crash",
        ],
        "exception": [
            f"Siapkan kondisi normal untuk '{base_kw}'",
            f"Induksi kondisi error: input tidak valid / timeout / dependensi down",
            f"Jalankan proses yang memicu exception",
            f"Verifikasi pesan error yang ditampilkan sesuai POC",
            f"Verifikasi log dan recovery mechanism berfungsi",
        ],
        "integration": [
            f"Pastikan service A dan service B sudah running",
            f"Kirim request ke endpoint: {heading}",
            f"Verifikasi response status code dan payload",
            f"Verifikasi data tersinkron di service tujuan",
        ],
    }
    return step_templates.get(cat, step_templates["functional"])


def _generate_expected(section: object) -> str:
    """Generate expected result based on section category."""
    cat = _determine_category(getattr(section, "content", ""))
    templates = {
        "functional": "Sistem menghasilkan output yang sesuai dengan spesifikasi POC, tanpa error.",
        "boundary": "Sistem menangani input di batas dengan benar: menolak/tidak crash dan menampilkan pesan yang sesuai.",
        "exception": "Sistem menangani exception secara graceful, menampilkan error message yang informatif, dan log tercatat.",
        "integration": "Data ter-transfer dengan benar antar service, status code 2xx, dan tidak ada data loss.",
    }
    return templates.get(cat, templates["functional"])


def generate_boundary_testcases(section: object) -> list[Testcase]:
    """Generate boundary test cases."""
    keywords = _extract_keywords(section)
    heading = section.heading if hasattr(section, 'heading') else ""
    return [
        Testcase(
            id=f"TC-BDR-{heading[:20].replace(' ', '-')}-1" if heading else "TC-BDR-1",
            title=f"Test {heading} - boundary scenario 1 ({keywords[0] if keywords else 'fitur'})",
            category="boundary",
            precondition="User telah login / sistem dalam kondisi ready",
            steps=_generate_steps(section, keywords),
            expected_result=_generate_expected(section),
            priority="medium",
            source_section=heading,
            tags=[keywords[0] if keywords else "fitur", "boundary", heading.lower().replace(" ", "-")],
        )
    ]


def generate_functional_testcases(section: object) -> list[Testcase]:
    """Generate functional test cases."""
    keywords = _extract_keywords(section)
    heading = section.heading if hasattr(section, 'heading') else ""
    return [
        Testcase(
            id=f"TC-FUNC-{heading[:20].replace(' ', '-')}-1" if heading else "TC-FUNC-1",
            title=f"Test {heading} - functional scenario 1 ({keywords[0] if keywords else 'fitur'})",
            category="functional",
            precondition="User telah login / sistem dalam kondisi ready",
            steps=_generate_steps(section, keywords),
            expected_result=_generate_expected(section),
            priority="medium",
            source_section=heading,
            tags=[keywords[0] if keywords else "fitur", "functional", heading.lower().replace(" ", "-")],
        )
    ]


def generate_exception_testcases(section: object) -> list[Testcase]:
    """Generate exception test cases."""
    keywords = _extract_keywords(section)
    heading = section.heading if hasattr(section, 'heading') else ""
    return [
        Testcase(
            id=f"TC-EXC-{heading[:20].replace(' ', '-')}-1" if heading else "TC-EXC-1",
            title=f"Test {heading} - exception scenario 1 ({keywords[0] if keywords else 'error'})",
            category="exception",
            precondition="User telah login / sistem dalam kondisi normal",
            steps=_generate_steps(section, keywords),
            expected_result=_generate_expected(section),
            priority="high",
            source_section=heading,
            tags=[keywords[0] if keywords else "error", "exception", heading.lower().replace(" ", "-")],
        )
    ]


def generate_integration_testcases(section: object) -> list[Testcase]:
    """Generate integration test cases."""
    keywords = _extract_keywords(section)
    heading = section.heading if hasattr(section, 'heading') else ""
    return [
        Testcase(
            id=f"TC-INTEG-{heading[:20].replace(' ', '-')}-1" if heading else "TC-INTEG-1",
            title=f"Test {heading} - integration scenario 1 ({keywords[0] if keywords else 'api'})",
            category="integration",
            precondition="Service terkait dalam kondisi running",
            steps=_generate_steps(section, keywords),
            expected_result=_generate_expected(section),
            priority="medium",
            source_section=heading,
            tags=[keywords[0] if keywords else "api", "integration", heading.lower().replace(" ", "-")],
        )
    ]


def _determine_category_from_text(text: str) -> str:
    """Alias for _determine_category for backward compatibility."""
    return _determine_category(text)


def _iter_sections(doc) -> list:
    """Walk all sections recursively."""
    sections = []
    for s in doc.sections:
        _walk_section(s, sections)
    return sections


def _walk_section(section: object, sections_list: list):
    """Yield section and all its subsections recursively."""
    sections_list.append(section)
    for sub in getattr(section, "subsections", []):
        _walk_section(sub, sections_list)


def generate_testcases_from_section(section: object) -> list[Testcase]:
    """Generate test cases from a single section."""
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


def generate_testcases(doc, max_per_section: int = 3) -> list[Testcase]:
    """Generate test cases from a POC document."""
    testcases = []
    all_sections = _iter_sections(doc)
    for section in all_sections:
        section_testcases = generate_testcases_from_section(section)
        # Limit test cases per section
        if len(section_testcases) > max_per_section:
            section_testcases = section_testcases[:max_per_section]
        testcases.extend(section_testcases)
    return testcases


def generate_testcases_with_format(
    doc: object,
    max_per_section: int = 3,
    fmt: str = "markdown",
) -> str:
    """Generate testcases lalu kembalikan sebagai string sesuai `fmt`.

    fmt: "json" | "markdown" | "table"
    """
    testcases = generate_testcases(doc, max_per_section=max_per_section)

    if fmt == "json":
        return json.dumps(
            [tc.to_dict() for tc in testcases],
            indent=2,
            ensure_ascii=False,
        )
    if fmt == "table":
        lines = [
            "| ID | Title | Category | Priority |",
            "|----|-------|----------|----------|",
        ]
        lines += [
            f"| {tc.id} | {tc.title} | {tc.category} | {tc.priority} |"
            for tc in testcases
        ]
        return "\n".join(lines)
    return "\n\n".join(tc.to_markdown() for tc in testcases)