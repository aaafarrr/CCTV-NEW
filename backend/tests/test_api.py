import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import AsyncClient, ASGITransport
from app.main import app, startup_event
from app.services.cctv_engine import clospol_engine

async def run_suite():
    await startup_event()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health & Root
        r_health = await client.get("/health")
        assert r_health.status_code == 200

        # 2. Setup initial admin
        r_status = await client.get("/api/auth/status")
        assert r_status.status_code == 200

        # Setup root admin if not set
        if r_status.json()["needs_initial_setup"]:
            r_setup = await client.post("/api/auth/setup-admin", json={
                "username": "admin",
                "password": "AdminPassword123!",
                "full_name": "Security Chief",
                "email": "admin@cctv.local"
            })
            assert r_setup.status_code == 200
            token = r_setup.json()["access_token"]
        else:
            r_login = await client.post("/api/auth/login", data={"username": "admin", "password": "AdminPassword123!"})
            assert r_login.status_code == 200
            token = r_login.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create Camera (Clospol style)
        r_cam = await client.post("/api/cctv", headers=headers, json={
            "name": "Entrance Gate Lobby",
            "stream_url": "rtsp://192.168.1.100:554/live/ch0",
            "snapshot_url": "http://192.168.1.100/snapshot.jpg",
            "record_stream": True,
            "record_interval": 5,
            "retention_days": 14,
            "snapshot_headers": {}
        })
        assert r_cam.status_code == 200
        cam_id = r_cam.json()["camera_id"]

        # 4. List Cameras
        r_list = await client.get("/api/cctv", headers=headers)
        assert r_list.status_code == 200
        assert len(r_list.json()["cameras"]) >= 1

        # 5. Check Google Drive Status
        r_gdrive = await client.get("/api/google-drive/status", headers=headers)
        assert r_gdrive.status_code == 200
        assert "quota" in r_gdrive.json()

        # 6. Test Camera Gallery
        r_gallery = await client.get(f"/api/cctv/{cam_id}/gallery", headers=headers)
        assert r_gallery.status_code == 200
        assert "files" in r_gallery.json()

        print("ALL CLOSPOL CCTV & GOOGLE DRIVE TESTS PASSED SUCCESSFULLY!")
    clospol_engine.stop()

if __name__ == "__main__":
    asyncio.run(run_suite())
