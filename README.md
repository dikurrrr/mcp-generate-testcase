# MCP Generate Testcase

Repository ini berisi alat otomatisasi pembuatan test case dari dokumen POC (Proof of Concept).

## Tujuan

Membantu pengembang dan QA menghasilkan test case terstruktur dari dokumen POC (Proof of Concept) dalam format markdown, JSON, atau CSV. Generator ini diekstrak aturan dari konten POC (seperti batas nilai, ketentuan "wajib"/"harus", pesan validasi, dan lainnya) dan mengubahnya menjadi test case yang bisa langsung digunakan.

## Arsitektur Saat Ini

Repository ini dikonsolidasikan menjadi **satu generator utama** (`tools/combined_generator.py`) yang menggantikan beberapa script lama:

- `tools/generate_batch.py` → Digantikan oleh `combined_generator.py`
- `generated-testcases/generate_csv.py` → Digantikan oleh `combined_generator.py`
- `generated-testcases/generate-200-testcases.py` → Digantikan oleh `combined_generator.py`

File-file lama dipindahkan ke folder `legacy/` untuk referensi belakang compatibilitas.

## Fitur Utama

- **Generate Test Case dari POC**: Membaca file `.md`/`.txt` dan menghasilkan test case berdasarkan rule-engine
- **3 Format Output**: CSV (dengan kolom `steps` berformat berurutan), JSON, dan Markdown
- **Bahasa Indonesia**: Opsi label bahasa Indonesia (`--lang id`)
- **Timestamp di Nama File**: Nama file CSV mencakup tanggal pembuatan (`all-testcases-2026-11-12.csv`)
- **Tracking Dokument**: Setiap test case mencakup field `document` menunjuk ke file POC asal
- **Kontrol Jumlah**: Parameter `--total` untuk membatasi jumlah test case yang dihasilkan

## Struktur Folder

```
mcp-generate-testcase/
├── legacy/              # File lama (disimpan untuk referensi)
│   ├── generate_batch.py
│   ├── generate_csv.py
│   └── generate-200-testcases.py
├── tools/
│   ├── combined_generator.py   # Generator utama (1 file gabungan)
│   ├── ocr_pdf.swift         # Helper OCR PDF scan (macOS Vision)
│   └── pdf_to_poc.py         # Konversi PDF → markdown POC
├── generated-testcases/   # Output test case (CSV/JSON/MD)
├── docs/                # Folder dokumen POC
├── generator.py         # Modul inti (dipakai combined_generator.py)
├── parser.py            # Modul baca POC
├── requirements.txt
└── README.md
```

## Cara Pakai

### Generate Test Case

```bash
# English (default)
python3 tools/combined_generator.py --total 10

# Bahasa Indonesia
python3 tools/combined_generator.py --total 10 --lang id

# Generate minimal 200 test case dari file POC tertentu
python3 tools/combined_generator.py --min-200 \
  --poc-files "doc1.md" "doc2.md"
```

### Output yang Dihasilkan

Setiap eksekusi menghasilkan 3 file di `generated-testcases/`:
- `all-testcases{x}.{en,id}.md` - Format baca Markdown
- `all-testcases{x}.{en,id}.json` - Format JSON lengkap
- `all-testcases{x}.{en,id}.csv` - Format CSV (11 kolom E, 9 kolom I)

Contoh CSV (English):
```csv
id,title,document,category,priority,kind,precondition,steps,expected_result,source_section,tags
TC-001,"Test aturan: Aplikasi harus...","01-requisition-approval-bidding","exception","high","rule","Precondition text","1. Siapkan kondisi...","Sistem berperilaku...","Fitur, exception, rule-sentence"
```

Contoh CSV (Indonesia):
```csv
ID,Judul,Kategori,Prioritas,Prasyarat,Langkah,Hasil yang Diharapkan,Sumber Section,Tag
TC-001,"Test aturan: Aplikasi harus...","exception","medium","Form...","1. Siapkan kondisi...","Sistem menolak...","Fitur, exception, rule-sentence"
```

### Konversi PDF ke POC

```bash
python3 tools/pdf_to_poc.py <file.pdf> -o docs/<file>.md --title "<Judul>"
```

Atau gunakan helper Swift:
```bash
swift tools/ocr_pdf.swift <file.pdf> /tmp/output.txt
```

### Generate dari File POC Tertentu (mode --min-200)

```bash
python3 tools/combined_generator.py --min-200 \
  --poc-files "CODE_FIXES_SUMMARY.md" "README.md"
```

## File yang Sudah Ada

- `generated-testcases/` - Berisi hasil generate dari eksekusi sebelumnya
- `legacy/` - File lama yang masih dapat diakses untuk referensi
- `docs/` - Folder kosong menanti dokumen POC user

## Dependencies

Lihat `requirements.txt` untuk daftar library yang diperlukan.

## Kontribusi

1. Fork repository
2. Buat branch fitur
3. Commit perubahan
4. Push ke branch
5. Buat Pull Request
