# DEPRECATED: This file is kept for historical reference.
# Please use tools/combined_generator.py for all test case generation needs.
#!/usr/bin/env python3
"""Generate minimum 200 testcases from available POC files and export to CSV."""

from pathlib import Path
from parser import read_poc_document
from generator import generate_testcases
import csv

def translate_to_indonesian(text: str) -> str:
    indonesian_map = {
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
    for eng, idn in indonesian_map.items():
        text = text.replace(eng, idn)
    return text

def testcase_to_dict(tc) -> dict:
    return {
        "ID": tc.id,
        "Judul": translate_to_indonesian(tc.title),
        "Kategori": translate_to_indonesian(tc.category),
        "Prioritas": translate_to_indonesian(tc.priority),
        "Prasyarat": translate_to_indonesian(tc.precondition),
        "Langkah": " | ".join(tc.steps),
        "Hasil yang Diharapkan": translate_to_indonesian(tc.expected_result),
        "Sumber Section": translate_to_indonesian(tc.source_section),
        "Tag": "; ".join(tc.tags),
    }

# Available POC files
poc_files = [
    "./CODE_FIXES_SUMMARY.md",
    "./README.md",
]

print("=" * 60)
print("Generating testcases from available POC files")
print("=" * 60)

all_testcases = []

for poc_file in poc_files:
    print(f"\nReading: {poc_file}")
    doc = read_poc_document(poc_file)
    print(f"  Sections: {len(doc.sections)}")
    tc = generate_testcases(doc, max_per_section=50)  # High limit
    print(f"  Generated: {len(tc)} testcases")
    all_testcases.extend(tc)
    print(f"  Cumulative: {len(all_testcases)}")

print(f"\n{'=' * 60}")
print(f"Total testcases generated: {len(all_testcases)}")
print(f"{'=' * 60}")

if len(all_testcases) >= 200:
    # Export to CSV
    fieldnames = ["ID", "Judul", "Kategori", "Prioritas", "Prasyarat", "Langkah", "Hasil yang Diharapkan", "Sumber Section", "Tag"]
    
    csv_file = Path("./min-200-testcases-indonesia.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for tc in all_testcases[:200]:  # Only first 200
            row = testcase_to_dict(tc)
            writer.writerow(row)
    
    print(f"\n✅ Exported 200 testcases to: {csv_file}")
    
    # Show preview
    print("\n--- Preview (first 5 rows) ---")
    with open(csv_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines[:6]:
            print(line.strip())
else:
    print(f"\n⚠️  Only {len(all_testcases)} testcases generated (need 200+)")
    print("Try increasing max_per_section or adding more POC files.")