# MCP Generate Testcase

**MCP Generate Testcase** adalah server MCP (Model Context Protocol) yang mengotomatisasi pembuatan test case dari dokumen Proof of Concept (POC). Alat ini menganalisis struktur dokumen POC dan menghasilkan test case yang terstruktur dengan kategori, prioritas, langkah eksekusi, dan hasil yang diharapkan.

## Fitur

- **Parsing POC Document**: Baca dan parse file markdown/txt menjadi struktur section hierarkis
- **Generasi Test Case Otomatis**: Generate test case berdasarkan rule-engine dengan 4 kategori:
  - `functional` - Test fitur umum
  - `boundary` - Test batas input/range
  - `exception` - Test handling error/exception
  - `integration` - Test integrasi antar service/API
- **Ekstraksi Aturan**: Selain template generic, generator menarik aturan konkret dari teks POC:
  - batas angka (`min. 3, maks. 120 karakter`, `Qty ≥ 1`, `maks 10 MB`) → test case batas bawah/atas dan pelanggarannya
  - pesan validasi yang dikutip (`"Judul minimal 3 karakter."`) → test case negatif dengan ekspektasi pesan persis
  - kalimat aturan (`wajib`, `harus`, `tidak boleh`, `hanya`, `otomatis`) → test case positif + negatif
  - endpoint (`POST /api/...`) → test case integrasi, dan opsi mode (`default X … atau Y`) → test case per opsi
  - Setiap test case punya penanda `kind`: `rule` (hasil ekstraksi) atau `generic` (template)
- **Prioritas Test Case**: Auto-determine prioritas (high, medium, low) berdasarkan keyword
- **Multiple Output Format**: Support JSON, Markdown, dan Table format
- **Keyword Extraction**: Otomatis ekstrak keyword dari konten section untuk title dan tags
- **MCP Server Protocol**: Siap untuk diintegrasikan ke dalam sistem MCP/aplikasi lain

## Instalasi

```bash
# Clone repository
git clone https://github.com/dikurrrr/mcp-generate-testcase.git

# Masuk ke direktori
cd mcp-generate-testcase

# Install dependencies
pip install -r requirements.txt
```

## Penggunaan

### Jalankan Server MCP

```bash
python server_adv_testcase.py
```

Server akan berjalan melalui STDIO dan siap menerima perintah MCP.

### Dari Kode/Python

```python
from parser import read_poc_document
from generator import generate_testcases_with_format

# Baca file POC
doc = read_poc_document("./docs/sample-poc.md")

# Generate test case (format markdown)
result = generate_testcases_with_format(doc, max_per_section=3, fmt="markdown")
print(result)
```

### Via MCP Tools

Server menawarkan 3 tools yang bisa dipanggil:

1. **`read_poc_document`** - Baca dan parse file POC
   - `file_path`: Path ke file POC (misal: `./docs/poc-api-gateway.md`)

2. **`generate_testcases`** - Generate test case dari dokumen POC
   - `file_path`: Path ke file POC
   - `max_per_section`: Maksimal test case per section (default: 3)
   - `output_format`: Format output (`json`, `markdown`, `table`, default: `markdown`)

3. **`list_poc_documents`** - List file POC di directory
   - `directory`: Directory yang akan di-scan (default: `./docs`)

### Konversi PDF ke POC

Server ini hanya membaca file teks (`.md`/`.txt`), jadi PDF/dokumen requirement
harus dijadikan markdown dulu:

```bash
python tools/pdf_to_poc.py 01-requisition-approval-bidding-1.pdf \
    -o docs/01-requisition-approval-bidding.md \
    --title "POC: Requisition, Approval, sampai Bidding"
```

Heading dideteksi dari penomoran berurutan di dokumen (`1. Judul` → `## Judul`,
`4.2 Judul` → `### Judul`). Baris header/footer berulang dibuang lewat
`--noise` (regex, default menangani footer "Savinix — …" dan "Halaman x / y").

### Generate Semua Dokumen ke Satu File

Untuk menggabungkan hasil seluruh POC di `docs/` menjadi satu set output
(markdown, JSON, dan CSV):

```bash
python tools/generate_batch.py                 # semua test case apa adanya
python tools/generate_batch.py --total 200     # dipangkas/dilengkapi tepat 200
```

Menghasilkan `generated-testcases/all-testcases.{md,json,csv}`. Test case
hasil ekstraksi aturan (`kind=rule`) diprioritaskan; template generic hanya
dipakai untuk melengkapi sampai `--total` terpenuhi. ID dirapikan ulang
berurutan lintas dokumen (TC-001…TC-200), karena tiap dokumen memulai
hitungan dari TC-001.

Kolom CSV: `id, title, document, category, priority, kind, precondition,
steps, expected_result, source_section, tags`. Kolom `steps` berisi satu
langkah per baris di dalam satu sel (field di-quote sesuai standar CSV) —
aktifkan "Wrap Text" di Excel/Google Sheets supaya terbaca penuh.

Batas jumlah test case hasil ekstraksi per section diatur lewat konstanta di
`generator.py`: `MAX_RULES_PER_SECTION`, `MAX_OBLIGATIONS_PER_SECTION`,
`MAX_MESSAGES_PER_SECTION`, `MAX_ACTIONS_PER_SECTION`, `MAX_ENUMS_PER_SECTION`.

### Contoh File POC

```markdown
# POC: API Gateway Authentication

## Fitur Utama

User harus melakukan login sebelum mengakses endpoint tertentu.
Sistem akan menolak akses jika token expired.

## Endpoint Auth

POST /api/auth/login
- Request: username dan password
- Response: JWT token
```

## Output Hasil

Test case akan dihasilkan dengan struktur berikut:

```markdown
# Test Test API Gateway Authentication - scenario 1 (login)

## Precondition
User telah login / sistem dalam kondisi ready (ref: sample-poc)

## Steps
- Siapkan lingkungan yang sesuai dengan syarat: login
- Akses modul/layanan terkait 'login'
- Jalankan operasi: login
- Verifikasi output sesuai dengan spesifikasi POC

## Expected Result
Sistem menghasilkan output yang sesuai dengan spesifikasi POC, tanpa error.

## Priority
medium

## Source Section
Fitur Utama

## Tags
- login
- functional
- sample-poc
```

## Struktur Project

```
mcp-generate-testcase/
├── __init__.py      # Package init
├── CODE_FIXES_SUMMARY.md  # Ringkasan perbaikan (ter-ignore di .gitignore)
├── __pycache__      # Folder cache Python (ter-ignore di .gitignore)
├── docs/            # Dokumen POC (markdown hasil konversi/penulisan manual)
├── generated-testcases/  # Hasil generate test case
├── generator.py     # Logika generate test case
├── parser.py        # Logika parse POC document
├── server_adv_testcase.py  # MCP Server entry point
├── templates.py     # Format output Testcase
├── tools/
│   ├── pdf_to_poc.py  # Konversi PDF requirement menjadi markdown POC
│   └── generate_batch.py  # Semua POC → satu file md/json/csv
├── requirements.txt # Dependencies
├── .gitignore       # Ignore pycache dan summary files
└── README.md        # Dokumentasi ini
```

## Dependencies

Lihat `requirements.txt` untuk daftar library yang diperlukan. Library utama meliputi `mcp-server` untuk protokol MCP.

## Kontribusi

1. Fork repository
2. Buat branch fitur (`git checkout -b fitur-baru`)
3. Commit perubahan (`git commit -m 'Menambahkan fitur X'`)
4. Push ke branch (`git push origin fitur-baru`)
5. Buat Pull Request