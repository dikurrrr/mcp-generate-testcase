import json
import uuid
from parser import POCDocument, Section, extract_keywords, _determine_category
from templates import Testcase

PRIORITY_RULES = {
    "high": ["critical", "must", "harus", "fatal", "security", "auth"],
    "medium": ["should", "wajib", "normal", "standard"],
    "low": ["nice", "optional", "prefer", "saran", "rekomendasi"],
}


def _generate_steps(section: Section, keywords: list[str]) -> list[str]:
    """Generate langkah test case berdasarkan konten section."""
    cat = _determine_category(section.content)
    base_kw = keywords[0] if keywords else "fitur"

    step_templates = {
        "functional": [
            f"Siapkan lingkungan yang sesuai dengan syarat: {section.heading}",
            f"Akses modul/layanan terkait '{base_kw}'",
            f"Jalankan operasi: {section.heading}",
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
            f"Kirim request ke endpoint: {section.heading}",
            f"Verifikasi response status code dan payload",
            f"Verifikasi data tersinkron di service tujuan",
        ],
    }
    return step_templates.get(cat, step_templates["functional"])


def _generate_expected(section: Section) -> str:
    cat = _determine_category(section.content)
    templates = {
        "functional": "Sistem menghasilkan output yang sesuai dengan spesifikasi POC, tanpa error.",
        "boundary": "Sistem menangani input di batas dengan benar: menolak/tidak crash dan menampilkan pesan yang sesuai.",
        "exception": "Sistem menangani exception secara graceful, menampilkan error message yang informatif, dan log tercatat.",
        "integration": "Data ter-transfer dengan benar antar service, status code 2xx, dan tidak ada data loss.",
    }
    return templates.get(cat, templates["functional"])


def generate_testcases(doc: POCDocument, max_per_section: int = 3) -> list[Testcase]:
    """Generate testcases dari seluruh section dokumen POC."""
    testcases: list[Testcase] = []
    counter = 0

    for section in _iter_sections(doc):
        if not section.content.strip():
            continue

        keywords = extract_keywords(section)
        category = _determine_category(section.content)
        priority = _determine_priority(section.content)

        for i in range(min(max_per_section, len(keywords) or 1)):
            counter += 1
            tc_id = f"TC-{counter:03d}"
            kw = keywords[i] if i < len(keywords) else section.heading

            testcases.append(Testcase(
                id=tc_id,
                title=f"Test {section.heading} - scenario {i + 1} ({kw})",
                category=category,
                precondition=f"User telah login / sistem dalam kondisi ready (ref: {doc.title})",
                steps=_generate_steps(section, keywords),
                expected_result=_generate_expected(section),
                priority=priority,
                source_section=section.heading,
                tags=[kw, category, doc.title.lower().replace(" ", "-")],
            ))

    return testcases


def _iter_sections(doc: POCDocument):
    """Walk all sections recursively."""
    for s in doc.sections:
        yield from s.walk()


def generate_testcases_with_format(
    doc: POCDocument,
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
