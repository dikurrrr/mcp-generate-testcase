# POC: API Gateway Authentication

## Fungsi Utama
Sistem harus melakukan autentikasi melalui API key untuk setiap request.
- User harus memiliki valid API key
- Setiap request harus menyertakan header Authorization
- Token kedaluarsa harus ditolak

## Batasan Performance
Maksimal 100 request per menit untuk endpoint tertentu.
- Maksimal 50 koneksi simultan
- Timeout 30 deti untuk response

## Penanganan Error
Sistem harus menangani error ketika input invalid.
- Request dengan API key tidak valid ditolak
- Request tanpa otorisasi menampilkan error 401
- Timeout koneksi ditangkap dengan baik

## Integrasi dengan Service Lain
Sinkronisasi data ke service user management.
- Endpoint: /api/v1/users
- Method: POST
- Harus sinkron user ke service lain dengan status 201
