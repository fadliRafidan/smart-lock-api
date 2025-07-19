import pytest
import threading
import time
from fastapi.testclient import TestClient as FastAPIClient
from app import app, get_db_connection, db
from psycopg2 import sql

# --- Fixtures untuk Setup/Teardown Database Testing ---

@pytest.fixture(scope='module')
def setup_database_module():
    """Fixture untuk menyiapkan database sekali per module/file test."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Kosongkan tabel sebelum test dimulai
        cur.execute(sql.SQL("TRUNCATE TABLE device_logs, devices RESTART IDENTITY CASCADE;"))
        conn.commit()
        print("Database truncated for module testing.")
        cur.close()
    except Exception as e:
        print(f"ERROR: Could not truncate database for testing: {e}")
        pytest.fail(f"Database setup failed: {e}")
    finally:
        if conn:
            conn.close()
    yield

@pytest.fixture
def test_client(setup_database_module):
    """
    Fixture untuk mengembalikan instance TestClient FastAPI.
    Pastikan device dengan UUID tetap tersedia.
    """
    device_id = '1b3f4bf7-e9ae-4a27-a0f4-d3dd58375225'  # UUID simulasi
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            sql.SQL("""
                INSERT INTO devices (id, name, type, status, version_id, updated_at)
                VALUES (%s, 'Room 101', 'door_lock', 'unlocked', 0, NOW())
                ON CONFLICT (id) DO UPDATE
                SET status = 'unlocked', version_id = 0, updated_at = NOW();
            """),
            (device_id,)
        )
        conn.commit()
        cur.close()
    except Exception as e:
        pytest.fail(f"Device initialization failed in test_client fixture: {e}")
    finally:
        if conn:
            conn.close()

    with FastAPIClient(app=app) as client:
        yield client

# --- Test Cases ---

def test_get_device_status(test_client):
    """Menguji endpoint GET /device/{device_id}/status."""
    device_id = "1b3f4bf7-e9ae-4a27-a0f4-d3dd58375225"
    response = test_client.get(f"/device/{device_id}/status")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["id"] == device_id
    assert json_data["status"] == "unlocked"
    assert "updated_at" in json_data
    assert "version_id" in json_data

def test_update_status_success(test_client):
    """Menguji endpoint POST /device/{device_id}/update untuk update status."""
    device_id = "1b3f4bf7-e9ae-4a27-a0f4-d3dd58375225"
    # Ambil version_id terkini
    current_version_id = db.get_device(device_id)["version_id"]
    response = test_client.post(
        f"/device/{device_id}/update",
        json={"new_status": "locked", "expected_version_id": current_version_id, "changed_by": "tester"}
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "locked"
    assert json_data["version_id"] == current_version_id + 1

def test_concurrent_updates(test_client):
    """
    Simulasikan dua update bersamaan: keduanya mencoba mengganti status menjadi 'unlocked'.
    Harusnya satu sukses, satu gagal (409).
    """
    device_id = "1b3f4bf7-e9ae-4a27-a0f4-d3dd58375225"
    results = []

    def send_update_in_thread():
        with FastAPIClient(app=app) as client_thread:
            time.sleep(0.01 + threading.current_thread().ident % 5 / 1000)
            current_version_id = db.get_device(device_id)["version_id"]
            response = client_thread.post(
                f"/device/{device_id}/update",
                json={"new_status": "unlocked", "expected_version_id": current_version_id, "changed_by": "thread"}
            )
            results.append({"status_code": response.status_code, "json": response.json()})

    t1 = threading.Thread(target=send_update_in_thread)
    t2 = threading.Thread(target=send_update_in_thread)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    success_count = sum(1 for r in results if r["status_code"] == 200)
    conflict_count = sum(1 for r in results if r["status_code"] == 409)

    assert success_count == 1, f"Expected 1 success, got {success_count}"
    assert conflict_count == 1, f"Expected 1 conflict, got {conflict_count}"

def test_device_not_found(test_client):
    """Menguji kasus perangkat tidak ditemukan."""
    device_id = "00000000-0000-0000-0000-000000000000"
    response = test_client.get(f"/device/{device_id}/status")
    assert response.status_code == 404
    assert response.json()["detail"] == "Device not found"

    response = test_client.post(
        f"/device/{device_id}/update",
        json={"new_status": "locked", "expected_version_id": 0, "changed_by": "tester"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Device not found"
