# DEPRECATED: This file is kept for historical reference.
# Please use tools/combined_generator.py for all test case generation needs.
#!/usr/bin/env python3
"""Generate testcases from POC and export to CSV with Indonesian labels."""

import csv
from pathlib import Path

from parser import read_poc_document
from generator import generate_testcases


def translate_to_indonesian(text: str) -> str:
    """Simple Indonesian translation for testcase labels and values."""
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
    """Convert Testcase dataclass to dictionary.
    Keys must match CSV fieldnames exactly.
    """
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


def main():
    # Baca file POC (gunakan README.md sebagai contoh)
    doc = read_poc_document("./README.md")
    
    # Generate testcases
    testcases = generate_testcases(doc, max_per_section=3)
    
    print(f"Generated {len(testcases)} testcases dari POC: {doc.title}\n")
    
    # Define CSV field names (Indonesian)
    fieldnames = [
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
    
    # Tulis ke CSV
    csv_file = Path("./testcases-indonesia.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for tc in testcases:
            row = testcase_to_dict(tc)
            writer.writerow(row)
    
    print(f"✅ CSV exported to: {csv_file}")
    print(f"Total rows: {len(testcases)}")
    
    # Print preview
    print("\n--- Preview CSV ---")
    with open(csv_file, "r", encoding="utf-8") as f:
        print(f.read())


if __name__ == "__main__":
    main()