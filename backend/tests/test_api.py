import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app, startup_event
from app.services.camera_stream import stream_manager

async def run_suite():
    await startup_event()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Verify Strict JWT Auth Enforcement (401 without token)
        r_unauth = await client.get("/api/v1/auth/users")
        assert r_unauth.status_code == 401, f"Expected 401 without token, got {r_unauth.status_code}"

        r_unauth_mut = await client.post("/api/v1/storage/sync", json={"camera_name": "Cam 1", "reason": "Test"})
        assert r_unauth_mut.status_code == 401, f"Expected 401 on protected mutation, got {r_unauth_mut.status_code}"

        # 2. Login as Admin (SQLite User persistence)
        r_login = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
        assert r_login.status_code == 200, r_login.text
        token = r_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r_users = await client.get("/api/v1/auth/users", headers=headers)
        assert r_users.status_code == 200 and len(r_users.json()) >= 2

        # 3. Verify Operator RBAC restriction on Admin-only user creation
        r_op_login = await client.post("/api/v1/auth/login", data={"username": "operator", "password": "operator123"})
        op_token = r_op_login.json()["access_token"]
        r_forbidden = await client.post(
            "/api/v1/auth/users",
            headers={"Authorization": f"Bearer {op_token}"},
            json={"username": "tempuser", "password": "password123", "full_name": "Temp", "email": "t@c.local", "role": "VIEWER"}
        )
        assert r_forbidden.status_code == 403, f"Expected 403 for operator creating user, got {r_forbidden.status_code}"

        # 4. Cameras, PTZ, Timeline & V380 Discovery
        r_cams = await client.get("/api/v1/cameras")
        assert r_cams.status_code == 200 and len(r_cams.json()) >= 4

        r_ptz = await client.post("/api/v1/cameras/cam_1/ptz", json={"action": "zoom_in", "step": 0.2})
        assert r_ptz.status_code == 200 and r_ptz.json()["ptz"]["zoom"] > 1.0

        r_tl = await client.get("/api/v1/cameras/cam_1/timeline")
        assert r_tl.status_code == 200 and len(r_tl.json()["bands"]) >= 4

        r_v380 = await client.get("/api/v1/cameras/discover/v380")
        assert r_v380.status_code == 200 and len(r_v380.json()["devices"]) >= 2

        # 5. Security Boundary Checks (SSRF & Path Traversal)
        r_ssrf = await client.put(
            "/api/v1/cameras/cam_1",
            headers=headers,
            json={"name": "Test", "location": "Loc", "stream_url": "file:///etc/passwd"}
        )
        assert r_ssrf.status_code == 400

        r_trav = await client.get("/api/v1/cameras/snapshots/download/..%2Fconfig.py")
        assert r_trav.status_code in (400, 404)

        # 6. Simulate & Persist Fall Detection (DeepCamera Skill)
        r_fall = await client.post(
            "/api/v1/alerts/simulate",
            headers=headers,
            json={"event_type": "FALL_DETECTED", "camera_id": "cam_1"}
        )
        assert r_fall.status_code == 200 and r_fall.json()["event_type"] == "FALL_DETECTED"

        r_alerts = await client.get("/api/v1/alerts")
        assert r_alerts.status_code == 200
        assert any(a["event_type"] == "FALL_DETECTED" for a in r_alerts.json())

        # 7. Faces & Multi-Cloud Storage Pool
        r_faces = await client.get("/api/v1/faces/people-clusters")
        assert r_faces.status_code == 200 and len(r_faces.json()) >= 4

        r_sync = await client.post(
            "/api/v1/storage/sync",
            headers=headers,
            json={"camera_name": "Cam 1", "reason": "Automated Suite"}
        )
        assert r_sync.status_code == 200 and r_sync.json()["status"] == "COMPLETED"

        print("ALL AUTOMATED TESTS PASSED (Auth 401/403 RBAC, SQLite Users/Events, Fall Detection, V380, Qdrant, Cloud Pool)!")
    stream_manager.stop_all()

if __name__ == "__main__":
    asyncio.run(run_suite())
