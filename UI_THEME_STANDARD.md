# STANDAR TEMA & DESIGN SYSTEM TEMPLATE: CCTV NEW (LIGHT ENTERPRISE EDITION)

Dokumen ini mendefinisikan standar resmi arsitektur visual, token desain, komponen UI, dan layout template yang akan digunakan dalam pengembangan aplikasi **CCTV NEW**.

---

## 1. Filosofi & Karakteristik Desain

* **Nuansa Visual**: **Clean Enterprise Light Mode**
  - Bersih, profesional, ergonomis untuk pemantauan siang hari / kantor pengawasan resmi.
  - Memanfaatkan kontras tinggi agar feed video CCTV tetap menonjol di atas latar belakang terang tanpa membuat mata cepat lelah.
* **Component Library Utama**: **Ant Design (antd) / Material-UI (MUI)**
  - Mengedepankan komponen data-dense: Data Table canggih, Filter bar terstruktur, Modal/Drawer interaktif, Form kontrol PTZ yang kokoh.
  - Ikonografi: `@ant-design/icons` atau `lucide-react`.
* **Navigasi & Tata Letak**: **Multi-page Application**
  - Layout Collapsible Sidebar di sisi kiri dengan header breadcrumbs dan panel notifikasi real-time.

---

## 2. Palet Warna Resmi (Color Palette Tokens)

```css
:root {
  /* Surface & Background */
  --bg-app: #f4f6f9;              /* Background utama halaman */
  --bg-surface: #ffffff;          /* Background Card, Panel, Modal, Table */
  --bg-subtle: #f8fafc;           /* Background hover, secondary list item */
  
  /* Borders & Dividers */
  --border-light: #e2e8f0;        /* Garis pemisah antar card & table cell */
  --border-strong: #cbd5e1;       /* Border input, select, & panel aktif */
  
  /* Typography */
  --text-primary: #0f172a;        /* Teks utama (Slate-900) - kontras tajam */
  --text-secondary: #475569;      /* Label, sub-judul (Slate-600) */
  --text-muted: #94a3b8;          /* Placeholder, timestamp pudar */
  
  /* Brand / Primary Accent */
  --primary-color: #1677ff;       /* Blue Enterprise (Ant Design blue) */
  --primary-hover: #4096ff;
  --primary-bg: #e6f4ff;          /* Background badge aktif */
  
  /* Status & AI Event Accents */
  --status-online: #10b981;       /* Emerald / Green untuk Camera Online */
  --status-offline: #94a3b8;      /* Gray untuk Kamera Mati */
  --alert-danger: #ef4444;        /* Merah untuk Intrusion & Alert Watchlist */
  --alert-warning: #f59e0b;       /* Kuning/Amber untuk Loitering / Anomali */
  --badge-vehicle: #8b5cf6;       /* Ungu untuk deteksi Kendaraan */
  --badge-person: #06b6d4;        /* Cyan untuk deteksi Manusia / Pedestrian */
  --badge-face: #3b82f6;          /* Biru untuk deteksi Wajah / Face Cluster */
  
  /* CCTV Feed Player Surface */
  --video-bg: #000000;            /* Khusus area player video tetap hitam murni */
  --video-overlay-text: #ffffff;  /* Teks OSD (On-Screen Display) putih */
}
```

---

## 3. Struktur Layout & Navigasi (Shell Structure)

```
+-----------------------------------------------------------------------------------+
|  [ TOPBAR HEADER ]  Breadcrumbs > Current Page       [Search]  [Alarm Bell] [User]|
+---------------+-------------------------------------------------------------------+
| [SIDEBAR]     |  [ MAIN CONTENT CANVAS - #f4f6f9 ]                                |
| - Dashboard   |                                                                   |
| - Live Grid   |  +------------------------+  +---------------------------------+  |
| - People/Faces|  | Video Matrix Grid      |  | AI Detection & Event Stream     |  |
| - Events/Logs |  | (1x1, 2x2, 3x3, 4x4)   |  | (Side Drawer / Realtime Feed)   |  |
| - Cloud Store |  |                        |  |                                 |  |
| - Settings    |  +------------------------+  +---------------------------------+  |
|               |  +-------------------------------------------------------------+  |
|               |  | Incident Timeline Scrubber (Colored Event Bands)            |  |
| [Collapse <]  |  +-------------------------------------------------------------+  |
+---------------+-------------------------------------------------------------------+
```

### Halaman Utama:
1. **Dashboard Overview**: Ringkasan metrik statistik (total kamera aktif, foot-traffic hari ini, insiden keamanan terakhir, pemakaian storage).
2. **Live Multi-Cam Grid**: Pemantau live feed 1, 4, 9, 16 kamera dengan kontrol PTZ & digital zoom.
3. **People Gallery & Face Search**: Antarmuka klaster wajah Google Photos-style dengan modal drop-photo vector search.
4. **Events & Incidents Log**: Tabel data enterprise (filter tanggal, tipe insiden, kamera, export CSV/PDF).
5. **Storage & Cloud Sync**: Manajemen sinkronisasi rekaman lokal ke Google Drive / OneDrive / S3 (Clospol).
6. **System & Camera Settings**: Manajemen IP/RTSP stream, V380 network scanner, dan pengaturan sensitivitas AI.

---

## 4. Standar Modul Player & AI Overlay

### A. Adaptive Multi-Camera Matrix
* Pilihan tata letak instan:
  - **Single Focus (1x1)**: Kamera tunggal resolusi maksimal dengan OSD detail.
  - **Quad View (2x2)**: Standar default 4 kamera pemantau ruangan.
  - **9-Cam Matrix (3x3)** & **16-Cam Matrix (4x4)**: Modus monitoring perimeter luas.
* Tombol aksi cepat di sudut setiap tile video: Fullscreen, Snapshot Instan, PTZ Controller, dan Audio Mute/Unmute.

### B. AI Bounding Box & Zone Overlay
* Menggunakan lapisan Canvas HTML5 transparan di atas elemen `<video>` / stream MSE / WebRTC:
  - **Hijau (#10b981)**: Orang / Person normal yang terdeteksi & tracking ID.
  - **Ungu (#8b5cf6)**: Kendaraan (mobil, motor, bus, truk) dengan label kelas.
  - **Merah (#ef4444)**: Pelanggaran Zona Terlarang (Intrusion Polygon) & Target Masuk Daftar DPO.
  - **Kuning (#f59e0b)**: Peringatan Loitering (orang berdiam melebihi batas waktu aman).

### C. Incident Timeline Scrubber
* Pita waktu horizontal 24-jam di bawah feed rekaman:
  - Jalur abu-abu muda menandakan rekaman normal kontinu.
  - Segmen pita diwarnai otomatis saat terjadi event: Merah (Intrusion/Face Watchlist), Kuning (Loitering), Biru (People detected), Ungu (Vehicle crossed).
  - Fitur drag & click untuk melompat langsung ke detik terjadinya insiden.

### D. Google Photos-style Face Search Drawer
* Mengunggah foto target (JPG/PNG) via drag & drop.
* Menampilkan daftar thumbnail wajah mirip dari database vektor (Qdrant) beserta persentase similarity (contoh: *Match 94.2%*).
* Menampilkan riwayat kemunculan orang tersebut: timestamp, lokasi kamera, dan cuplikan klip rekaman.

---

## 5. Standar Kode & Konvensi Komponen (Frontend)

1. **State Management**: Zustand / React Context untuk status kamera aktif, notifikasi alert, dan user preferences.
2. **Streaming Client**: WebRTC / HLS.js / Canvas MJPEG stream client dengan auto-reconnect fallback jika jaringan putus.
3. **Komponen Form**: Ant Design `<Form>`, `<Table>`, `<Select>`, `<Card>` dengan tema kustom yang telah disesuaikan agar tampak clean dan lapang.
4. **Responsivitas**: Mendukung resolusi Full HD (1920x1080), 2K/4K display untuk ruang monitor security, serta adaptif untuk tablet.

