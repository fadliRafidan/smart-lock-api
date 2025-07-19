from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import psycopg2
from psycopg2 import sql

# --- KONFIGURASI DATABASE ---
DB_HOST = "localhost"
DB_NAME = "smart_lock_db"
DB_USER = "postgres"
DB_PASSWORD = "mysecretpassword"
DB_PORT = "5432"

app = FastAPI(
    title="Smart Device API (FastAPI)",
    description="API untuk mengontrol dan memantau status perangkat pintar.",
    version="2.0.0",
)

# Helper function untuk koneksi DB
def get_db_connection():
    try:
        return psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection error")

# Model untuk request body
class LockAction(BaseModel):
    new_status: str
    expected_version_id: int
    changed_by: str = "system"

# Kelas untuk interaksi database
class DeviceDB:
    def get_device(self, device_id: str):
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(sql.SQL("""
                SELECT id, name, type, status, version_id, updated_at
                FROM devices WHERE id = %s;
            """), (device_id,))
            result = cur.fetchone()
            if result:
                return {
                    "id": result[0],
                    "name": result[1],
                    "type": result[2],
                    "status": result[3],
                    "version_id": result[4],
                    "updated_at": result[5].isoformat()
                }
            return None
        finally:
            cur.close()
            conn.close()

    def update_status(self, device_id: str, new_status: str, expected_version_id: int, changed_by: str):
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # Dapatkan status lama untuk logging
            cur.execute("SELECT status FROM devices WHERE id = %s;", (device_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Device not found")
            previous_status = row[0]

            # Update status dengan optimistic locking
            cur.execute("""
                UPDATE devices
                SET status = %s, version_id = version_id + 1, updated_at = NOW()
                WHERE id = %s AND version_id = %s
                RETURNING version_id, updated_at;
            """, (new_status, device_id, expected_version_id))

            if cur.rowcount == 0:
                conn.rollback()
                current = self.get_device(device_id)
                raise HTTPException(status_code=409, detail={
                    "error": "Version conflict",
                    "current_status": current["status"],
                    "current_version_id": current["version_id"]
                })

            updated_version_id, updated_at = cur.fetchone()

            # Insert ke device_logs
            cur.execute("""
                INSERT INTO device_logs (device_id, previous_status, new_status, changed_by)
                VALUES (%s, %s, %s, %s);
            """, (device_id, previous_status, new_status, changed_by))

            conn.commit()
            return {
                "device_id": device_id,
                "status": new_status,
                "version_id": updated_version_id,
                "updated_at": updated_at.isoformat()
            }
        except HTTPException as e:
            raise e
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Database update error: {e}")
        finally:
            cur.close()
            conn.close()

# Inisialisasi DB handler
db = DeviceDB()

# Endpoint untuk mendapatkan status
@app.get("/device/{device_id}/status", summary="Dapatkan status perangkat")
async def get_device_status(device_id: str):
    device = db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

# Endpoint untuk update status
@app.post("/device/{device_id}/update", summary="Update status perangkat")
async def update_device_status(device_id: str, request_body: LockAction):
    return db.update_status(device_id, request_body.new_status, request_body.expected_version_id, request_body.changed_by)
