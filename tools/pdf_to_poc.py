"""Konversi dokumen PDF (requirement/POC) menjadi markdown POC.

Parser MCP di repo ini hanya bisa membaca teks (.md/.txt), jadi PDF harus
dijadikan markdown dulu sebelum bisa dipakai `generate_testcases`.

Pemakaian:
    python tools/pdf_to_poc.py 01-requisition-approval-bidding-1.pdf \\
        -o docs/01-requisition-approval-bidding.md \\
        --title "POC: Requisition, Approval, sampai Bidding"

Heading dideteksi dari penomoran yang berurutan:
    "1. Judul"     -> "## Judul"
    "4.2 Judul"    -> "### Judul"
Nomor dianggap heading hanya jika sesuai urutan; daftar bernomor di dalam
section tetap jadi teks biasa.
"""

import argparse
import re
from pathlib import Path

from pypdf import PdfReader

# Baris header/footer halaman yang berulang di tiap halaman PDF.
DEFAULT_NOISE = r"^(Savinix\s+—|Halaman\s+\d+\s*/\s*\d+$)"


def extract_text(pdf_path: str) -> str:
    """Ambil teks mentah seluruh halaman PDF."""
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        pages.append((page.extract_text() or "").strip())
    return "\n".join(pages)


def clean_text(text: str, noise_pattern: str = DEFAULT_NOISE) -> list[str]:
    """Buang baris noise, rapikan baris kosong berulang."""
    noise = re.compile(noise_pattern)
    lines = []
    for raw in text.split("\n"):
        line = raw.strip()
        if noise.match(line):
            continue
        if not line and lines and not lines[-1]:
            continue
        lines.append(line)
    return lines


def to_markdown(lines: list[str], title: str) -> str:
    """Ubah baris teks menjadi markdown dengan heading berurutan."""
    out = [f"# {title}"]
    expected_top = 1   # nomor section (## ) berikutnya yang diharapkan
    expected_sub = 1   # nomor sub-section (### ) berikutnya

    def add_heading(level: int, text: str) -> None:
        if out and out[-1] != "":
            out.append("")
        out.append(f"{'#' * level} {text}")

    for line in lines:
        sub = re.match(r"^(\d+)\.(\d+)\s+(\S.*)$", line)
        top = re.match(r"^(\d+)\.\s+(\S.*)$", line)

        if (
            sub
            and len(line) < 120
            and int(sub.group(1)) == expected_top - 1
            and int(sub.group(2)) == expected_sub
        ):
            add_heading(3, sub.group(3))
            expected_sub += 1
        elif top and len(line) < 120 and int(top.group(1)) == expected_top:
            add_heading(2, top.group(2))
            expected_top += 1
            expected_sub = 1
        else:
            out.append(line)

    return "\n".join(out).strip() + "\n"


def convert(pdf_path: str, out_path: str, title: str | None = None,
            noise_pattern: str = DEFAULT_NOISE) -> str:
    text = extract_text(pdf_path)
    title = title or Path(pdf_path).stem
    md = to_markdown(clean_text(text, noise_pattern), title)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(md, encoding="utf-8")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pdf", help="Path file PDF sumber")
    ap.add_argument("-o", "--out", required=True, help="Path markdown tujuan")
    ap.add_argument("--title", help="Judul dokumen (default: nama file PDF)")
    ap.add_argument(
        "--noise",
        default=DEFAULT_NOISE,
        help="Regex baris header/footer yang dibuang",
    )
    args = ap.parse_args()

    path = convert(args.pdf, args.out, args.title, args.noise)
    print(f"{path}: {len(Path(path).read_text(encoding='utf-8').splitlines())} baris")


if __name__ == "__main__":
    main()
