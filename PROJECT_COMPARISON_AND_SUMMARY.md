# RANGKUMAN FITUR, PERBANDINGAN, DAN KESIMPULAN REPOSITORI REFERENSI
**Direktori Sumber**: `D:\Project\CCTV NEW\CCTV REFF PROJECT`  
**Proyek Referensi**: 8 Proyek (*CCTV / VisionGuard, Frigate, ClearCam, DeepCamera, ZoneMinder, CCTV-v380-pro, V380-Web, Clospol*)

---

## 1. Rangkuman Detail Fitur Tiap Proyek

### 1. VisionGuard AI (`CCTV`)
* **Kategori**: NVR Cerdas Full-Stack (All-in-One Enterprise)
* **Teknologi**: Python (FastAPI), React + Vite + Tailwind CSS, Qdrant Vector DB, YOLOv11, ByteTrack, InsightFace (SCRFD + ArcFace).
* **Daftar Fitur Utama**:
  - **Pencarian Wajah Mirip Google Photos**: Ekstraksi wajah 512-dimensi ke dalam Qdrant Vector DB (dengan pencarian kemiripan kosinus `< 50ms`). Memiliki mode fallback otomatis ke memory (`:memory:`) jika Qdrant server belum diinstal.
  - **People Gallery & Clustering**: Pengelompokan galeri wajah otomatis berdasarkan identitas orang yang sama, lengkap dengan tagging nama & watchlist (DPO / VIP).
  - **Cross-Line Counting & Traffic Analytics**: Perhitungan jumlah pedestrian dan kendaraan (mobil, motor, bus, truk) yang melewati garis maya masuk/keluar.
  - **Deteksi Perilaku Mencurigakan**:
    - *Intrusion Detection*: Deteksi pelanggaran batas area terlarang berbasis ROI polygon.
    - *Loitering Detection*: Deteksi orang yang berdiam terlalu lama di zona rawan.
  - **Dashboard Manajemen Lengkap**: Live view camera grid, log kejadian, analitik grafik, dan persistence konfigurasi kamera ke JSON/Database.

---

### 2. Frigate NVR (`frigate`)
* **Kategori**: Real-Time Object Detection NVR tingkat Produksi
* **Teknologi**: Python, Go (**go2rtc**), Vue.js / TypeScript, TensorFlow Lite, OpenVINO, TensorRT.
* **Daftar Fitur Utama**:
  - **Pipeline Deteksi 2 Lapis (Super Efisien)**: Motion detection ringan berbasis CPU dijalankan terlebih dahulu untuk menemukan area gerakan; inferensi model AI berat hanya dipanggil pada koordinat kotak tersebut. Menghemat beban CPU/GPU hingga 80%.
  - **go2rtc Streaming Core**: Streaming multi-protokol latensi sangat rendah (WebRTC, MSE, RTSP re-streaming, HLS).
  - **Hardware Accelerator Penuh**: Dukungan native Google Coral TPU, NVIDIA TensorRT, Intel OpenVINO, dan Apple Silicon.
  - **Recording & Retention Fleksibel**: Perekaman kontinu atau hanya saat objek spesifik (person/car) terdeteksi, dengan aturan retensi berbeda antara rekaman biasa dan rekaman event klip.
  - **Integrasi Smart Home**: Integrasi MQTT dan Home Assistant secara native.

---

### 3. ClearCam (`clearcam`)
* **Kategori**: AI NVR Modern & Peringatan Berbasis LLM
* **Teknologi**: Python, Ultralytics YOLOv8/v11, OC-SORT Tracker, OpenCV, LLM APIs (OpenAI/Anthropic/Local).
* **Daftar Fitur Utama**:
  - **Pelacakan Objek Stabil (OC-SORT)**: Mengatasi masalah ID switching saat objek tertutup sementara (occlusion).
  - **AI Event Summaries (LLM Narrative)**: Menerjemahkan serangkaian deteksi koordinat menjadi kalimat laporan manusiawi (Contoh: *"Kurir berseragam meletakkan paket di teras depan pada pukul 14:15"*).
  - **Notifikasi Multi-Kanal Cerdas**: Kirim peringatan ringkas ke Telegram, Pushover, atau Mobile Push Notification.
  - **Antarmuka Minimalis Single-File**: Dashboard HTML responsif yang ringan dan tidak memerlukan instalasi rumit.

---

### 4. DeepCamera (`DeepCamera`)
* **Kategori**: Platform Edge AI & Modular Skills Surveillance
* **Teknologi**: Python, C++, ONNX Runtime, PyTorch, Local LLM/VLM (Qwen, SmolVLM, DeepSeek).
* **Daftar Fitur Utama**:
  - **Modular Skills Catalog**: Modul AI berbentuk plugin independen yang bisa dinyalakan/dimatikan sesuai kebutuhan kamera.
  - **Person Re-Identification (Re-ID)**: Melacak orang yang sama yang berpindah-pindah antar kamera berbeda berdasarkan ciri pakaian/postur tanpa harus melihat wajah.
  - **Analisis Adegan Multimodal (VLM)**: Menggunakan Vision-Language Model lokal untuk menganalisis aktivitas yang tidak biasa pada feed CCTV.
  - **Fall Detection (Deteksi Jatuh)**: Khusus untuk pemantauan lansia, pasien rumah sakit, atau area industri.
  - **Face Recognition Edge**: Pengenalan wajah lokal dengan privasi 100% on-premise.

---

### 5. ZoneMinder (`zoneminder`)
* **Kategori**: Enterprise Surveillance Server Tradisional & Battle-Tested
* **Teknologi**: C++, PHP, Perl, JavaScript, MySQL, Linux V4L.
* **Daftar Fitur Utama**:
  - **Circular Pre-Alarm Buffering**: Memanfaatkan RAM/Shared Memory (`shm` / `mmap`) untuk menyimpan beberapa detik frame video secara kontinu, sehingga saat gerak terdeteksi, rekaman video menyertakan beberapa detik **sebelum** kejadian dimulai.
  - **Sistem Zona Fleksibel**: Pembagian area pantau (*Active, Inclusive, Exclusive, Preclusive*) dengan konfigurasi threshold sensitivitas piksel yang sangat mendalam.
  - **Skalabilitas Multi-Kamera Masif**: Mampu menangani puluhan hingga ratusan kamera analog/IP secara bersamaan dalam satu klaster server.

---

### 6. CCTV-v380-pro (`CCTV-v380-pro`)
* **Kategori**: Riset Protokol & Tooling Reverse-Engineering V380
* **Teknologi**: Python, Shell Scripts, Packet Analysis (Wireshark).
* **Daftar Fitur Utama**:
  - **Local Network Discovery (`findcam.py`)**: Mengirimkan broadcast UDP paket `NVDEVSEARCH^100` ke port `10008` untuk menemukan semua kamera V380 di jaringan LAN tanpa login cloud vendor.
  - **Ekstraksi Informasi Kamera**: Mengambil Device ID, IP Address, port, dan firmware info secara otomatis dari paket balasan port `10009`.
  - **Riset Bypass Protokol Cloud P2P**: Skrip proof-of-concept untuk verifikasi streaming dan autentikasi kamera lokal.

---

### 7. V380-Web (`V380-Web`)
* **Kategori**: Firmware Patcher & RTSP Enabler Kamera V380
* **Teknologi**: C, Shell Scripting, Embedded Linux binaries.
* **Daftar Fitur Utama**:
  - **Non-Invasive Patch via MicroSD Card**: Mengaktifkan akses RTSP pada kamera V380 tanpa perlu membongkar casing atau solder UART. Cukup menaruh file patch di kartu memori.
  - **Native RTSP Stream Server**: Membuka endpoint `rtsp://<IP_Kamera>:554/live/ch0` sehingga kamera murah V380 bisa langsung dimasukkan ke NVR standar (Frigate, ZoneMinder, atau CCTV NEW).
  - **Embedded Web Management**: Menyediakan web interface mini di kamera untuk pengaturan jaringan, reboot, dan manajemen RTSP.

---

### 8. Clospol (`Clospol`)
* **Kategori**: Multi-Cloud Storage Pooling Gateway
* **Teknologi**: TypeScript, Next.js 15, Drizzle ORM, SQLite/PostgreSQL, Cloud Storage SDKs.
* **Daftar Fitur Utama**:
  - **Unified Storage Pooling**: Menggabungkan berbagai akun cloud gratis/berbayar (Google Drive, OneDrive, Dropbox, AWS S3, Cloudflare R2, MinIO, disk lokal) menjadi satu drive virtual raksasa.
  - **Storage Tiering Otomatis**: Memindahkan file lama dari penyimpanan cepat (NVMe/SSD) ke cold cloud storage hemat biaya secara otomatis.
  - **Deduplikasi & Chunking**: Pemecahan file rekaman dan enkripsi sebelum diunggah ke cloud publik.

---

## 2. Matriks Perbandingan Proyek

| Kriteria / Fitur | VisionGuard (`CCTV`) | Frigate | ClearCam | DeepCamera | ZoneMinder | V380 Tools | Clospol |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Fokus Arsitektur** | Modern Fullstack NVR | High-Perf AI NVR | Smart Tracking & LLM | Edge AI Skills | Classic Enterprise NVR | Cam Protocol & RTSP Hack | Storage Gateway |
| **Bahasa Utama** | Python + TS/React | Python + Go | Python | Python + C++ | C++ + PHP | Python / C | TypeScript (Next.js) |
| **Object Detection & Tracking** | YOLOv11 + ByteTrack | Multi-model (Coral/TRT) | YOLO + OC-SORT | Multi-model (ONNX) | Motion Pixel Difference | - | - |
| **Face Vector Search (512-d)** | **Ya (Qdrant DB)** | Tidak bawaan | Tidak | Ya (InsightFace) | Tidak | - | - |
| **Traffic / Line Counting** | **Ya (People & Vehicle)** | Parsial (Zones) | Tidak | Tidak | Tidak | - | - |
| **Behavioral Anomaly** | **Intrusion & Loitering** | Zone-based Alert | Basic Alert | Fall Detection & VLM | Motion Zones | - | - |
| **AI Narrative Summaries (LLM)** | Tidak | Tidak | **Ya (LLM Engine)** | **Ya (VLM)** | Tidak | - | - |
| **Streaming Engine Latency** | OpenCV / Standard RTSP | **Ultra-Low (go2rtc/WebRTC)** | OpenCV Web Stream | OpenCV / WebRTC | Shm Circular Buffer | Native RTSP Server | - |
| **Kamera V380 Support** | Stream RTSP standar | Stream RTSP standar | Stream RTSP standar | Stream RTSP standar | Stream RTSP standar | **Auto Discovery & Unlock** | - |
| **Cloud Storage Archiving** | Local Storage Only | Local / Network Drive | Local Only | Local Only | Local / S3 Plugin | - | **Multi-Cloud Pooling** |
| **UI Dashboard** | **Modern Full (React)** | **Modern (Vue)** | Simple HTML5 | Web Dashboard | Classic Web PHP | Web Mini | **Modern (Next.js)** |

---

## 3. Kesimpulan & Rekomendasi untuk `CCTV NEW`

Dari perbandingan 8 proyek di atas, dapat ditarik beberapa kesimpulan strategis:

1. **Baseline / Fondasi Utama Paling Cocok**:  
   Gunakan **VisionGuard AI (`CCTV`)** sebagai fondasi struktur proyek `CCTV NEW`. Proyek ini sudah memiliki arsitektur full-stack modern (FastAPI + React Vite), sistem pencarian wajah Google Photos-style dengan Qdrant (lengkap dengan mode in-memory fallback), serta engine deteksi objek, traffic counting, dan anomali perilaku (intrusion/loitering) yang siap pakai.

2. **Peningkatan Streaming & Efisiensi Resource (Adopsi dari Frigate & ZoneMinder)**:
   - Gunakan pendekatan **Frigate** (motion pre-filter) agar model AI berat tidak perlu memproses frame 24/7 saat kondisi sepi.
   - Pertimbangkan integrasi **go2rtc** untuk streaming WebRTC yang latensinya di bawah 500ms di browser.
   - Terapkan konsep **pre-event buffer** dari ZoneMinder agar video rekaman insiden menyertakan 5 detik sebelum alarm berbunyi.

3. **Penyelesaian Masalah Kamera Murah / Populer (Adopsi dari V380 Tools)**:
   - Pasang scanner UDP dari **CCTV-v380-pro** di halaman Settings untuk otomatis mendeteksi kamera V380 di jaringan LAN.
   - Sediakan dokumentasi / installer **V380-Web** agar kamera V380 user dapat langsung di-unlock RTSP-nya dan dimasukkan ke `CCTV NEW`.

4. **Kecerdasan Tambahan (Adopsi dari ClearCam & DeepCamera)**:
   - Tambahkan fitur *AI Narrative Summary* (ClearCam) agar notifikasi alarm ke user berupa kalimat ringkas berbahasa manusia.
   - Siapkan ekstensi modular (DeepCamera) untuk fitur masa depan seperti *Person Re-Identification* dan *Fall Detection*.

5. **Efisiensi Penyimpanan Rekaman (Adopsi dari Clospol)**:
   - Integrasikan konsep gateway dari **Clospol** sebagai modul sinkronisasi rekaman otomatis ke multi-cloud gratis (Google Drive / OneDrive / S3) agar hard disk lokal NVR tidak cepat penuh.

