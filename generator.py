import json
import re
from parser import POCDocument, Section, extract_keywords
from templates import Testcase

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

PRIORITY_RULES = {
    "high": ["critical", "must", "harus", "fatal", "security", "auth"],
    "medium": ["should", "wajib", "normal", "standard"],
    "low": ["nice", "optional", "prefer", "saran", "rekomendasi"],
}

# Batas jumlah test case hasil ekstraksi aturan per section, supaya satu
# section yang padat aturan tidak mendominasi seluruh dokumen.
MAX_RULES_PER_SECTION = 6
MAX_MESSAGES_PER_SECTION = 3
MAX_ACTIONS_PER_SECTION = 2
MAX_ENUMS_PER_SECTION = 2
MAX_OBLIGATIONS_PER_SECTION = 8

UNIT = r"(karakter|kata|item|baris|file|tingkat|MB|hari|jam)"

PAT_LEN_RANGE = re.compile(
    rf"min\.?\s*(\d+)\s*,?\s*maks\.?\s*(\d+)\s*{UNIT}?", re.IGNORECASE)
PAT_MAX = re.compile(rf"maks\.?\s*(\d+)\s*{UNIT}?", re.IGNORECASE)
PAT_MIN = re.compile(rf"min\.?\s*(\d+)\s*{UNIT}?", re.IGNORECASE)
PAT_GTE = re.compile(r"(?:≥|>=)\s*(\d+)")
PAT_LTE = re.compile(r"(?:≤|<=)\s*(\d+)")
PAT_MESSAGE = re.compile(r'"([^"\n]{12,120})"')
PAT_ACTION = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/[A-Za-z0-9_\-\[\]/{}<>:.$]+)")
PAT_ENUM = re.compile(r"default\s+(\w[\w-]*)[^.]{0,80}?atau\s+(\w[\w-]*)", re.IGNORECASE)

# Kata kunci yang menandai sebuah kalimat benar-benar berisi aturan perilaku.
OBLIGATION_CUES = ("wajib", "harus", "tidak boleh", "hanya", "otomatis",
                   "ditolak", "tidak bisa", "minimal", "maksimal", "boleh")
# Kalimat kutipan yang berisi penanda ini baru dianggap pesan validasi.
MESSAGE_CUES = ("wajib", "tidak", "ditolak", "dipakai", "gagal", "lewat",
                "dicabut", "dikenali", "dipilih", "belum", "minimal", "maksimal",
                "harus", "invalid", "terlalu", "kosong")

# Potongan teks yang menandakan angka tersebut rujukan kode/migrasi, bukan aturan.
NOISE_SUBJECT = ("migrasi", "src/", "route.ts", "page.tsx", ".yml", "docs/",
                 "posgres", "postgres", "commit", "versi", "P0-", "PR-")

# Karakter diagram alur di PDF — bukan kalimat aturan.
DIAGRAM_CHARS = re.compile(r"[─│▶◀▼▲└┌┐┘├┤┬┴┼→←↔]")

# Label tabel yang ikut terekspos saat teks PDF diratakan.
TABLE_LABELS = ("Field Wajib? Aturan & catatan", "Field Wajib?", "Aturan & catatan",
                "Aturan", "Wajib?", "Field", "Kolom", "Contoh")


def _determine_category(text: str) -> str:
    text_lower = text.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return cat
    return "functional"


def _determine_priority(text: str) -> str:
    text_lower = text.lower()
    for prio, keywords in PRIORITY_RULES.items():
        if any(kw in text_lower for kw in keywords):
            return prio
    return "medium"


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


# ─── Ekstraksi aturan konkret dari teks section ───────────────────────────────

def _clean_subject(text: str, start: int, width: int = 110) -> str:
    """Ambil potongan teks sebelum angka sebagai konteks/field."""
    chunk = text[max(0, start - width):start]
    chunk = re.split(r"[.;|•\n·]", chunk)[-1]
    # Label/ikon tabel ikut terekspos saat PDF diratakan — buang supaya
    # subject-nya tinggal nama field.
    for mark in ("✅", "⭕", "✱", "❌"):
        chunk = chunk.split(mark)[0]
    for label in TABLE_LABELS:
        chunk = chunk.replace(label, " ")
    chunk = chunk.replace('"', " ").replace("(", " ").replace(")", " ")
    chunk = re.sub(r"^(?:dan|atau|serta|dengan|untuk|pada|di|ke|dari)\s+", "",
                   chunk.strip(), flags=re.IGNORECASE)
    chunk = re.sub(r"\s+", " ", chunk).strip(" -:–\t,")
    words = chunk.split()[-3:]
    # Buang sisa token aturan yang ikut terbawa ("maks", "≥3", "wajib", angka).
    noise_token = re.compile(r"^(?:kata|dan|atau|dengan|untuk|pada|di|ke|dari|"
                             r"maks|min|minimal|maksimal|wajib|opsional|"
                             r"[≥≤<>=\d].*)$", re.IGNORECASE)
    while words and noise_token.match(words[0]):
        words.pop(0)
    return " ".join(words)[:45].strip(" -:–\t·,")


def _is_noise(subject: str) -> bool:
    low = subject.lower()
    return any(bad.lower() in low for bad in NOISE_SUBJECT)


def extract_rules(text: str) -> list[dict]:
    """Ambil aturan angka (min/maks/rentang) dari teks section."""
    rules: list[dict] = []
    seen: set[tuple] = set()

    def add(kind: str, lo: int | None, hi: int | None, unit: str, subject: str):
        # Subject yang isinya cuma satuan (mis. "MB/ﬁle") bukan nama field.
        if subject.lower().strip("/,") in {"mb", "mb/file", "file", "karakter",
                                           "item", "baris", "tingkat"}:
            subject = ""
        key = (kind, lo, hi, unit, subject)
        if key in seen or _is_noise(subject):
            return
        # Nilai tak masuk akal untuk sebuah aturan produk (nomor migrasi, tahun, dsb).
        for v in (lo, hi):
            if v is not None and (v < 0 or v > 5000):
                return
        seen.add(key)
        rules.append({"kind": kind, "min": lo, "max": hi,
                      "unit": (unit or "").strip(), "subject": subject})

    range_spans: list[tuple[int, int]] = []

    for m in PAT_LEN_RANGE.finditer(text):
        range_spans.append(m.span())
        add("range", int(m.group(1)), int(m.group(2)), m.group(3) or "",
            _clean_subject(text, m.start()))

    def in_range(pos: int) -> bool:
        return any(lo <= pos < hi for lo, hi in range_spans)

    for m in PAT_MAX.finditer(text):
        if in_range(m.start()):
            continue  # sudah tercakup sebagai rentang min–maks
        add("max", None, int(m.group(1)), m.group(2) or "",
            _clean_subject(text, m.start()))
    for m in PAT_MIN.finditer(text):
        if in_range(m.start()):
            continue
        add("min", int(m.group(1)), None, m.group(2) or "",
            _clean_subject(text, m.start()))
    for m in PAT_GTE.finditer(text):
        if in_range(m.start()):
            continue
        add("gte", int(m.group(1)), None, "",
            _clean_subject(text, m.start()))
    for m in PAT_LTE.finditer(text):
        if in_range(m.start()):
            continue
        add("lte", None, int(m.group(1)), "",
            _clean_subject(text, m.start()))

    return rules[:MAX_RULES_PER_SECTION]


def extract_messages(text: str) -> list[str]:
    """Ambil pesan validasi/error yang dikutip di dokumen."""
    out: list[str] = []
    for m in PAT_MESSAGE.finditer(text):
        msg = " ".join(m.group(1).split())
        low = msg.lower()
        if len(msg) < 10 or _is_noise(msg):
            continue
        # Hanya kutipan yang bernada pesan validasi, bukan judul/label tabel.
        if not any(cue in low for cue in MESSAGE_CUES):
            continue
        if msg not in out:
            out.append(msg)
    return out[:MAX_MESSAGES_PER_SECTION]


def extract_obligations(text: str) -> list[str]:
    """Ambil kalimat aturan perilaku (wajib/harus/tidak boleh/hanya/...)."""
    out: list[str] = []
    for raw in re.split(r'(?<=[.!?])["\')\]]?\s+|•', text):
        sentence = " ".join(raw.split())
        # Sisa sel tabel ikut menempel ("… ✅ saat publish") — potong di penanda sel.
        for mark in ("✅", "⭕", "✱", "❌"):
            sentence = sentence.split(mark)[0]
        sentence = sentence.strip(" -–—")
        if len(sentence) > 160:
            sentence = sentence[:157].rsplit(" ", 1)[0] + "…"
        if not 30 <= len(sentence) <= 180:
            continue
        if _is_noise(sentence) or not re.search(r"[a-zA-Z]{3,}", sentence):
            continue
        if DIAGRAM_CHARS.search(sentence):
            continue
        low = sentence.lower()
        if not any(cue in low for cue in OBLIGATION_CUES):
            continue
        if sentence not in out:
            out.append(sentence)
    return out[:MAX_OBLIGATIONS_PER_SECTION]


def extract_actions(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in PAT_ACTION.finditer(text):
        pair = (m.group(1).upper(), m.group(2).rstrip(".,);"))
        if pair not in out:
            out.append(pair)
    return out[:MAX_ACTIONS_PER_SECTION]


def extract_enums(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in PAT_ENUM.finditer(text):
        pair = (m.group(1), m.group(2))
        if pair not in out and not _is_noise(pair[0]):
            out.append(pair)
    return out[:MAX_ENUMS_PER_SECTION]


# ─── Pembentukan test case dari aturan ───────────────────────────────────────

def _tc(counter: list[int], **kwargs) -> Testcase:
    counter[0] += 1
    return Testcase(id=f"TC-{counter[0]:03d}", **kwargs)


GENERIC_TOKENS = {"baris", "item", "data", "user", "sistem", "form", "field",
                  "wajib", "nilai", "input", "dokumen", "halaman", "vendor"}

# Penanda bahwa sebuah pesan memang bicara soal batas/validasi.
RULE_CUES = MESSAGE_CUES + ("karakter", "lebih", "melebihi")


def _pick_message(messages: list[str], rule: dict) -> str | None:
    """Pilih pesan validasi yang relevan dengan aturan (cocokkan kata kunci).

    Butuh dua syarat: ada kata dari nama field DAN ada penanda aturan
    (minimal/maksimal/wajib/karakter/...), supaya tidak salah tempel pesan.
    """
    tokens = [w.lower() for w in re.findall(r"[A-Za-z]{3,}", rule["subject"])
              if w.lower() not in GENERIC_TOKENS]
    unit = rule["unit"].lower()

    for msg in messages:
        low = msg.lower()
        rule_cue = any(cue in low for cue in RULE_CUES)
        if not rule_cue:
            continue
        if any(tok in low for tok in tokens) or (unit and unit in low):
            return msg
    return None


def _rule_testcases(section: Section, counter: list[int],
                    doc: POCDocument, messages: list[str]) -> list[Testcase]:
    """Test case boundary/exception konkret dari aturan angka di section."""
    tcs: list[Testcase] = []

    for rule in extract_rules(section.content):
        subject = rule["subject"] or section.heading
        u = rule["unit"]
        suffix = f" {u}" if u else ""
        lo, hi = rule["min"], rule["max"]
        message = _pick_message(messages, rule)
        invalid_expected = (
            f"Sistem menolak input dan menampilkan pesan: \"{message}\"" if message
            else "Sistem menolak input dengan pesan validasi yang jelas, data tidak tersimpan."
        )

        def push(value: int, label: str, valid: bool):
            tcs.append(_tc(
                counter,
                title=f"Test {subject} — {value}{suffix} ({label})",
                category="boundary",
                precondition=f"Form pada bagian '{section.heading}' terbuka dan user sudah login",
                steps=[
                    f"Isi '{subject}' dengan {value}{suffix}",
                    "Simpan / submit form",
                    "Amati respons sistem",
                ],
                expected_result=(
                    f"Input diterima, nilai {value}{suffix} tersimpan tanpa error."
                    if valid else invalid_expected
                ),
                priority=_determine_priority(section.content),
                source_section=section.heading,
                tags=[subject, "boundary", "rule"],
                kind="rule",
            ))

        if lo is not None and hi is not None:
            push(lo, "batas bawah, valid", True)
            push(max(lo - 1, 0), "di bawah batas bawah, ditolak", False)
            push(hi, "batas atas, valid", True)
            push(hi + 1, "di atas batas atas, ditolak", False)
        elif hi is not None:
            push(hi, "batas maksimum, valid", True)
            push(hi + 1, "melebihi batas maksimum, ditolak", False)
        elif lo is not None:
            push(lo, "batas minimum, valid", True)
            push(max(lo - 1, 0), "di bawah batas minimum, ditolak", False)

    return tcs


def _obligation_testcases(section: Section, counter: list[int]) -> list[Testcase]:
    """Test case dari kalimat aturan perilaku di section (wajib/harus/ditolak/...)."""
    tcs: list[Testcase] = []
    for sentence in extract_obligations(section.content):
        low = sentence.lower()
        negative = any(cue in low for cue in
                       ("tidak boleh", "ditolak", "tidak bisa", "belum", "hanya"))
        title = sentence if len(sentence) <= 70 else sentence[:67].rstrip() + "…"

        if negative:
            steps = [
                f"Siapkan kondisi normal pada '{section.heading}'",
                f"Coba langgar aturan: {sentence}",
                "Periksa respons sistem terhadap pelanggaran",
            ]
            expected = f"Sistem menolak aksi sesuai aturan: \"{sentence}\"."
            category, priority = "exception", "high"
        else:
            steps = [
                f"Siapkan kondisi sesuai aturan: {sentence}",
                "Jalankan alur yang diatur pada bagian ini",
                "Periksa hasil terhadap aturan tersebut",
            ]
            expected = f"Sistem berperilaku sesuai aturan: \"{sentence}\"."
            category = "functional"
            priority = _determine_priority(section.content)

        tcs.append(_tc(
            counter,
            title=f"Test aturan: {title}",
            category=category,
            precondition=f"User berada di bagian '{section.heading}' dan sudah login",
            steps=steps,
            expected_result=expected,
            priority=priority,
            source_section=section.heading,
            tags=[section.heading, category, "rule-sentence"],
            kind="rule",
        ))

        # Aturan wajib/harus punya sisi negatif yang layak diuji terpisah.
        if not negative and any(cue in low for cue in ("wajib", "harus")):
            tcs.append(_tc(
                counter,
                title=f"Test aturan (negatif): {title}",
                category="exception",
                precondition=f"User berada di bagian '{section.heading}' dan sudah login",
                steps=[
                    "Siapkan kondisi normal pada bagian ini",
                    f"Lewati pemenuhan aturan: {sentence}",
                    "Periksa apakah sistem menolak / menandai ketidaksesuaian",
                ],
                expected_result=(
                    f"Sistem menolak atau menandai pelanggaran aturan: \"{sentence}\"."
                ),
                priority="high",
                source_section=section.heading,
                tags=[section.heading, "exception", "rule-sentence"],
                kind="rule",
            ))
    return tcs


def _message_testcases(section: Section, counter: list[int],
                       doc: POCDocument) -> list[Testcase]:
    """Satu test case negatif per pesan validasi yang dikutip dokumen."""
    tcs: list[Testcase] = []
    for msg in extract_messages(section.content):
        tcs.append(_tc(
            counter,
            title=f"Test validasi: {msg[:70]}",
            category="exception",
            precondition=f"User berada di bagian '{section.heading}'",
            steps=[
                "Picu kondisi yang melanggar aturan pada bagian ini",
                "Submit form / aksi",
                "Periksa pesan yang muncul di UI",
            ],
            expected_result=f"Sistem menampilkan pesan: \"{msg}\" dan tidak menyimpan data.",
            priority="high",
            source_section=section.heading,
            tags=[extract_keywords(section)[0] if extract_keywords(section) else section.heading,
                  "exception", "validation-message"],
            kind="rule",
        ))
    return tcs


def _action_testcases(section: Section, counter: list[int]) -> list[Testcase]:
    """Test integrasi untuk endpoint yang disebut di section."""
    tcs: list[Testcase] = []
    for method, path in extract_actions(section.content):
        tcs.append(_tc(
            counter,
            title=f"Test {method} {path} — respons dan validasi",
            category="integration",
            precondition="Service berjalan, user terautentikasi sesuai aturan bagian ini",
            steps=[
                f"Kirim request {method} {path} dengan payload valid",
                "Periksa status code dan body respons",
                f"Kirim request {method} {path} dengan payload tidak valid",
                "Periksa status code dan pesan error",
            ],
            expected_result="Request valid menghasilkan status 2xx; request tidak valid ditolak 4xx dengan pesan jelas.",
            priority="high",
            source_section=section.heading,
            tags=[path, "integration", "api"],
            kind="rule",
        ))
    return tcs


def _enum_testcases(section: Section, counter: list[int]) -> list[Testcase]:
    """Test per opsi mode/tipe yang disebut sebagai alternatif."""
    tcs: list[Testcase] = []
    for first, second in extract_enums(section.content):
        for opt in (first, second):
            tcs.append(_tc(
                counter,
                title=f"Test opsi {opt} pada {section.heading}",
                category="functional",
                precondition=f"User membuka bagian '{section.heading}'",
                steps=[
                    f"Pilih opsi '{opt}'",
                    "Lanjutkan alur sampai selesai",
                    "Periksa perilaku sistem sesuai opsi yang dipilih",
                ],
                expected_result=f"Sistem memproses alur dengan mode '{opt}' sesuai aturan POC.",
                priority=_determine_priority(section.content),
                source_section=section.heading,
                tags=[opt, "functional", "option"],
                kind="rule",
            ))
    return tcs


def _generic_testcases(section: Section, counter: list[int],
                       doc: POCDocument, max_per_section: int) -> list[Testcase]:
    """Test case template lama — dipakai sebagai pelengkap."""
    tcs: list[Testcase] = []
    keywords = extract_keywords(section)
    category = _determine_category(section.content)
    priority = _determine_priority(section.content)

    for i in range(min(max_per_section, len(keywords) or 1)):
        kw = keywords[i] if i < len(keywords) else section.heading
        tcs.append(_tc(
            counter,
            title=f"Test {section.heading} - scenario {i + 1} ({kw})",
            category=category,
            precondition=f"User telah login / sistem dalam kondisi ready (ref: {doc.title})",
            steps=_generate_steps(section, keywords),
            expected_result=_generate_expected(section),
            priority=priority,
            source_section=section.heading,
            tags=[kw, category, doc.title.lower().replace(" ", "-")],
            kind="generic",
        ))
    return tcs


def generate_testcases(doc: POCDocument, max_per_section: int = 3,
                       enrich: bool = True) -> list[Testcase]:
    """Generate testcases dari seluruh section dokumen POC.

    enrich=True menambahkan test case konkret dari aturan yang diekstrak
    (batas angka, pesan validasi, endpoint, opsi mode) sebelum melengkapi
    dengan template generic.
    """
    testcases: list[Testcase] = []
    counter = [0]
    seen_titles: set[str] = set()

    def add(batch: list[Testcase]) -> None:
        for tc in batch:
            if tc.title in seen_titles:
                continue
            seen_titles.add(tc.title)
            testcases.append(tc)

    for section in _iter_sections(doc):
        if not section.content.strip():
            continue

        keywords = extract_keywords(section)
        category = _determine_category(section.content)
        priority = _determine_priority(section.content)

        if enrich:
            messages = extract_messages(section.content)
            add(_rule_testcases(section, counter, doc, messages))
            add(_obligation_testcases(section, counter))
            add(_message_testcases(section, counter, doc))
            add(_action_testcases(section, counter))
            add(_enum_testcases(section, counter))

        for i in range(min(max_per_section, len(keywords) or 1)):
            kw = keywords[i] if i < len(keywords) else section.heading

            add([_tc(
                counter,
                title=f"Test {section.heading} - scenario {i + 1} ({kw})",
                category=category,
                precondition=f"User telah login / sistem dalam kondisi ready (ref: {doc.title})",
                steps=_generate_steps(section, keywords),
                expected_result=_generate_expected(section),
                priority=priority,
                source_section=section.heading,
                tags=[kw, category, doc.title.lower().replace(" ", "-")],
                kind="generic",
            )])

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
