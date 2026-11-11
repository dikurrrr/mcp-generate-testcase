import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class POCDocument:
    title: str
    sections: list["Section"] = field(default_factory=list)
    raw_content: str = ""

    @property
    def all_text(self) -> str:
        return " ".join(
            s.content for s in self.sections
        )


@dataclass
class Section:
    heading: str
    level: int
    content: str
    subsections: list["Section"] = field(default_factory=list)

    def walk(self):
        yield self
        for sub in self.subsections:
            yield from sub.walk()


def read_poc_document(file_path: str) -> POCDocument:
    """Baca file POC (txt, md, atau plain text)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {file_path}")

    raw = path.read_text(encoding="utf-8")
    return parse_markdown(raw, title=path.stem)


def parse_markdown(text: str, title: str = "POC Document") -> POCDocument:
    """Parse dokumen markdown menjadi struktur Section."""
    doc = POCDocument(title=title, raw_content=text)
    lines = text.split("\n")

    stack: list[tuple[int, Section]] = []  # (level, section)
    current_section = Section(heading=title, level=0, content="")
    buffer: list[str] = []

    for line in lines:
        heading_match = re.match(r"^(#{1,6})\s+(.*)", line)

        if heading_match:
            # Flush buffer ke section aktif
            if buffer:
                current_section.content += " ".join(buffer) + " "
                buffer = []

            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()

            # Pop stack hingga level cocok
            while stack and stack[-1][0] >= level:
                stack.pop()

            parent = stack[-1][1] if stack else None
            section = Section(heading=heading_text, level=level, content="")

            if parent is None:
                doc.sections.append(section)
            else:
                parent.subsections.append(section)

            stack.append((level, section))
            current_section = section

        else:
            buffer.append(line.strip())

    # Flush terakhir
    if buffer:
        current_section.content += " ".join(buffer)

    return doc


def _determine_category(text: str) -> str:
    """Determine section category from content."""
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


def extract_keywords(section: Section) -> list[str]:
    """Ekstrak kata kunci dari isi section untuk generate testcase."""
    stopwords = {
        "the", "a", "an", "is", "are", "will", "shall", "should",
        "dan", "di", "ke", "dari", "untuk", "yang", "dengan",
        "ini", "itu", "akan", "dapat", "bisa", "pada", "atau",
    }
    words = re.findall(r"[a-zA-Z\u00C0-\u017F]{4,}", section.content.lower())
    # Sederhana: ambil kata yang paling sering muncul
    freq = {}
    for w in words:
        if w not in stopwords:
            freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: -x[1])
    return [w for w, _ in sorted_words[:10]]
