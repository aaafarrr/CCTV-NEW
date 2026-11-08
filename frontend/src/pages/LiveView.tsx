import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Tag,
  Space,
  Typography,
  Table,
  Modal,
  Form,
  Input,
  InputNumber,
  Switch,
  Select,
  Segmented,
  Tooltip,
  Badge,
  Popconfirm,
  message,
  Divider,
} from 'antd';
import {
  VideoCameraOutlined,
  CameraOutlined,
  VideoCameraAddOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  CloudUploadOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  FullscreenOutlined,
  RadarChartOutlined,
  SearchOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { ENTERPRISE_TOKENS } from '../theme/enterpriseTheme';
import { apiFetch } from '../utils/api';

const { Title, Text } = Typography;

export const LiveViewPage: React.FC = () => {
  const [cameras, setCameras] = useState<any[]>([]);
  const [selectedCam, setSelectedCam] = useState<any | null>(null);
  const [galleryFiles, setGalleryFiles] = useState<any[]>([]);
  const [loadingGallery, setLoadingGallery] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const [recording, setRecording] = useState(false);
  const [gridSize, setGridSize] = useState<number>(2);

  // Modal Camera Form
  const [modalOpen, setModalOpen] = useState(false);
  const [isEdit, setIsEdit] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [camName, setCamName] = useState('');
  const [camStreamUrl, setCamStreamUrl] = useState('');
  const [camSnapshotUrl, setCamSnapshotUrl] = useState('');
  const [camRecordStream, setCamRecordStream] = useState(false);
  const [camRecordInterval, setCamRecordInterval] = useState(5);
  const [camRetentionDays, setCamRetentionDays] = useState(7);

  // ONVIF helper
  const [onvifUrl, setOnvifUrl] = useState('');
  const [onvifUser, setOnvifUser] = useState('');
  const [onvifPass, setOnvifPass] = useState('');
  const [testingOnvif, setTestingOnvif] = useState(false);

  // Playback Modal
  const [playbackFile, setPlaybackFile] = useState<any | null>(null);

  // Network CCTV Scanner
  const [scannerOpen, setScannerOpen] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanMode, setScanMode] = useState<string>('full');
  const [subnets, setSubnets] = useState<any[]>([]);
  const [selectedSubnet, setSelectedSubnet] = useState<string>('');
  const [scanUser, setScanUser] = useState('');
  const [scanPass, setScanPass] = useState('');
  const [discoveredDevices, setDiscoveredDevices] = useState<any[]>([]);
  const [probingIp, setProbingIp] = useState<string | null>(null);

  const fetchSubnets = async () => {
    try {
      const res = await apiFetch('/api/cctv/scanner/subnets');
      if (res.ok) {
        const data = await res.json();
        setSubnets(data.subnets || []);
        if (data.subnets && data.subnets.length > 0 && !selectedSubnet) {
          const primary = data.subnets.find((s: any) => s.is_primary) || data.subnets[0];
          setSelectedSubnet(primary.subnet_cidr);
        }
      }
    } catch {
      // ignore
    }
  };

  const openScanner = () => {
    setScannerOpen(true);
    fetchSubnets();
  };

  const handleStartScan = async () => {
    setScanning(true);
    try {
      const res = await apiFetch('/api/cctv/scanner/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: scanMode,
          subnet_cidr: selectedSubnet || undefined,
          username: scanUser.trim() || undefined,
          password: scanPass || undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setDiscoveredDevices(data.devices || []);
        if ((data.devices || []).length === 0) {
          message.info('Tidak ada perangkat CCTV atau ONVIF terdeteksi pada rentang ini.');
        } else {
          message.success(`Ditemukan ${data.devices.length} perangkat CCTV aktif di jaringan!`);
        }
      } else {
        const err = await res.json();
        message.error(err.detail || 'Pemindaian gagal.');
      }
    } catch (e: any) {
      message.error(e.message || 'Pemindaian gagal.');
    } finally {
      setScanning(false);
    }
  };

  const handleProbeDiscovered = async (dev: any) => {
    setProbingIp(dev.ip);
    try {
      const res = await apiFetch('/api/cctv/scanner/probe-device', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ip: dev.ip,
          port: dev.open_ports && dev.open_ports.length > 0 ? dev.open_ports[0] : 80,
          onvif_url: dev.onvif_url || undefined,
          username: scanUser.trim() || undefined,
          password: scanPass || undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const d = data.device;
        message.success(`Koneksi terverifikasi! ${d.manufacturer || dev.brand} - RTSP live: ${d.is_stream_live ? 'ONLINE' : 'OFFLINE'}`);
        setDiscoveredDevices((prev) =>
          prev.map((item) =>
            item.ip === dev.ip
              ? {
                  ...item,
                  rtsp_url: d.rtsp_url || item.rtsp_url,
                  snapshot_url: d.snapshot_url || item.snapshot_url,
                  brand: d.manufacturer || item.brand,
                  probed: true,
                  is_stream_live: d.is_stream_live,
                }
              : item
          )
        );
      } else {
        const err = await res.json();
        message.warning(err.detail || 'Kamera merespons tetapi verifikasi stream gagal.');
      }
    } catch (e: any) {
      message.error(e.message || 'Uji koneksi gagal.');
    } finally {
      setProbingIp(null);
    }
  };

  const handleImportToForm = (dev: any) => {
    setIsEdit(false);
    setEditId(null);
    setCamName(dev.device_name || `Kamera ${dev.brand} (${dev.ip})`);
    setCamStreamUrl(dev.rtsp_url || `rtsp://${dev.ip}:554/live/ch0`);
    setCamSnapshotUrl(dev.snapshot_url || '');
    setOnvifUrl(dev.onvif_url || `http://${dev.ip}:80/onvif/device_service`);
    setOnvifUser(scanUser);
    setOnvifPass(scanPass);
    setScannerOpen(false);
    setModalOpen(true);
    message.info('Informasi kamera telah disalin ke formulir. Silakan verifikasi dan simpan.');
  };

  const fetchCameras = async () => {
    try {
      const res = await apiFetch('/api/cctv');
      if (res.ok) {
        const data = await res.json();
        setCameras(data.cameras || []);
        if (data.cameras && data.cameras.length > 0 && !selectedCam) {
          setSelectedCam(data.cameras[0]);
        }
      }
    } catch {
      // ignore
    }
  };

  const fetchGallery = async (camId: string) => {
    setLoadingGallery(true);
    try {
      const res = await apiFetch(`/api/cctv/${camId}/gallery`);
      if (res.ok) {
        const data = await res.json();
        setGalleryFiles(data.files || []);
      }
    } catch {
      // ignore
    } finally {
      setLoadingGallery(false);
    }
  };

  useEffect(() => {
    fetchCameras();
    const interval = setInterval(fetchCameras, 8000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedCam) {
      fetchGallery(selectedCam.id);
    }
  }, [selectedCam?.id]);

  const handleTestOnvif = async () => {
    if (!onvifUrl.trim()) {
      message.warning('Masukkan URL/IP ONVIF');
      return;
    }
    setTestingOnvif(true);
    try {
      const res = await apiFetch('/api/cctv/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stream_url: onvifUrl,
          onvif_url: onvifUrl,
          onvif_username: onvifUser,
          onvif_password: onvifPass,
        }),
      });

      if (!res.ok) throw new Error('Koneksi ONVIF gagal');
      const data = await res.json();
      message.success('ONVIF ditemukan! URL RTSP otomatis diterapkan');
      if (data.stream_url) setCamStreamUrl(data.stream_url);
      if (data.onvif_details?.snapshot_url) setCamSnapshotUrl(data.onvif_details.snapshot_url);
    } catch (e: any) {
      message.error(e.message || 'Koneksi ONVIF gagal');
    } finally {
      setTestingOnvif(false);
    }
  };

  const handleSaveCamera = async () => {
    if (!camName.trim() || !camStreamUrl.trim()) {
      message.warning('Nama Kamera dan Stream URL wajib diisi');
      return;
    }

    try {
      const payload = {
        name: camName.trim(),
        stream_url: camStreamUrl.trim(),
        snapshot_url: camSnapshotUrl.trim() || null,
        record_stream: camRecordStream,
        record_interval: camRecordInterval,
        retention_days: camRetentionDays,
        snapshot_headers: {},
      };

      const url = isEdit ? `/api/cctv/${editId}` : '/api/cctv';
      const method = isEdit ? 'PUT' : 'POST';

      const res = await apiFetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error('Gagal menyimpan kamera');
      message.success(`Kamera ${camName} berhasil disimpan`);
      setModalOpen(false);
      fetchCameras();
    } catch (e: any) {
      message.error(e.message || 'Error simpan kamera');
    }
  };

  const handleDeleteCamera = async (camId: string) => {
    try {
      const res = await apiFetch(`/api/cctv/${camId}`, { method: 'DELETE' });
      if (res.ok) {
        message.success('Kamera dihapus');
        if (selectedCam?.id === camId) setSelectedCam(null);
        fetchCameras();
      }
    } catch {
      message.error('Gagal menghapus kamera');
    }
  };

  const handleCaptureSnapshot = async () => {
    if (!selectedCam) return;
    setCapturing(true);
    try {
      const res = await apiFetch(`/api/cctv/${selectedCam.id}/capture`, { method: 'POST' });
      if (res.ok) {
        message.success('Snapshot tersimpan & otomatis tersinkron ke Google Drive!');
        fetchGallery(selectedCam.id);
      } else {
        const err = await res.json();
        throw new Error(err.detail || 'Gagal capture');
      }
    } catch (e: any) {
      message.error(e.message || 'Snapshot error');
    } finally {
      setCapturing(false);
    }
  };

  const handleRecordClip = async () => {
    if (!selectedCam) return;
    setRecording(true);
    message.loading({ content: 'Merekam klip video stream (15 detik)...', key: 'rec_clip', duration: 16 });
    try {
      const res = await apiFetch(`/api/cctv/${selectedCam.id}/record-clip?duration=15`, { method: 'POST' });
      if (res.ok) {
        message.success({ content: 'Rekaman video berhasil dibuat & tersinkron ke Google Drive!', key: 'rec_clip' });
        fetchGallery(selectedCam.id);
      } else {
        const err = await res.json();
        throw new Error(err.detail || 'Gagal merekam');
      }
    } catch (e: any) {
      message.error({ content: e.message || 'Record error', key: 'rec_clip' });
    } finally {
      setRecording(false);
    }
  };

  const galleryColumns = [
    {
      title: 'Nama File',
      dataIndex: 'name',
      key: 'name',
      render: (t: string, r: any) => (
        <Space>
          <Tag color={r.fileType === 'video' ? 'blue' : 'purple'}>{r.fileType.toUpperCase()}</Tag>
          <Text strong>{t}</Text>
        </Space>
      ),
    },
    {
      title: 'Waktu Dibuat',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (t: string) => <span className="mono-text" style={{ fontSize: 12 }}>{new Date(t).toLocaleString('id-ID')}</span>,
    },
    {
      title: 'Ukuran',
      dataIndex: 'sizeBytes',
      key: 'sizeBytes',
      render: (b: number) => `${(b / (1024 * 1024)).toFixed(2)} MB`,
    },
    {
      title: 'Status Google Drive',
      dataIndex: 'syncStatus',
      key: 'syncStatus',
      render: (s: string, r: any) =>
        s === 'synced' ? (
          <a href={r.googleDriveUrl} target="_blank" rel="noreferrer">
            <Tag icon={<CheckCircleOutlined />} color="success">Tersimpan di Cloud</Tag>
          </a>
        ) : (
          <Tag color="default">Lokal Saja</Tag>
        ),
    },
    {
      title: 'Aksi',
      key: 'action',
      render: (_: any, r: any) => (
        <Space>
          <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={() => setPlaybackFile(r)}>
            Lihat Rekaman
          </Button>
          <Button size="small" href={r.downloadUrl} download>
            Unduh
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {/* Top Header Control Bar */}
      <Card size="small">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <Space wrap size="middle">
            <Title level={4} style={{ margin: 0 }}>
              <VideoCameraOutlined style={{ color: ENTERPRISE_TOKENS.primaryColor, marginRight: 8 }} />
              Live CCTV Matrix & Clospol Player
            </Title>
            <Segmented
              value={gridSize}
              onChange={(val) => setGridSize(Number(val))}
              options={[
                { label: '1x1 Fokus', value: 1 },
                { label: '2x2 Grid', value: 2 },
                { label: '3x3 Matrix', value: 3 },
              ]}
            />
          </Space>

          <Space wrap>
            <Button
              icon={<RadarChartOutlined style={{ color: ENTERPRISE_TOKENS.primaryColor }} />}
              onClick={openScanner}
            >
              Pindai Jaringan (ONVIF & RTSP)
            </Button>
            <Button
              type="primary"
              icon={<VideoCameraAddOutlined />}
              onClick={() => {
                setIsEdit(false);
                setCamName('');
                setCamStreamUrl('');
                setCamSnapshotUrl('');
                setCamRecordStream(false);
                setModalOpen(true);
              }}
            >
              Tambah Kamera Baru
            </Button>
          </Space>
        </div>
      </Card>

      {/* Main Grid View */}
      {cameras.length === 0 ? (
        <Card style={{ textAlign: 'center', padding: '40px 20px' }}>
          <Title level={4} type="secondary">Belum Ada Kamera Terdaftar</Title>
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            Tambahkan kamera IP/RTSP Anda atau hubungkan kamera ONVIF untuk memulai monitoring dan sinkronisasi ke Google Drive.
          </Text>
          <Button type="primary" icon={<VideoCameraAddOutlined />} onClick={() => setModalOpen(true)}>
            Daftarkan Kamera Pertama
          </Button>
        </Card>
      ) : (
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={gridSize === 1 ? 24 : 16}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: `repeat(${gridSize}, minmax(0, 1fr))`,
                gap: 12,
              }}
            >
              {cameras.slice(0, gridSize * gridSize).map((cam) => {
                const isSelected = selectedCam?.id === cam.id;
                return (
                  <Card
                    key={cam.id}
                    size="small"
                    onClick={() => setSelectedCam(cam)}
                    style={{
                      border: isSelected ? `2px solid ${ENTERPRISE_TOKENS.primaryColor}` : '1px solid #e2e8f0',
                      cursor: 'pointer',
                    }}
                    title={
                      <Space>
                        <Badge status={cam.status === 'active' ? 'success' : 'default'} />
                        <Text strong>{cam.name}</Text>
                      </Space>
                    }
                    extra={
                      <Space size={4}>
                        <Tooltip title="Edit Kamera">
                          <Button
                            size="small"
                            icon={<EditOutlined />}
                            onClick={(e) => {
                              e.stopPropagation();
                              setIsEdit(true);
                              setEditId(cam.id);
                              setCamName(cam.name);
                              setCamStreamUrl(cam.streamUrl);
                              setCamSnapshotUrl(cam.snapshotUrl || '');
                              setCamRecordStream(cam.recordStream);
                              setCamRecordInterval(cam.recordInterval);
                              setCamRetentionDays(cam.retentionDays);
                              setModalOpen(true);
                            }}
                          />
                        </Tooltip>
                        <Popconfirm title="Hapus kamera ini?" onConfirm={() => handleDeleteCamera(cam.id)}>
                          <Button size="small" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
                        </Popconfirm>
                      </Space>
                    }
                  >
                    <div style={{ aspectRatio: '16/10', background: '#000', borderRadius: 6, overflow: 'hidden' }}>
                      <img
                        src={`/api/cctv/${cam.id}/stream`}
                        alt={cam.name}
                        style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
                      />
                    </div>
                  </Card>
                );
              })}
            </div>
          </Col>

          {/* Side Control & Action Panel */}
          {selectedCam && (
            <Col xs={24} lg={gridSize === 1 ? 24 : 8}>
              <Card
                size="small"
                title={`Kontrol Kamera: ${selectedCam.name}`}
                extra={<Tag color="blue">{selectedCam.status.toUpperCase()}</Tag>}
              >
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>Stream URL:</Text>
                    <div className="mono-text" style={{ fontSize: 12, wordBreak: 'break-all' }}>{selectedCam.streamUrl}</div>
                  </div>

                  <Space wrap style={{ width: '100%' }}>
                    <Button
                      type="primary"
                      icon={<CameraOutlined />}
                      loading={capturing}
                      onClick={handleCaptureSnapshot}
                      block
                    >
                      Ambil Snapshot & Sync Drive
                    </Button>

                    <Button
                      icon={<VideoCameraOutlined />}
                      loading={recording}
                      onClick={handleRecordClip}
                      block
                    >
                      Rekam Klip Video 15s
                    </Button>
                  </Space>

                  <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                      <Text type="secondary">Auto-Record:</Text>
                      <Text strong>{selectedCam.recordStream ? `Aktif (Tiap ${selectedCam.recordInterval}m)` : 'Nonaktif'}</Text>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginTop: 4 }}>
                      <Text type="secondary">Retensi File:</Text>
                      <Text strong>{selectedCam.retentionDays} Hari</Text>
                    </div>
                  </div>
                </Space>
              </Card>
            </Col>
          )}
        </Row>
      )}

      {/* Clospol Archival Gallery & Scrubber Table */}
      {selectedCam && (
        <Card
          size="small"
          title={`Galeri Rekaman & Cloud Sync — ${selectedCam.name}`}
          extra={
            <Button size="small" icon={<ReloadOutlined spin={loadingGallery} />} onClick={() => fetchGallery(selectedCam.id)}>
              Segarkan Galeri
            </Button>
          }
        >
          <Table
            dataSource={galleryFiles}
            columns={galleryColumns}
            rowKey="id"
            loading={loadingGallery}
            pagination={{ pageSize: 6 }}
            size="small"
          />
        </Card>
      )}

      {/* Modal Add / Edit Camera */}
      <Modal
        title={isEdit ? 'Edit Pengaturan Kamera' : 'Tambah Kamera Baru (Clospol)'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSaveCamera}
        okText="Simpan Kamera"
      >
        <Form layout="vertical">
          <Form.Item label="Nama Kamera" required>
            <Input value={camName} onChange={(e) => setCamName(e.target.value)} placeholder="Contoh: Pintu Masuk Gudang" />
          </Form.Item>

          <Card size="small" title="Bantuan ONVIF Discovery" style={{ background: '#f8fafc', marginBottom: 16 }}>
            <Form.Item label="ONVIF IP / Service URL">
              <Input value={onvifUrl} onChange={(e) => setOnvifUrl(e.target.value)} placeholder="http://192.168.1.100:80/onvif/device_service" />
            </Form.Item>
            <Space style={{ width: '100%' }}>
              <Input value={onvifUser} onChange={(e) => setOnvifUser(e.target.value)} placeholder="Username" />
              <Input.Password value={onvifPass} onChange={(e) => setOnvifPass(e.target.value)} placeholder="Password" />
              <Button loading={testingOnvif} onClick={handleTestOnvif}>Pindai</Button>
            </Space>
          </Card>

          <Form.Item label="Stream URL (RTSP / HLS)" required>
            <Input value={camStreamUrl} onChange={(e) => setCamStreamUrl(e.target.value)} placeholder="rtsp://admin:pass@192.168.1.100:554/live/ch0" />
          </Form.Item>

          <Form.Item label="Snapshot URL (Opsional)">
            <Input value={camSnapshotUrl} onChange={(e) => setCamSnapshotUrl(e.target.value)} placeholder="http://192.168.1.100/snapshot.jpg" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="Perekaman Otomatis (Auto-Record)">
                <Switch checked={camRecordStream} onChange={(v) => setCamRecordStream(v)} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Interval Rekam (Menit)">
                <InputNumber value={camRecordInterval} onChange={(v) => setCamRecordInterval(Number(v || 5))} min={1} max={60} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="Masa Retensi File (Hari)">
            <InputNumber value={camRetentionDays} onChange={(v) => setCamRetentionDays(Number(v || 7))} min={1} max={365} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Playback Modal */}
      <Modal
        title={`Pemutaran Rekaman: ${playbackFile?.name || ''}`}
        open={!!playbackFile}
        onCancel={() => setPlaybackFile(null)}
        footer={[
          <Button key="close" type="primary" onClick={() => setPlaybackFile(null)}>Tutup</Button>
        ]}
        width={720}
      >
        {playbackFile && (
          <div>
            {playbackFile.fileType === 'video' ? (
              <video
                src={playbackFile.downloadUrl}
                controls
                autoPlay
                style={{ width: '100%', maxHeight: 420, background: '#000', borderRadius: 8 }}
              />
            ) : (
              <img
                src={playbackFile.downloadUrl}
                alt={playbackFile.name}
                style={{ width: '100%', maxHeight: 420, objectFit: 'contain', borderRadius: 8 }}
              />
            )}
            <div style={{ marginTop: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="mono-text">{playbackFile.name}</span>
              {playbackFile.googleDriveUrl && (
                <Button type="link" href={playbackFile.googleDriveUrl} target="_blank">
                  Buka di Google Drive ↗
                </Button>
              )}
            </div>
          </div>
        )}
      </Modal>
      {/* Network CCTV Scanner Modal */}
      <Modal
        title={
          <Space>
            <RadarChartOutlined style={{ color: ENTERPRISE_TOKENS.primaryColor }} />
            <span>Pemindaian Kamera CCTV di Jaringan (ONVIF & RTSP Discovery)</span>
          </Space>
        }
        open={scannerOpen}
        onCancel={() => setScannerOpen(false)}
        footer={[
          <Button key="close" onClick={() => setScannerOpen(false)}>
            Tutup
          </Button>,
        ]}
        width={920}
      >
        <Card size="small" style={{ background: '#f8fafc', marginBottom: 16 }}>
          <Row gutter={[16, 12]} align="middle">
            <Col xs={24} sm={8}>
              <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                Subnet / IP Range Target:
              </Text>
              <Select
                style={{ width: '100%' }}
                value={selectedSubnet}
                onChange={(val) => setSelectedSubnet(val)}
                options={[
                  ...subnets.map((s) => ({
                    label: `${s.subnet_cidr} (${s.interface_ip}${s.is_primary ? ' - Utama' : ''})`,
                    value: s.subnet_cidr,
                  })),
                  { label: 'Subnet 192.168.1.0/24', value: '192.168.1.0/24' },
                  { label: 'Subnet 192.168.0.0/24', value: '192.168.0.0/24' },
                  { label: 'Subnet 10.0.0.0/24', value: '10.0.0.0/24' },
                ]}
              />
            </Col>

            <Col xs={24} sm={8}>
              <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                Metode Pemindaian:
              </Text>
              <Select
                style={{ width: '100%' }}
                value={scanMode}
                onChange={(val) => setScanMode(val)}
                options={[
                  { label: 'Lengkap (ONVIF Multicast + Port Probe)', value: 'full' },
                  { label: 'ONVIF WS-Discovery Saja (Port 3702)', value: 'onvif' },
                  { label: 'Subnet Port Scanner (RTSP 554, HTTP 80/8080/8899)', value: 'subnet' },
                ]}
              />
            </Col>

            <Col xs={24} sm={8}>
              <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                Aksi:
              </Text>
              <Button
                type="primary"
                icon={<SearchOutlined />}
                loading={scanning}
                onClick={handleStartScan}
                style={{ width: '100%' }}
              >
                {scanning ? 'Memindai Jaringan...' : 'Mulai Pindai'}
              </Button>
            </Col>

            <Col xs={12} sm={12}>
              <Input
                placeholder="Username CCTV (Opsional untuk auto-auth)"
                value={scanUser}
                onChange={(e) => setScanUser(e.target.value)}
              />
            </Col>

            <Col xs={12} sm={12}>
              <Input.Password
                placeholder="Password CCTV (Opsional untuk auto-auth)"
                value={scanPass}
                onChange={(e) => setScanPass(e.target.value)}
              />
            </Col>
          </Row>
        </Card>

        <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text strong>
            Hasil Pemindaian ({discoveredDevices.length} Perangkat Ditemukan):
          </Text>
          {discoveredDevices.length > 0 && (
            <Tag color="success">
              <CheckCircleOutlined /> Pemindaian Selesai
            </Tag>
          )}
        </div>

        <Table
          dataSource={discoveredDevices}
          rowKey="ip"
          size="small"
          loading={scanning}
          pagination={{ pageSize: 5 }}
          locale={{
            emptyText: scanning
              ? 'Sedang mengirim paket WS-Discovery dan memindai port subnet...'
              : 'Belum ada perangkat terdeteksi. Klik "Mulai Pindai" untuk mendeteksi kamera CCTV di jaringan Anda.',
          }}
          columns={[
            {
              title: 'IP & Port',
              key: 'ip',
              render: (_: any, r: any) => (
                <div>
                  <Text strong style={{ fontSize: 14 }}>
                    {r.ip}
                  </Text>
                  <div style={{ marginTop: 4 }}>
                    {(r.open_ports || []).map((p: number) => (
                      <Tag key={p} color={p === 554 ? 'blue' : p === 80 || p === 8899 ? 'orange' : 'default'} style={{ fontSize: 11 }}>
                        {p}
                      </Tag>
                    ))}
                  </div>
                </div>
              ),
            },
            {
              title: 'Brand & Tipe',
              key: 'brand',
              render: (_: any, r: any) => (
                <Space direction="vertical" size={2}>
                  <Tag
                    color={
                      r.brand?.includes('Hikvision')
                        ? 'red'
                        : r.brand?.includes('Dahua')
                        ? 'orange'
                        : r.brand?.includes('Tapo')
                        ? 'green'
                        : r.brand?.includes('Xiongmai')
                        ? 'cyan'
                        : 'geekblue'
                    }
                  >
                    {r.brand || 'Generic CCTV'}
                  </Tag>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {r.discovery_method || r.type}
                  </Text>
                </Space>
              ),
            },
            {
              title: 'Nama / Hardware',
              dataIndex: 'device_name',
              key: 'device_name',
              render: (t: string, r: any) => (
                <div>
                  <Text strong>{t}</Text>
                  {r.hardware && r.hardware !== t && (
                    <div>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {r.hardware}
                      </Text>
                    </div>
                  )}
                </div>
              ),
            },
            {
              title: 'Stream RTSP Candidate',
              key: 'rtsp_url',
              render: (_: any, r: any) => (
                <div>
                  <span className="mono-text" style={{ fontSize: 11, wordBreak: 'break-all' }}>
                    {r.rtsp_url}
                  </span>
                  {r.is_stream_live !== undefined && (
                    <div style={{ marginTop: 2 }}>
                      <Tag color={r.is_stream_live ? 'success' : 'error'} style={{ fontSize: 10 }}>
                        {r.is_stream_live ? 'Stream Live OK' : 'Belum Terhubung'}
                      </Tag>
                    </div>
                  )}
                </div>
              ),
            },
            {
              title: 'Aksi',
              key: 'action',
              render: (_: any, r: any) => (
                <Space>
                  <Button
                    type="primary"
                    size="small"
                    icon={<PlusOutlined />}
                    onClick={() => handleImportToForm(r)}
                  >
                    Tambah
                  </Button>
                  <Button
                    size="small"
                    icon={<ThunderboltOutlined />}
                    loading={probingIp === r.ip}
                    onClick={() => handleProbeDiscovered(r)}
                  >
                    Uji
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Modal>
    </Space>
  );
};
