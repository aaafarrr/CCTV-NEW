import React, { useEffect, useState } from 'react';
import {
  Card,
  Tabs,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Alert,
  Typography,
  Popconfirm,
  message,
} from 'antd';
import {
  VideoCameraAddOutlined,
  RadarChartOutlined,
  EditOutlined,
  DeleteOutlined,
  UserAddOutlined,
  WifiOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { apiFetch } from '../utils/api';

const { Title, Text } = Typography;

interface SettingsProps {
  onOpenRoiDrawer?: (cam: any) => void;
}

export const SettingsPage: React.FC<SettingsProps> = ({ onOpenRoiDrawer }) => {
  const [cameras, setCameras] = useState<any[]>([]);
  const [v380Devices, setV380Devices] = useState<any[]>([]);
  const [v380Guide, setV380Guide] = useState<any>(null);
  const [onvifDevices, setOnvifDevices] = useState<any[]>([]);
  const [scanning, setScanning] = useState(false);

  // Camera Modal
  const [camModalOpen, setCamModalOpen] = useState(false);
  const [camFormId, setCamFormId] = useState('');
  const [camName, setCamName] = useState('');
  const [camLocation, setCamLocation] = useState('');
  const [camStreamUrl, setCamStreamUrl] = useState('synthetic_lobby');
  const [enableCounting, setEnableCounting] = useState(true);
  const [enableSuspicious, setEnableSuspicious] = useState(true);
  const [enableFaceRec, setEnableFaceRec] = useState(true);

  // Users RBAC
  const [users, setUsers] = useState<any[]>([]);
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newRole, setNewRole] = useState('OPERATOR');

  const fetchCameras = async () => {
    const res = await fetch('/api/v1/cameras');
    if (res.ok) setCameras(await res.json());
  };

  const fetchUsers = async () => {
    const res = await apiFetch('/api/v1/auth/users');
    if (res.ok) setUsers(await res.json());
  };

  useEffect(() => {
    fetchCameras();
    fetchUsers();
  }, []);

  const handleScanV380AndOnvif = async () => {
    setScanning(true);
    try {
      const [vRes, oRes] = await Promise.all([
        fetch('/api/v1/cameras/discover/v380'),
        fetch('/api/v1/cameras/discover/onvif'),
      ]);
      if (vRes.ok) {
        const vData = await vRes.json();
        setV380Devices(vData.devices || []);
        setV380Guide(vData.unlock_guide || null);
      }
      if (oRes.ok) {
        setOnvifDevices(await oRes.json());
      }
      message.success('Pemindaian jaringan LAN V380 (UDP 10008) & ONVIF selesai');
    } catch {
      message.error('Gagal memindai jaringan');
    } finally {
      setScanning(false);
    }
  };

  const handleSaveCamera = async () => {
    if (!camName.trim()) {
      message.warning('Nama kamera wajib diisi');
      return;
    }
    const targetId = camFormId.trim() || `cam_${Date.now().toString().slice(-4)}`;
    try {
      const res = await apiFetch(`/api/v1/cameras/${targetId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: camName.trim(),
          location: camLocation.trim() || 'Area Pengawasan',
          stream_url: camStreamUrl.trim(),
          enable_counting: enableCounting,
          enable_suspicious: enableSuspicious,
          enable_face_rec: enableFaceRec,
          roi_zones: [],
          counting_lines: [],
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Gagal menyimpan kamera');
      }
      message.success(`Kamera ${camName} berhasil disimpan`);
      setCamModalOpen(false);
      fetchCameras();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleDeleteCamera = async (id: string) => {
    const res = await apiFetch(`/api/v1/cameras/${id}`, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      message.error(err.detail || 'Hanya ADMIN yang dapat menghapus kamera');
      return;
    }
    message.success('Kamera dihapus');
    fetchCameras();
  };

  const handleQuickAddDiscovered = (dev: any) => {
    setCamFormId(`cam_v380_${dev.ip.split('.').pop()}`);
    setCamName(`${dev.manufacturer} (${dev.ip})`);
    setCamLocation(`LAN Discovery • ${dev.device_id}`);
    setCamStreamUrl(dev.rtsp_url);
    setCamModalOpen(true);
  };

  const handleCreateUser = async () => {
    if (!newUsername.trim() || !newPassword.trim()) {
      message.warning('Username dan password wajib diisi');
      return;
    }
    try {
      const res = await apiFetch('/api/v1/auth/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: newUsername.trim(),
          password: newPassword,
          full_name: newFullName.trim() || newUsername.trim(),
          email: newEmail.trim() || `${newUsername.trim()}@cctv.local`,
          role: newRole,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Gagal membuat pengguna');
      }
      message.success(`Pengguna ${newUsername} ditambahkan`);
      setUserModalOpen(false);
      setNewUsername('');
      setNewPassword('');
      fetchUsers();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleChangeUserRole = async (username: string, role: string) => {
    const res = await apiFetch(`/api/v1/auth/users/${username}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role }),
    });
    if (res.ok) {
      message.success(`Peran ${username} diubah ke ${role}`);
      fetchUsers();
    } else {
      const err = await res.json().catch(() => ({}));
      message.error(err.detail || 'Gagal mengubah peran');
    }
  };

  const handleDeleteUser = async (username: string) => {
    const res = await apiFetch(`/api/v1/auth/users/${username}`, { method: 'DELETE' });
    if (res.ok) {
      message.success(`Pengguna ${username} dihapus`);
      fetchUsers();
    } else {
      const err = await res.json().catch(() => ({}));
      message.error(err.detail || 'Gagal menghapus pengguna');
    }
  };

  return (
    <Card size="small">
      <Tabs
        items={[
          {
            key: 'cameras',
            label: '📹 Manajemen Kamera & Stream',
            children: (
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <Title level={5} style={{ margin: 0 }}>Daftar Kamera Terdaftar</Title>
                    <Text type="secondary" style={{ fontSize: 12 }}>Mendukung RTSP, ONVIF, V380 SD-Patch, dan Simulator AI Bawaan</Text>
                  </div>
                  <Button
                    type="primary"
                    icon={<VideoCameraAddOutlined />}
                    onClick={() => {
                      setCamFormId('');
                      setCamName('');
                      setCamLocation('');
                      setCamStreamUrl('synthetic_lobby');
                      setCamModalOpen(true);
                    }}
                  >
                    Tambah Kamera Baru
                  </Button>
                </div>

                <Table
                  dataSource={cameras}
                  rowKey="id"
                  size="small"
                  pagination={false}
                  columns={[
                    { title: 'ID', dataIndex: 'id', key: 'id', render: (t: string) => <span className="mono-text">{t}</span> },
                    { title: 'Nama Kamera', dataIndex: 'name', key: 'name', render: (t: string) => <Text strong>{t}</Text> },
                    { title: 'Lokasi', dataIndex: 'location', key: 'location' },
                    { title: 'Sumber Stream / RTSP', dataIndex: 'stream_url', key: 'stream_url', render: (t: string) => <Tag color="blue">{t}</Tag> },
                    {
                      title: 'Modul AI Aktif',
                      key: 'ai',
                      render: (_: any, r: any) => (
                        <Space size={4}>
                          {r.enable_counting && <Tag color="cyan">Counting</Tag>}
                          {r.enable_suspicious && <Tag color="red">Intrusion/Loitering</Tag>}
                          {r.enable_face_rec && <Tag color="purple">Face 512-d</Tag>}
                        </Space>
                      ),
                    },
                    {
                      title: 'Aksi',
                      key: 'action',
                      render: (_: any, r: any) => (
                        <Space>
                          <Button size="small" icon={<EditOutlined />} onClick={() => onOpenRoiDrawer?.(r)}>
                            Atur ROI
                          </Button>
                          <Popconfirm title="Hapus kamera ini?" onConfirm={() => handleDeleteCamera(r.id)}>
                            <Button size="small" danger icon={<DeleteOutlined />} />
                          </Popconfirm>
                        </Space>
                      ),
                    },
                  ]}
                />
              </Space>
            ),
          },
          {
            key: 'v380',
            label: '📡 Pemindai Jaringan V380 Pro & ONVIF',
            children: (
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Alert
                  type="info"
                  showIcon
                  message="Integrasi Protokol CCTV-v380-pro (UDP 10008 -> 10009) & V380-Web SD Patch"
                  description="Memindai kamera Macro-Video V380 / V380 Pro secara lokal di jaringan LAN menggunakan paket broadcast heksadesimal NVDEVSEARCH^100 tanpa ketergantungan cloud vendor."
                />

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text strong>Klik tombol di kanan untuk memindai perangkat V380 & ONVIF di LAN:</Text>
                  <Button type="primary" icon={<WifiOutlined />} loading={scanning} onClick={handleScanV380AndOnvif}>
                    Pindai Jaringan LAN (V380 & ONVIF)
                  </Button>
                </div>

                <Table
                  dataSource={[...v380Devices, ...onvifDevices]}
                  rowKey={(r) => `${r.ip}_${r.device_id}`}
                  size="small"
                  pagination={false}
                  columns={[
                    { title: 'IP Address', dataIndex: 'ip', key: 'ip', render: (t: string) => <span className="mono-text">{t}</span> },
                    { title: 'Device ID / Model', key: 'model', render: (_: any, r: any) => `${r.device_id} (${r.hw_model})` },
                    { title: 'Pabrikan', dataIndex: 'manufacturer', key: 'manufacturer' },
                    { title: 'Status RTSP / Patch', dataIndex: 'sd_patch_status', key: 'sd_patch_status', render: (t: string) => <Tag icon={<CheckCircleOutlined />} color="success">{t}</Tag> },
                    {
                      title: 'Integrasi',
                      key: 'add',
                      render: (_: any, r: any) => (
                        <Button size="small" type="primary" onClick={() => handleQuickAddDiscovered(r)}>
                          + Tambahkan ke NVR
                        </Button>
                      ),
                    },
                  ]}
                />

                {v380Guide && (
                  <Card size="small" title="Panduan Aktivasi RTSP Kamera V380 via MicroSD (Ref: Arkady23/V380-Web)">
                    <ol style={{ margin: 0, paddingLeft: 20 }}>
                      {(v380Guide.steps || []).map((st: string, i: number) => (
                        <li key={i} style={{ marginBottom: 4 }}>{st}</li>
                      ))}
                    </ol>
                  </Card>
                )}
              </Space>
            ),
          },
          {
            key: 'users',
            label: '👥 Manajemen Pengguna (RBAC)',
            children: (
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Title level={5} style={{ margin: 0 }}>Daftar Akun Operator & Administrator</Title>
                  <Button type="primary" icon={<UserAddOutlined />} onClick={() => setUserModalOpen(true)}>
                    Tambah Pengguna
                  </Button>
                </div>
                <Table
                  dataSource={users}
                  rowKey="username"
                  size="small"
                  pagination={false}
                  columns={[
                    { title: 'Username', dataIndex: 'username', key: 'username', render: (t: string) => <Text strong>{t}</Text> },
                    { title: 'Nama Lengkap', dataIndex: 'full_name', key: 'full_name' },
                    { title: 'Email', dataIndex: 'email', key: 'email' },
                    {
                      title: 'Peran (Role)',
                      dataIndex: 'role',
                      key: 'role',
                      render: (r: string, rec: any) =>
                        rec.username === 'admin' ? (
                          <Tag color="blue">{r} (Root)</Tag>
                        ) : (
                          <Select
                            size="small"
                            value={r}
                            onChange={(val) => handleChangeUserRole(rec.username, val)}
                            style={{ width: 120 }}
                            options={[
                              { value: 'ADMIN', label: 'ADMIN' },
                              { value: 'OPERATOR', label: 'OPERATOR' },
                            ]}
                          />
                        ),
                    },
                    {
                      title: 'Aksi',
                      key: 'action',
                      render: (_: any, rec: any) =>
                        rec.username === 'admin' ? null : (
                          <Popconfirm title={`Hapus pengguna ${rec.username}?`} onConfirm={() => handleDeleteUser(rec.username)}>
                            <Button size="small" danger icon={<DeleteOutlined />} />
                          </Popconfirm>
                        ),
                    },
                  ]}
                />
              </Space>
            ),
          },
        ]}
      />

      {/* Modal Tambah Kamera */}
      <Modal
        title="Tambah / Konfigurasi Kamera CCTV"
        open={camModalOpen}
        onCancel={() => setCamModalOpen(false)}
        onOk={handleSaveCamera}
        okText="Simpan Kamera"
      >
        <Form layout="vertical">
          <Form.Item label="Nama Kamera" required>
            <Input value={camName} onChange={(e) => setCamName(e.target.value)} placeholder="Contoh: Kamera Koridor Timur" />
          </Form.Item>
          <Form.Item label="Lokasi Pemasangan">
            <Input value={camLocation} onChange={(e) => setCamLocation(e.target.value)} placeholder="Contoh: Lantai 2 - Ruang Server" />
          </Form.Item>
          <Form.Item label="Sumber Stream (RTSP URL atau Simulator AI)">
            <Select
              value={camStreamUrl}
              onChange={(v) => setCamStreamUrl(v)}
              options={[
                { value: 'synthetic_lobby', label: 'Simulator AI: Lobby Utama (People & Face)' },
                { value: 'synthetic_parking', label: 'Simulator AI: Area Parkir (Vehicles & Loitering)' },
                { value: 'synthetic_gate', label: 'Simulator AI: Gerbang Kargo V380 (Trucks)' },
                { value: 'synthetic_warehouse', label: 'Simulator AI: Gudang & Brankas (Intrusion)' },
              ]}
            />
          </Form.Item>
          <Form.Item label="Atau Masukkan RTSP URL Kustom (rtsp://...)">
            <Input value={camStreamUrl} onChange={(e) => setCamStreamUrl(e.target.value)} />
          </Form.Item>
          <Space size="large">
            <Form.Item label="Traffic Counting">
              <Switch checked={enableCounting} onChange={(v) => setEnableCounting(v)} />
            </Form.Item>
            <Form.Item label="Intrusion & Loitering">
              <Switch checked={enableSuspicious} onChange={(v) => setEnableSuspicious(v)} />
            </Form.Item>
            <Form.Item label="Face Vector 512-d">
              <Switch checked={enableFaceRec} onChange={(v) => setEnableFaceRec(v)} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      {/* Modal Tambah User */}
      <Modal
        title="Tambah Akun Pengguna Baru"
        open={userModalOpen}
        onCancel={() => setUserModalOpen(false)}
        onOk={handleCreateUser}
        okText="Buat Akun"
      >
        <Form layout="vertical">
          <Form.Item label="Username" required>
            <Input value={newUsername} onChange={(e) => setNewUsername(e.target.value)} />
          </Form.Item>
          <Form.Item label="Password (minimal 6 karakter)" required>
            <Input.Password value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
          </Form.Item>
          <Form.Item label="Nama Lengkap">
            <Input value={newFullName} onChange={(e) => setNewFullName(e.target.value)} />
          </Form.Item>
          <Form.Item label="Role">
            <Select
              value={newRole}
              onChange={(v) => setNewRole(v)}
              options={[
                { value: 'ADMIN', label: 'ADMIN (Akses Penuh)' },
                { value: 'OPERATOR', label: 'OPERATOR (Monitoring & PTZ)' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

