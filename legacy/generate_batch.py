# DEPRECATED: This file is kept for historical reference.
# Please use tools/combined_generator.py for all test case generation needs.
"""Generate test case dari semua POC di docs/ menjadi satu set output.

Contoh:
    python tools/generate_batch.py
    python tools/generate_batch.py --total 200
    python tools/generate_batch.py --docs-dir docs --out-dir generated-testcases

Hasil: all-testcases.md, all-testcases.json, all-testcases.csv.

Test case hasil ekstraksi aturan (`kind == "rule"`) diprioritaskan; template
generic dipakai sebagai pelengkap sampai total terpenuhi. ID dirapikan ulang
berurutan karena tiap dokumen memulai dari TC-001.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

# Agar `parser`/`generator` di root repo bisa di-import saat script dijalankan langsung.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generator import generate_testcases  # noqa: E402
from parser import read_poc_document  # noqa: E402

CSV_COLUMNS = [
    "id",
    "title",
    "document",
    "category",
    "priority",
    "kind",
    "precondition",
    "steps",
    "expected_result",
    "source_section",
    "tags",
]


def doc_paths(docs_dir: Path) -> list[Path]:
    return [
        p for p in sorted(docs_dir.iterdir())
        if p.is_file() and p.suffix.lower() in {".md", ".txt"}
    ]


def collect(paths: list[Path], max_per_section: int) -> dict[str, list]:
    """Kumpulkan test case per dokumen, dipisah rule vs generic."""
    per_doc: dict[str, list] = {}
    for path in paths:
        doc = read_poc_document(str(path))
        tcs = generate_testcases(doc, max_per_section=max_per_section)
        per_doc[path.stem] = tcs
    return per_doc


def count_rules(per_doc: dict[str, list]) -> int:
    return sum(1 for tcs in per_doc.values() for tc in tcs if tc.kind == "rule")


def build(per_doc: dict[str, list], total: int, per_doc_generic: int) -> list:
    """Ambil semua test case rule, lengkapi dengan generic sampai `total`."""
    rules = [(name, tc) for name, tcs in per_doc.items()
             for tc in tcs if tc.kind == "rule"]
    generics = {name: [tc for tc in tcs if tc.kind != "rule"]
                for name, tcs in per_doc.items()}

    if len(rules) >= total:
        return rules[:total]

    rows = list(rules)
    remaining = total - len(rows)
    # Kuota generic proporsional terhadap jumlah rule tiap dokumen.
    rule_count = {name: sum(1 for n, _ in rules if n == name) for name in per_doc}
    total_rules = sum(rule_count.values()) or 1
    quota = {}
    for name in per_doc:
        quota[name] = round(remaining * rule_count[name] / total_rules)
    quota[list(per_doc)[-1]] += remaining - sum(quota.values())

    for name, tcs in generics.items():
        take = min(quota.get(name, 0), len(tcs), per_doc_generic)
        rows.extend((name, tc) for tc in tcs[:take])

    # Kalau masih kurang (mis. generic tiap dokumen habis), ambil sisa apa pun.
    if len(rows) < total:
        used = {id(tc) for _, tc in rows}
        spare = [(name, tc) for name, tcs in generics.items()
                 for tc in tcs if id(tc) not in used]
        rows.extend(spare[:total - len(rows)])

    return rows[:total]


def _steps_cell(tc) -> str:
    """Langkah per baris di dalam satu sel CSV (Excel/Sheets tetap membacanya
    sebagai satu sel karena field-nya di-quote)."""
    return "\n".join(f"{i}. {step}" for i, step in enumerate(tc.steps, 1))


def write_csv(rows: list[tuple[str, object]], out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for doc_name, tc in rows:
            writer.writerow({
                "id": tc.id,
                "title": tc.title,
                "document": doc_name,
                "category": tc.category,
                "priority": tc.priority,
                "kind": tc.kind,
                "precondition": tc.precondition,
                "steps": _steps_cell(tc),
                "expected_result": tc.expected_result,
                "source_section": tc.source_section,
                "tags": ", ".join(tc.tags),
            })


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--docs-dir", default="docs")
    ap.add_argument("--out-dir", default="generated-testcases")
    ap.add_argument("--total", type=int, default=0,
                    help="Total test case yang diinginkan (0 = semua)")
    ap.add_argument("--max-per-section", type=int, default=6,
                    help="Batas test case generic per section saat melengkapi")
    args = ap.parse_args()

    docs_dir = Path(args.docs_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = doc_paths(docs_dir)
    if not paths:
        raise SystemExit(f"Tidak ada dokumen POC di {docs_dir}")

    # Naikkan jumlah scenario generic bertahap kalau target belum tercapai.
    per_doc = collect(paths, args.max_per_section)
    if args.total:
        for extra in range(1, 21):
            if sum(len(v) for v in per_doc.values()) >= args.total:
                break
            per_doc = collect(paths, args.max_per_section + extra)

    rows = (build(per_doc, args.total, args.max_per_section * 4)
            if args.total else
            [(name, tc) for name, tcs in per_doc.items() for tc in tcs])

    # ID unik berurutan lintas dokumen.
    for i, (doc_name, tc) in enumerate(rows, 1):
        tc.id = f"TC-{i:03d}"

    (out_dir / "all-testcases.md").write_text(
        "\n\n".join(tc.to_markdown() for _, tc in rows) + "\n", encoding="utf-8"
    )
    (out_dir / "all-testcases.json").write_text(
        json.dumps([tc.to_dict() for _, tc in rows], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_csv(rows, out_dir / "all-testcases.csv")

    rule_count = sum(1 for _, tc in rows if tc.kind == "rule")
    print(f"{len(rows)} test case dari {len({d for d, _ in rows})} dokumen "
          f"({rule_count} rule-based, {len(rows) - rule_count} generic)")
    for name in ("all-testcases.md", "all-testcases.json", "all-testcases.csv"):
        print(f"  {out_dir / name}")


if __name__ == "__main__":
    main()
