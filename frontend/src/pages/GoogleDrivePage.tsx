import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  Space,
  Typography,
  Progress,
  Modal,
  Form,
  Input,
  Alert,
  message,
} from 'antd';
import {
  GoogleOutlined,
  CloudUploadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  FolderOpenOutlined,
  HddOutlined,
  SettingOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { ENTERPRISE_TOKENS } from '../theme/enterpriseTheme';
import { apiFetch } from '../utils/api';

const { Title, Text, Paragraph } = Typography;

export const GoogleDrivePage: React.FC = () => {
  const [statusData, setStatusData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  // Form State
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [refreshToken, setRefreshToken] = useState('');
  const [rootFolder, setRootFolder] = useState('CCTV Recordings');

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/google-drive/status');
      if (res.ok) {
        const data = await res.json();
        setStatusData(data);
        if (data.root_folder) setRootFolder(data.root_folder);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleSaveConfig = async () => {
    if (!clientId.trim() || !clientSecret.trim() || !refreshToken.trim()) {
      message.warning('Lengkapi Client ID, Client Secret, dan Refresh Token');
      return;
    }
    setSaving(true);
    try {
      const res = await apiFetch('/api/google-drive/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: clientId.trim(),
          client_secret: clientSecret.trim(),
          refresh_token: refreshToken.trim(),
          root_folder_name: rootFolder.trim() || 'CCTV Recordings',
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Gagal menyimpan kredensial Google Drive');
      }

      message.success('Koneksi Google Drive berhasil diverifikasi & disimpan!');
      setModalOpen(false);
      fetchStatus();
    } catch (e: any) {
      message.error(e.message || 'Error koneksi');
    } finally {
      setSaving(false);
    }
  };

  const isConnected = statusData?.is_configured && statusData?.quota?.configured;
  const quota = statusData?.quota || {};
  const totalGb = quota.total_bytes ? (quota.total_bytes / (1024 * 1024 * 1024)).toFixed(1) : 'Unlimited';
  const usedGb = quota.used_bytes ? (quota.used_bytes / (1024 * 1024 * 1024)).toFixed(2) : '0';
  const usedPct = quota.used_percentage || 0;

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card size="small">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              <GoogleOutlined style={{ color: '#ea4335', marginRight: 8 }} />
              Penyimpanan Google Drive (Clospol Cloud Integration)
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Arsip rekaman CCTV dan snapshot gambar otomatis diunggah ke Google Drive dengan struktur folder hirarki: <strong>CCTV Recordings → [Nama Kamera] → YYYY-MM</strong>
            </Text>
          </div>

          <Space>
            <Button icon={<SyncOutlined spin={loading} />} onClick={fetchStatus}>
              Segarkan
            </Button>
            <Button type="primary" icon={<SettingOutlined />} onClick={() => setModalOpen(true)}>
              Konfigurasi Google Drive OAuth
            </Button>
          </Space>
        </div>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title="Status Integrasi Cloud"
              value={isConnected ? 'Terhubung' : 'Belum Terhubung'}
              valueStyle={{ color: isConnected ? '#10b981' : '#f59e0b' }}
              prefix={isConnected ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
            />
            <div style={{ marginTop: 6, fontSize: 12, color: ENTERPRISE_TOKENS.textSecondary }}>
              Akun: <strong>{quota.user || 'Belum Login'}</strong>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title="Penggunaan Kuota Google Drive"
              value={`${usedGb} GB`}
              suffix={`/ ${totalGb} GB`}
              prefix={<HddOutlined style={{ color: ENTERPRISE_TOKENS.primaryColor }} />}
            />
            <div style={{ marginTop: 8 }}>
              <Progress percent={usedPct} size="small" strokeColor={ENTERPRISE_TOKENS.primaryColor} />
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title="Folder Root CCTV di Google Drive"
              value={statusData?.root_folder || 'CCTV Recordings'}
              prefix={<FolderOpenOutlined style={{ color: '#f59e0b' }} />}
            />
            <div style={{ marginTop: 6, fontSize: 12, color: ENTERPRISE_TOKENS.textSecondary }}>
              Auto-create subfolder bulanan aktif
            </div>
          </Card>
        </Col>
      </Row>

      <Card size="small" title="Struktur Penyimpanan Rekaman Clospol">
        <Paragraph>
          Setiap snapshot dan video clip yang disimpan dari kamera CCTV secara otomatis dialokasikan ke folder virtual di Google Drive Anda:
        </Paragraph>
        <div style={{ background: '#f8fafc', padding: 14, borderRadius: 8, border: '1px solid #e2e8f0', fontFamily: 'monospace', fontSize: 13 }}>
          <div>📁 My Drive /</div>
          <div style={{ paddingLeft: 20 }}>└── 📁 {statusData?.root_folder || 'CCTV Recordings'} /</div>
          <div style={{ paddingLeft: 44 }}>└── 📁 Kamera Lobby Utama /</div>
          <div style={{ paddingLeft: 68 }}>└── 📁 2026-11 /</div>
          <div style={{ paddingLeft: 92 }}>├── 🎥 cctv_kamera_lobby_utama_20261108_183000.mp4</div>
          <div style={{ paddingLeft: 92 }}>└── 📷 cctv_kamera_lobby_utama_20261108_183015.jpg</div>
        </div>
      </Card>

      <Modal
        title="Pengaturan Google Drive API (OAuth2)"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSaveConfig}
        confirmLoading={saving}
        okText="Simpan & Uji Koneksi"
      >
        <Alert
          type="info"
          showIcon
          message="Panduan Kredensial Google Cloud Console"
          description="Buat OAuth 2.0 Client ID (Web Application) di Google Cloud Console dengan scope Google Drive API, lalu ambil Refresh Token Anda."
          style={{ marginBottom: 16 }}
        />

        <Form layout="vertical">
          <Form.Item label="Google Client ID" required>
            <Input value={clientId} onChange={(e) => setClientId(e.target.value)} placeholder="xxxxx.apps.googleusercontent.com" />
          </Form.Item>

          <Form.Item label="Google Client Secret" required>
            <Input.Password value={clientSecret} onChange={(e) => setClientSecret(e.target.value)} placeholder="Client Secret dari Google Console" />
          </Form.Item>

          <Form.Item label="Google OAuth Refresh Token" required>
            <Input.Password value={refreshToken} onChange={(e) => setRefreshToken(e.target.value)} placeholder="Refresh Token OAuth2" />
          </Form.Item>

          <Form.Item label="Nama Folder Root di Google Drive">
            <Input value={rootFolder} onChange={(e) => setRootFolder(e.target.value)} placeholder="CCTV Recordings" />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
};

