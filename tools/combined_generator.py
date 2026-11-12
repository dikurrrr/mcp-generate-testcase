#!/usr/bin/env python3
"""Combined generator script - menggabungkan tools/generate_batch.py, generated-testcases/generate_csv.py, generator.py, dan generate-200-testcases.py."""

import argparse
import csv
import json
import sys
from pathlib import Path
from datetime import datetime

# Agar modul di root repo bisa di-import saat script dijalankan langsung.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parser import read_poc_document
from generator import generate_testcases, Testcase

INDONESIAN_MAP = {
    "functional": "fungsi",
    "boundary": "batas",
    "exception": "exception",
    "integration": "integrasi",
    "high": "tinggi",
    "medium": "sedang",
    "low": "rendah",
    "Test": "Test",
    "Scenario": "Skenario",
    "Priority": "Prioritas",
    "Source Section": "Sumber Section",
    "Tags": "Tag",
    "Precondition": "Prasyarat",
    "Steps": "Langkah",
    "Expected Result": "Hasil yang Diharapkan",
    "ID": "ID",
    "Title": "Judul",
}


def translate_to_indonesian(text: str) -> str:
    for eng, idn in INDONESIAN_MAP.items():
        text = text.replace(eng, idn)
    return text


def _steps_cell(tc) -> str:
    return "\n".join(f"{i}. {step}" for i, step in enumerate(tc.steps, 1))


def doc_paths(docs_dir: Path):
    return [p for p in sorted(docs_dir.iterdir()) if p.is_file() and p.suffix.lower() in {".md", ".txt"}]


def collect(paths: list, max_per_section: int) -> dict:
    per_doc = {}
    for path in paths:
        doc = read_poc_document(str(path))
        tcs = generate_testcases(doc, max_per_section=max_per_section)
        # Store document name with each test case
        for tc in tcs:
            tc._doc_name = path.stem  # Store basename without extension
        per_doc[path.stem] = tcs
    return per_doc


def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate test case dari POC")
    ap.add_argument("--docs-dir", default="docs", help="Folder berisi dokumen POC")
    ap.add_argument("--total", type=int, default=0, help="Target test case (0 = semua)")
    ap.add_argument("--max-per-section", type=int, default=5, help="Batas per section")
    ap.add_argument("--out-dir", default="generated-testcases", help="Folder output")
    ap.add_argument("--lang", choices=["en", "id"], default="en", help="Bahasa label: en=English (default), id=Indonesia")
    args = ap.parse_args()

    docs_dir = Path(args.docs_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = doc_paths(docs_dir)
    if not paths:
        print(f"Tidak ada dokumen POC di {docs_dir}")
        return

    per_doc = collect(paths, args.max_per_section)

    # Ambil semua rule dulu
    all_rules = [tc for name, tcs in per_doc.items() for tc in tcs if tc.kind == "rule"]
    if args.total and args.total < len(all_rules):
        target = args.total
    else:
        target = len(all_rules)

    # Bangka rows: dulu rule, lalu generic proporsional
    rows = list(all_rules)
    remaining = target - len(rows)
    generics = {name: [tc for tc in tcs if tc.kind != "rule"] for name, tcs in per_doc.items()}
    total_rules_per_doc = {name: sum(1 for tc in tcs if tc.kind == "rule") for name, tcs in per_doc.items()}
    total_rules = sum(total_rules_per_doc.values()) or 1
    quota = {}
    for name in per_doc:
        quota[name] = round(remaining * total_rules_per_doc.get(name, 0) / total_rules)

    for name in per_doc:
        gen_list = generics[name]
        take = min(quota.get(name, 0), len(gen_list))
        for tc in gen_list[:take]:
            rows.append(tc)

    # Renumber ID and ensure document name is preserved
    for i, tc in enumerate(rows, 1):
        tc.id = f"TC-{i:03d}"

    # Output filenames berdasarkan bahasa
    lang_suffix = "id" if args.lang == "id" else "en"
    out_md = out_dir / f"all-testcases-{lang_suffix}.md"
    out_json = out_dir / f"all-testcases-{lang_suffix}.json"
    out_csv = out_dir / f"all-testcases-{lang_suffix}-{datetime.now().strftime("%Y-%m-%d")}.csv"

    # Timestamp untuk semua output
    timestamp = get_timestamp()

    # Tulis MD
    md_lines = []
    for tc in rows:
        md_lines.append(f"# {tc.title}")
        md_lines.append(f"## Precondition\n{tc.precondition}")
        md_lines.append(f"## Steps")
        for step in tc.steps:
            md_lines.append(f"- {step}")
        md_lines.append(f"## Expected Result\n{tc.expected_result}")
        md_lines.append("")
    out_md.write_text("\n".join(md_lines), encoding="utf-8")

    # Tulis JSON
    json_data = [tc.to_dict() for tc in rows]
    out_json.write_text(json.dumps(json_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Tulis CSV dengan kolom timestamp
    if args.lang == "id":
        csv_header = [
            "ID",
            "Judul",
            "Kategori",
            "Prioritas",
            "Prasyarat",
            "Langkah",
            "Hasil yang Diharapkan",
            "Sumber Section",
            "Tag",
            
        ]
    else:
        csv_header = [
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

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_header)
        writer.writeheader()
        for tc in rows:
            if args.lang == "id":
                writer.writerow({
                    "ID": tc.id,
                    "Judul": tc.title,
                    "Kategori": tc.category,
                    "Prioritas": tc.priority,
                    "Prasyarat": tc.precondition,
                    "Langkah": _steps_cell(tc),
                    "Hasil yang Diharapkan": tc.expected_result,
                    "Sumber Section": tc.source_section,
                    "Tag": ", ".join(tc.tags),
                })
            else:
                writer.writerow({
                    "id": tc.id,
                    "title": tc.title,
                    "document": tc._doc_name if hasattr(tc, "_doc_name") else "",
                    "category": tc.category,
                    "priority": tc.priority,
                    "kind": tc.kind,
                    "precondition": tc.precondition,
                    "steps": _steps_cell(tc),
                    "expected_result": tc.expected_result,
                    "source_section": tc.source_section,
                    "tags": ", ".join(tc.tags),
                })

    rule_count = sum(1 for tc in rows if tc.kind == "rule")
    print(f"✅ {len(rows)} test case dari {len({tc._doc_name if hasattr(tc, '_doc_name') else '' for tc in rows})} dokumen ({rule_count} rule-based)")
    for fname in ("all-testcases.md", "all-testcases.json", "all-testcases.csv"):
        print(f"  {out_dir / fname}")


if __name__ == "__main__":
    main()
