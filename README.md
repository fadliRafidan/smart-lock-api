**Smart Lock API (FastAPI)**


## Tech Stack

**Server:** Python, FastApi, PostgreSQL



Sistem ini merupakan implementasi API untuk mengontrol dan memantau status Smart Lock dengan arsitektur yang mendukung Optimistic Locking untuk menjaga konsistensi data, bahkan dalam kondisi update bersamaan (concurrent).
Fitur Utama

✅ Mendapatkan status kunci perangkat (GET)

✅ Memperbarui status perangkat (POST)

✅ Mendukung Optimistic Locking

✅ Logging perubahan status (device_logs)

✅ Siap diuji secara lokal dengan pytest

✅ Dokumentasi interaktif melalui Swagger UI

Persyaratan Sistem

    Python 3.9+

    PostgreSQL 13+

    pip untuk manajemen dependensi

    Virtual environment (opsional, direkomendasikan)

## Struktur Proyek

smart-lock-api

- app.py                
- test_app.py           
- requirements.txt      
- README.md             


## Instalasi & Konfigurasi

Clone Repository

```bash
git clone https://github.com/fadliRafidan/smart-lock-api.git
```
```bash
cd smart-lock-api
```
Buat Virtual Environment (Rekomendasi)

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```
Install Dependensi
```bash
pip install -r requirements.txt
```
Siapkan Database

    Buat database smart_lock_db di PostgreSQL.

    Jalankan query untuk membuat tabel:

    CREATE EXTENSION IF NOT EXISTS "pgcrypto";

    CREATE TABLE devices (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name VARCHAR(100) NOT NULL,
        type VARCHAR(50) NOT NULL,
        status VARCHAR(50) NOT NULL DEFAULT 'unlocked',
        version_id INT NOT NULL DEFAULT 0,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE device_logs (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
        previous_status VARCHAR(50) NOT NULL,
        new_status VARCHAR(50) NOT NULL,
        changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        changed_by VARCHAR(50) NOT NULL
    );

Konfigurasi Koneksi Database
Edit variabel berikut di app.py:

    DB_HOST = "localhost"
    DB_NAME = "smart_lock_db"
    DB_USER = "postgres"
    DB_PASSWORD = "your_password"
    DB_PORT = "5432"

Menjalankan Aplikasi

    Jalankan server FastAPI:

    uvicorn app:app --reload --host 0.0.0.0 --port 8000

    Akses API melalui:

        Swagger UI: http://localhost:8000/docs



Endpoint Utama
```http
GET /device/{device_id}/status
```

Mendapatkan status perangkat.

Contoh Response:
```bash
{
  "id": "d56e6e42-bf24-4c5b-9085-6a5d4d28e5f1",
  "name": "Main Door Lock",
  "type": "smart-lock",
  "status": "locked",
  "version_id": 2,
  "updated_at": "2025-07-19T14:20:00Z"
}
```
```http
POST /device/{device_id}/update
```

Memperbarui status perangkat dengan Optimistic Locking.

Contoh Request:
```bash
{
  "new_status": "unlocked",
  "expected_version_id": 0,
  "changed_by": "user_1010"
}
```

Contoh Response:
```bash
{
  "device_id": "1b3f4bf7-e9ae-4a27-a0f4-d3dd58375225",
  "status": "unlocked",
  "version_id": 1,
  "updated_at": "2025-07-19T18:07:00.392044+00:00"
}
```
Pengujian Lokal

    Install pytest

pip install pytest

Jalankan pengujian:

    pytest

Fokus pengujian:

    Mendapatkan status perangkat.

    Update status dengan Optimistic Locking.

    Pengujian concurrent update.

    Perangkat tidak ditemukan (404).


## License

[MIT](https://choosealicense.com/licenses/mit/)

