# CCTV NEW — Enterprise AI Surveillance & Multi-Cloud NVR

Aplikasi Pemantauan CCTV Tingkat Produksi yang mengintegrasikan sintesis dari 8 proyek referensi (`VisionGuard AI`, `Frigate`, `CCTV-v380-pro`, `V380-Web`, `ClearCam`, `DeepCamera`, `ZoneMinder`, dan `Clospol`) dengan antarmuka **Clean Enterprise Light Mode** berbasis **Ant Design**.

---

## Fitur Utama

1. **Dashboard Operasional & Analitik Real-Time**:
   - Pemantauan metrik Foot Traffic (Pejalan Kaki), Klasifikasi Kendaraan (Mobil, Motor, Truk, Bus), dan Kesehatan Kamera.
2. **Live Multi-Cam Grid (1x1, 2x2, 3x3, 4x4) + Quick PTZ & Timeline Scrubber**:
   - Kontrol Pan, Tilt, dan Digital Zoom interaktif.
   - Overlay AI Bounding Box & ROI Polygon (Intrusion `#ef4444`, Loitering `#f59e0b`, Person `#10b981`, Vehicle `#8b5cf6`).
   - **Incident Timeline Scrubber 24-Jam** dengan pita warna kejadian & Pre-Alarm Circular Buffer (~5 detik).
3. **People Gallery & Google Photos-Style Face Vector Search (Qdrant 512-d)**:
   - Pencarian kemiripan wajah kosinus 512-dimensi dengan unggah foto (dilengkapi sampel uji cepat & fallback Qdrant in-memory).
4. **Events & Incidents Log + AI Narrative Summary**:
   - Log kejadian keamanan lengkap dengan ringkasan kalimat AI otomatis (ClearCam/VLM style) & fitur Export CSV.
5. **Multi-Cloud Storage Pool & Auto-Tiering Gateway (Clospol Engine)**:
   - Penggabungan Local NVMe Rolling Buffer dengan Google Drive, Microsoft OneDrive, dan AWS S3 / Cloudflare R2.
6. **V380 UDP Network Scanner & RTSP Unlocker Guide**:
   - Pemindai kamera lokal V380 (`NVDEVSEARCH^100` pada UDP port `10008 -> 10009`) beserta panduan patch MicroSD `V380-Web`.

---

## Cara Menjalankan

### 1. Menjalankan Backend (FastAPI)
```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```
Dokumentasi API Swagger tersedia di: `http://localhost:8000/docs`

### 2. Menjalankan Frontend (React + Vite + Ant Design)
```powershell
cd frontend
npm run dev
```
Buka browser di: `http://localhost:3000`

### Akun Login Default
- **Administrator**: `admin` / `admin123`
- **Operator**: `operator` / `operator123`
