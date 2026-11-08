# MEMORY REPOSITORY REFERENSI CCTV NEW

Dokumen ini merupakan ringkasan pengetahuan, arsitektur, kapabilitas, dan analisis integrasi dari seluruh proyek referensi yang telah dipelajari di folder `CCTV REFF PROJECT`.

---

## 1. Ikhtisar Proyek Referensi

| # | Nama Proyek | Bahasa / Stack Utama | Fokus Utama | Nilai Manfaat untuk `CCTV NEW` |
|---|---|---|---|---|
| 1 | **[VisionGuard AI (CCTV)](file:///d:/Project/CCTV%20NEW/CCTV%20REFF%20PROJECT/CCTV)** | Python (FastAPI), React + Vite (TS), Qdrant Vector DB, YOLOv11 + ByteTrack, InsightFace | Full-stack CCTV NVR Modern siap pakai: Face Vector Search (Google Photos-style), Traffic Counting & Anomaly Detection (Intrusion/Loitering) | **Fondasi Fullstack Utama**: Arsitektur end-to-end lengkap (FastAPI + React Vite), sistem vektor wajah 512-d dengan Qdrant DB (termasuk fallback in-memory), pipeline ByteTrack + YOLOv11, persistent camera config JSON/PostgreSQL. |
| 2 | **[frigate](file:///d:/Project/CCTV%20NEW/CCTV%20REFF%20PROJECT/frigate)** | Python, Go (go2rtc), Vue.js / TypeScript | NVR Produksi Real-time + AI Detector (Coral TPU, OpenVINO, TensorRT) | Arsitektur pipeline video kecepatan tinggi, integrasi engine streaming go2rtc (WebRTC/MSE), optimasi deteksi hanya saat ada gerak, sistem recording & retention. |
| 3 | **[dunderhay/CCTV-v380-pro](file:///d:/Project/CCTV%20NEW/CCTV%20REFF%20PROJECT/CCTV-v380-pro)** | Python, Shell, Network Protocol Reverse-engineering | Protokol V380 Pro, Discovery UDP, Autentikasi Cloud / P2P | Script discovery kamera lokal (`discover-cam-on-network/findcam.py`), handshake paket binary/UDP broadcast (`NVDEVSEARCH^100`), bypass cloud V380. |
| 4 | **[Arkady23/V380-Web](file:///d:/Project/CCTV%20NEW/CCTV%20REFF%20PROJECT/V380-Web)** | C, Shell, HTML/JS Embedded | Custom Web Server & RTSP Enabler untuk Kamera V380 (via SD Card) | Cara membuka stream RTSP murni dari kamera V380 langsung melalui modifikasi SD Card/patch lokal tanpa ketergantungan cloud vendor. |
| 5 | **[SharpAI/DeepCamera](file:///d:/Project/CCTV%20NEW/CCTV%20REFF%20PROJECT/DeepCamera)** | Python, C++, ONNX, PyTorch, Docker | AI Surveillance Skills: VLM, Face Recognition, Person Re-ID, Fall Detection | Ekosistem modular AI Vision tingkat lanjut, edge inference, multimodal scene understanding menggunakan local LLM/VLM. |
| 6 | **[ZoneMinder/zoneminder](file:///d:/Project/CCTV%20NEW/CCTV%20REFF%20PROJECT/zoneminder)** | C++, PHP, Perl, JavaScript | Sistem Surveillance & CCTV NVR enterprise matang | Logika zone masking, motion detection thresholding, multi-camera management, arsitektur buffer circular di POSIX shared memory (`mmap`). |
| 7 | **[roryclear/clearcam](file:///d:/Project/CCTV%20NEW/CCTV%20REFF%20PROJECT/clearcam)** | Python, Ultralytics YOLO, OpenCV, FastAPI/Web | NVR cerdas modern, Object Tracking (OC-SORT), AI Event Summaries (LLM), Mobile Notifications | Integrasi YOLO + OC-SORT tracking, peringatan cerdas ringkas berbasis LLM, pipeline Python yang bersih & mudah diadopsi. |
| 8 | **[aaafarrr/Clospol](file:///d:/Project/CCTV%20NEW/CCTV%20REFF%20PROJECT/Clospol)** | TypeScript, Next.js 15, Drizzle ORM, SQLite, S3/Cloud APIs | Multi-Cloud Storage Pooling Gateway | Menyatukan penyimpanan rekaman CCTV ke multiple cloud (Google Drive, OneDrive, S3/R2/MinIO) dengan auto-tiering & archiving hemat biaya. |

---

## 2. Analisis Mendalam Tiap Proyek

### 1. VisionGuard AI (`CCTV`) — *Primary Base Foundation*
* **Arsitektur & Komponen**:
  - **Backend**: FastAPI (`app/main.py`), threading worker untuk kamera (`camera_stream.py`), modular AI engine (`services/ai/detector.py`, `counting.py`, `anomaly.py`, `face_engine.py`).
  - **Vector Database**: Qdrant Vector DB dengan embedding InsightFace ArcFace (512-dimensi Cosine Distance). Hebatnya, memiliki fallback otomatis ke mode `QdrantClient(":memory:")` jika server Qdrant standalone tidak terpasang.
  - **AI Engines**:
    - `detector.py`: YOLOv11 + ByteTrack untuk tracking objek terus-menerus.
    - `counting.py`: Cross-line counting (orang & klasifikasi kendaraan: motor, mobil, bus, truk) dengan zona ROI polygon.
    - `anomaly.py`: Intrusion Detection pada area terlarang & Loitering Detection (berdiam diri melebihi batas waktu aman).
    - `face_engine.py`: SCRFD Face Detection + InsightFace embedding extractor.
  - **Frontend**: React + Vite + Tailwind CSS (`frontend/src`), dilengkapi halaman Dashboard, Live View Grid, Events Log, Face Gallery (People clustering), Face Search Modal (Google Photos style), Analytics Chart, dan Settings.
* **Pelajaran untuk CCTV NEW**: Sangat cocok menjadi kerangka dasar / baseline sistem `CCTV NEW` karena sudah full-stack, modular, dan memiliki integrasi backend-frontend yang rapi.

---

### 2. Frigate NVR (`blakeblackshear/frigate`)
* **Arsitektur**:
  - Menggunakan **go2rtc** sebagai streaming hub (mendukung RTSP, WebRTC, MSE, HLS).
  - **Dua Tingkat Deteksi**: Deteksi gerak berbasis CPU resolusi rendah (motion detection) menentukan *bounding box*, baru kemudian frame dikirim ke model deteksi objek (TensorFlow Lite, OpenVINO, TensorRT, Coral TPU) untuk menghemat komputasi.
  - Multi-process multiprocessing di Python untuk menghindari batasan GIL.
* **Pelajaran untuk CCTV NEW**: Adopsi streaming go2rtc untuk WebRTC low-latency streaming dan teknik motion pre-filtering sebelum AI inference agar CPU tidak overload.

---

### 3. CCTV-v380-pro & V380-Web (`dunderhay/CCTV-v380-pro` & `Arkady23/V380-Web`)
* **Masalah pada Kamera V380**:
  - Kamera V380/V380 Pro mengunci stream di aplikasi bawaan dan menyulitkan akses RTSP standar.
* **Solusi dari Referensi**:
  - **Discovery**: Skrip di `CCTV-v380-pro/scripts/discover-cam-on-network/findcam.py` membongkar packet discovery UDP broadcast:
    - Broadcast payload heksadesimal `NVDEVSEARCH^100` (`4e564445565345415243485e313030...`) ke port `255.255.255.255:10008`.
    - Kamera merespons ke port UDP `10009` berisi identitas hardware, IP, dan device ID.
  - **RTSP Hack / Custom Web Service**: `V380-Web` menyediakan patch yang dipasang pada MicroSD card kamera tanpa perlu solder UART/chip flashing. Patch ini mengaktifkan daemon RTSP lokal (`rtsp://ip:554/live/ch0`).
* **Pelajaran untuk CCTV NEW**: Integrasi auto-scanner V380 di LAN dan petunjuk setup unlock RTSP ke dashboard settings.

---

### 4. ClearCam (`roryclear/clearcam`)
* **Arsitektur**:
  - Pipeline: Video Capture -> Motion / Object Detection (YOLO) -> Tracking (OC-SORT) -> Event Aggregator -> LLM Summary -> Notification.
* **Pelajaran untuk CCTV NEW**: Notifikasi kejadian cerdas berbentuk kalimat ringkasan naratif bertenaga AI/LLM.

---

### 5. DeepCamera (`SharpAI/DeepCamera`)
* **Arsitektur**:
  - Modular skill engine: VLM scene analysis, Face Recognition, Person Re-Identification (Re-ID), Fall Detection.
* **Pelajaran untuk CCTV NEW**: Analitik lanjutan seperti deteksi orang jatuh (fall detection) dan Re-ID lintas kamera.

---

### 6. ZoneMinder (`ZoneMinder/zoneminder`)
* **Arsitektur**:
  - Backend C++ dengan performa tinggi untuk penanganan frame circular buffer di RAM (`mmap` / POSIX Shared Memory).
  - Model Monitoring Zone: Active, Inclusive, Exclusive, Pre-alarm buffer.
* **Pelajaran untuk CCTV NEW**: Konsep pengaturan Zona Pantau (Motion Zones) dan circular buffer untuk merekam beberapa detik *sebelum* kejadian terdeteksi (pre-event buffer).

---

### 7. Clospol (`aaafarrr/Clospol`)
* **Arsitektur**:
  - Next.js 15 + TypeScript + Drizzle ORM + Multi-provider Cloud Storage Gateway.
* **Pelajaran untuk CCTV NEW**: Manajemen *storage tiering* (rekaman live di disk lokal, lalu video event klip otomatis di-backup ke Google Drive / OneDrive / S3 gratis).

---

## 3. Blueprint Arsitektur CCTV NEW (Sintesis Semua Referensi)

```
+-----------------------------------------------------------------------------------+
|                                 CCTV NEW SYSTEM                                   |
+-----------------------------------------------------------------------------------+
|  [ Ingestion & Discovery Layer ]                                                  |
|  - RTSP Streams (ONVIF, Generic IP Cam)                                           |
|  - V380 Pro UDP Scanner & SD-Patch RTSP Unlocker (Ref: CCTV-v380-pro & V380-Web)  |
|  - Low-Latency Streaming Core: go2rtc / WebRTC / MSE (Ref: Frigate)               |
+-----------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
|  [ Real-Time AI Processing Layer ] (Base: VisionGuard CCTV)                       |
|  - Motion Pre-filtering & Zone Masking (Ref: ZoneMinder)                          |
|  - Object Detection: YOLOv11 + ByteTrack / OC-SORT (Ref: CCTV, ClearCam)         |
|  - Traffic Counting & Anomaly (Intrusion & Loitering Engine) (Ref: CCTV)          |
|  - Vector Face Engine: SCRFD + InsightFace 512-d (Ref: CCTV)                      |
|  - Advanced Skills: Person Re-ID, Fall Detection, VLM Summary (DeepCam, ClearCam) |
+-----------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
|  [ Storage, Vector & Retention Layer ]                                            |
|  - Vector DB: Qdrant Vector Store (High-speed Face Similarity <50ms) (Ref: CCTV)  |
|  - Event Logs & Metadata: SQLite / PostgreSQL (Ref: CCTV)                         |
|  - Storage Tiering: Multi-Cloud Backup Gateway (Ref: Clospol)                      |
+-----------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
|  [ Presentation & Dashboard Layer ] (Base: VisionGuard CCTV)                      |
|  - Modern Web Dashboard (React + Vite + Tailwind CSS)                             |
|  - Live Grid, People Gallery (Face Clustering), Photo Vector Search Modal         |
|  - Analytics & Traffic Charts, Alert Notifications                                |
+-----------------------------------------------------------------------------------+
```

---

## 4. Lokasi Folder Referensi

Folder referensi tersedia di:
- `D:\Project\CCTV NEW\CCTV REFF PROJECT\CCTV` *(VisionGuard AI - Fullstack Base)*
- `D:\Project\CCTV NEW\CCTV REFF PROJECT\frigate`
- `D:\Project\CCTV NEW\CCTV REFF PROJECT\CCTV-v380-pro`
- `D:\Project\CCTV NEW\CCTV REFF PROJECT\V380-Web`
- `D:\Project\CCTV NEW\CCTV REFF PROJECT\DeepCamera`
- `D:\Project\CCTV NEW\CCTV REFF PROJECT\zoneminder`
- `D:\Project\CCTV NEW\CCTV REFF PROJECT\clearcam`
- `D:\Project\CCTV NEW\CCTV REFF PROJECT\Clospol`
