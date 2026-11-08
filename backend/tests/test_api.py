import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import AsyncClient, ASGITransport
from app.main import app, startup_event
from app.services.camera_stream import stream_manager

async def run_suite():
    await startup_event()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Check initial setup status (should need setup on clean slate)
        r_status = await client.get("/api/v1/auth/status")
        assert r_status.status_code == 200, r_status.text
        assert r_status.json()["needs_initial_setup"] is True

        # 2. Complete First-Time Setup: Register Root Admin
        r_setup = await client.post("/api/v1/auth/setup-admin", json={
            "username": "admin",
            "password": "AdminPassword123!",
            "full_name": "Chief Security Officer",
            "email": "cso@enterprise.local"
        })
        assert r_setup.status_code == 200, r_setup.text
        token = r_setup.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Verify System is now configured (setup locked)
        r_status2 = await client.get("/api/v1/auth/status")
        assert r_status2.json()["needs_initial_setup"] is False
        r_setup_locked = await client.post("/api/v1/auth/setup-admin", json={
            "username": "hacker",
            "password": "Password123!",
            "full_name": "Hacker",
            "email": "h@h.com"
        })
        assert r_setup_locked.status_code == 400

        # 4. Strict RBAC: 401 without token, 200 with admin token
        r_unauth = await client.get("/api/v1/auth/users")
        assert r_unauth.status_code == 401
        r_users = await client.get("/api/v1/auth/users", headers=headers)
        assert r_users.status_code == 200
        assert len(r_users.json()) == 1

        # 5. Create Operator User
        r_create_op = await client.post("/api/v1/auth/users", headers=headers, json={
            "username": "operator1",
            "password": "OperatorPass123!",
            "full_name": "Operator Room 1",
            "email": "op1@enterprise.local",
            "role": "OPERATOR"
        })
        assert r_create_op.status_code == 200

        # Operator Login
        r_op_login = await client.post("/api/v1/auth/login", data={"username": "operator1", "password": "OperatorPass123!"})
        assert r_op_login.status_code == 200
        op_token = r_op_login.json()["access_token"]
        op_headers = {"Authorization": f"Bearer {op_token}"}

        # Operator forbidden on admin-only route
        r_op_forbidden = await client.post("/api/v1/auth/users", headers=op_headers, json={
            "username": "op2",
            "password": "Password123!",
            "full_name": "Op 2",
            "email": "op2@local",
            "role": "OPERATOR"
        })
        assert r_op_forbidden.status_code == 403

        # 6. Camera Management (Clean Slate = 0 cameras)
        r_cams = await client.get("/api/v1/cameras", headers=headers)
        assert r_cams.status_code == 200
        assert len(r_cams.json()) == 0

        # Add Real RTSP Camera
        r_add_cam = await client.put("/api/v1/cameras/cam_main", headers=headers, json={
            "name": "Lobby Entrance Gate",
            "location": "Building A - Ground Floor",
            "stream_url": "rtsp://admin:securepass@192.168.1.50:554/live/ch0",
            "enable_counting": True,
            "enable_suspicious": True,
            "enable_face_rec": True,
            "roi_zones": [],
            "counting_lines": []
        })
        assert r_add_cam.status_code == 200

        # Check list & password masking
        r_cams_after = await client.get("/api/v1/cameras", headers=headers)
        assert len(r_cams_after.json()) == 1
        cam_item = r_cams_after.json()[0]
        assert "stream_url_masked" in cam_item
        assert "securepass" not in cam_item["stream_url_masked"]

        # 7. S3 Cloud Gateway Policy
        r_storage = await client.get("/api/v1/storage/overview", headers=headers)
        assert r_storage.status_code == 200
        assert "s3_configured" in r_storage.json()

        # Update S3 Policy
        r_policy = await client.put("/api/v1/storage/policy", headers=headers, json={
            "s3_bucket": "production-nvr-vault",
            "s3_endpoint_url": "https://s3.ap-southeast-1.amazonaws.com",
            "s3_region": "ap-southeast-1",
            "s3_prefix": "cctv-enterprise",
            "local_retention_days": 14,
            "cloud_retention_days": 180,
            "auto_sync_critical_events": True
        })
        assert r_policy.status_code == 200

        # 8. Rate Limiting Protection (failed login threshold)
        for _ in range(5):
            await client.post("/api/v1/auth/login", data={"username": "admin", "password": "WrongPassword!"})
        r_locked = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "WrongPassword!"})
        assert r_locked.status_code == 429

        print("ALL PRODUCTION BACKEND TESTS PASSED CLEANLY (Zero Dummy Data, Real First-Time Setup, Strict Security)!")
    stream_manager.stop_all()

if __name__ == "__main__":
    asyncio.run(run_suite())
