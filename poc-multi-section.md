# POC: User Management System

## Fungsi Utama
User harus login sebelum mengakses fitur lain.
Sistem harus menvalidasi input nama lengkap.

## Batasan Performance
Maksimal 50 user simultan.
Timeout 60 deti untuk response API.

## Penanganan Error
Sistem harus menangani error ketika input invalid.
- Username kosong menampilkan error
- Password salah menampilkan pesan kesalahan
- User tidak ditemukan menampilkan error 404

## Integrasi dengan Service Lain
Sinkronisasi ke service keuangan.
- Endpoint: /api/v1/balance
- Method: GET
- Harus mengembalikan saldo akurat
