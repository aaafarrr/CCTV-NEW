import React, { useEffect, useState } from 'react';
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
  InputNumber,
  Select,
  Switch,
  message,
} from 'antd';
import {
  CloudServerOutlined,
  CloudSyncOutlined,
  PlusOutlined,
  DeleteOutlined,
  PoweroffOutlined,
  HddOutlined,
  SafetyOutlined,
} from '@ant-design/icons';
import { ENTERPRISE_TOKENS } from '../theme/enterpriseTheme';
import { apiFetch } from '../utils/api';

const { Title, Text } = Typography;

export const StorageSyncPage: React.FC = () => {
  const [overview, setOverview] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [addModalOpen, setAddModalOpen] = useState(false);

  // Add Provider State
  const [provName, setProvName] = useState('');
  const [provType, setProvType] = useState('GOOGLE_DRIVE');
  const [provEndpoint, setProvEndpoint] = useState('gdrive://cctv-backup-bucket');
  const [provTier, setProvTier] = useState('WARM (Tier 2)');
  const [provQuota, setProvQuota] = useState<number>(1000);

  const fetchOverview = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/storage/overview');
      if (res.ok) setOverview(await res.json());
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  const handleTriggerSync = async () => {
    setSyncing(true);
    try {
      const res = await apiFetch('/api/v1/storage/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          camera_name: 'Semua Kamera Aktif (Pool)',
          reason: 'Sinkronisasi Manual Operator',
        }),
      });
      if (res.ok) {
        const job = await res.json();
        message.success(`Arsip ${job.filename} berhasil disinkronkan ke ${job.target_provider}`);
        fetchOverview();
      }
    } catch {
      message.error('Gagal menjalankan sinkronisasi cloud');
    } finally {
      setSyncing(false);
    }
  };

  const handleAddProvider = async () => {
    if (!provName.trim() || !provEndpoint.trim()) {
      message.warning('Lengkapi nama dan endpoint provider terlebih dahulu');
      return;
    }
    try {
      const res = await apiFetch('/api/v1/storage/providers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: provName.trim(),
          type: provType,
          endpoint: provEndpoint.trim(),
          tier: provTier,
          quota_gb: provQuota,
        }),
      });
      if (res.ok) {
        message.success(`Provider ${provName} ditambahkan ke Storage Pool`);
        setAddModalOpen(false);
        setProvName('');
        fetchOverview();
      }
    } catch {
      message.error('Gagal menambahkan provider');
    }
  };

  const handleToggleProvider = async (id: string) => {
    await apiFetch(`/api/v1/storage/providers/${id}/toggle`, { method: 'PUT' });
    fetchOverview();
  };

  const handleDeleteProvider = async (id: string) => {
    const res = await apiFetch(`/api/v1/storage/providers/${id}`, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json();
      message.error(err.detail || 'Gagal menghapus provider');
      return;
    }
    message.success('Provider dihapus dari pool');
    fetchOverview();
  };

  const handleToggleAutoTiering = async (enabled: boolean) => {
    if (!overview?.policy) return;
    await apiFetch('/api/v1/storage/policy', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...overview.policy,
        auto_tiering_enabled: enabled,
      }),
    });
    message.success(`Auto-Tiering ${enabled ? 'Diaktifkan' : 'Dinonaktifkan'}`);
    fetchOverview();
  };

  const providerColumns = [
    {
      title: 'Nama Storage Provider',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, r: any) => (
        <div>
          <Text strong>{name}</Text>
          <div className="mono-text" style={{ fontSize: 11, color: ENTERPRISE_TOKENS.textSecondary }}>{r.endpoint}</div>
        </div>
      ),
    },
    {
      title: 'Tipe & Tier',
      key: 'tier',
      render: (_: any, r: any) => (
        <Space>
          <Tag color="blue">{r.type}</Tag>
          <Tag color="purple">{r.tier}</Tag>
        </Space>
      ),
    },
    {
      title: 'Kapasitas Terpakai',
      key: 'usage',
      width: 240,
      render: (_: any, r: any) => {
        const pct = Math.round(((r.used_gb || 0) / Math.max(1, r.quota_gb || 1)) * 100);
        return (
          <div>
            <div style={{ fontSize: 12 }}>{r.used_gb} GB / {r.quota_gb} GB ({pct}%)</div>
            <Progress percent={pct} size="small" strokeColor={ENTERPRISE_TOKENS.primaryColor} showInfo={false} />
          </div>
        );
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (st: string) => (
        <Tag color={st === 'CONNECTED' ? 'success' : 'default'}>{st}</Tag>
      ),
    },
    {
      title: 'Aksi',
      key: 'action',
      render: (_: any, r: any) => (
        <Space>
          <Button size="small" icon={<PoweroffOutlined />} onClick={() => handleToggleProvider(r.id)}>
            Toggle
          </Button>
          {r.id !== 'prov_local_nvme' && (
            <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDeleteProvider(r.id)} />
          )}
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card size="small">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              <CloudServerOutlined style={{ color: ENTERPRISE_TOKENS.primaryColor, marginRight: 8 }} />
              Multi-Cloud Storage Pool & Auto-Tiering Gateway (Clospol Engine)
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Penggabungan disk lokal NVMe dengan Google Drive, OneDrive, dan S3/Cloudflare R2 untuk retensi rekaman hemat biaya
            </Text>
          </div>

          <Space>
            <Button icon={<PlusOutlined />} onClick={() => setAddModalOpen(true)}>
              Tambah Cloud Provider
            </Button>
            <Button type="primary" icon={<CloudSyncOutlined spin={syncing} />} loading={syncing} onClick={handleTriggerSync}>
              Sinkronkan Klip ke Cloud Sekarang
            </Button>
          </Space>
        </div>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title="Total Kapasitas Pool Gabungan"
              value={overview?.total_quota_gb ?? 8500}
              suffix="GB"
              prefix={<HddOutlined style={{ color: ENTERPRISE_TOKENS.primaryColor }} />}
            />
            <div style={{ marginTop: 6, fontSize: 12, color: ENTERPRISE_TOKENS.textSecondary }}>
              Tersedia Bebas: <strong>{overview?.free_gb ?? 6873.3} GB</strong>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title="Provider Cloud Terhubung"
              value={overview?.connected_providers ?? 3}
              suffix={`/ ${overview?.total_providers ?? 4} Node`}
              prefix={<CloudServerOutlined style={{ color: ENTERPRISE_TOKENS.statusOnline }} />}
            />
            <div style={{ marginTop: 6, fontSize: 12, color: ENTERPRISE_TOKENS.textSecondary }}>
              Strategi Routing: <strong>{overview?.policy?.routing_strategy || 'WEIGHTED_FAILOVER'}</strong>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Statistic
                title="Kebijakan Auto-Tiering & Pre-Alarm"
                value={`${overview?.policy?.local_retention_hours ?? 48} Jam Lokal`}
                prefix={<SafetyOutlined style={{ color: ENTERPRISE_TOKENS.badgeVehicle }} />}
              />
              <Switch
                checked={overview?.policy?.auto_tiering_enabled ?? true}
                onChange={handleToggleAutoTiering}
              />
            </div>
            <div style={{ marginTop: 6, fontSize: 12, color: ENTERPRISE_TOKENS.textSecondary }}>
              Pre-Event Buffer: <strong>{overview?.policy?.pre_event_buffer_sec ?? 5}s</strong> • Arsip Cloud: <strong>{overview?.policy?.cloud_retention_days ?? 90} Hari</strong>
            </div>
          </Card>
        </Col>
      </Row>

      <Card size="small" title="Daftar Storage Provider dalam Pool">
        <Table
          dataSource={overview?.providers || []}
          columns={providerColumns}
          rowKey="id"
          loading={loading}
          pagination={false}
          size="small"
        />
      </Card>

      <Card size="small" title="Riwayat Job Sinkronisasi & Tiering Rekaman">
        <Table
          dataSource={overview?.recent_jobs || []}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 5 }}
          columns={[
            { title: 'Nama File Klip / Bundle', dataIndex: 'filename', key: 'filename', render: (t: string) => <span className="mono-text">{t}</span> },
            { title: 'Kamera Sumber', dataIndex: 'source_camera', key: 'source_camera' },
            { title: 'Target Cloud Provider', dataIndex: 'target_provider', key: 'target_provider', render: (t: string) => <Tag color="blue">{t}</Tag> },
            { title: 'Ukuran', dataIndex: 'size_mb', key: 'size_mb', render: (v: number) => `${v} MB` },
            { title: 'Status', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color="success">{s}</Tag> },
          ]}
        />
      </Card>

      <Modal
        title="Hubungkan Cloud Storage Provider Baru ke Pool"
        open={addModalOpen}
        onCancel={() => setAddModalOpen(false)}
        onOk={handleAddProvider}
        okText="Hubungkan Provider"
      >
        <Form layout="vertical">
          <Form.Item label="Nama Provider" required>
            <Input value={provName} onChange={(e) => setProvName(e.target.value)} placeholder="Contoh: Backblaze B2 Cold Archive" />
          </Form.Item>
          <Form.Item label="Tipe Protokol Cloud">
            <Select
              value={provType}
              onChange={(v) => setProvType(v)}
              options={[
                { value: 'GOOGLE_DRIVE', label: 'Google Drive API' },
                { value: 'ONEDRIVE', label: 'Microsoft OneDrive Graph' },
                { value: 'S3_COMPATIBLE', label: 'AWS S3 / Cloudflare R2 / MinIO' },
                { value: 'LOCAL_DISK', label: 'Local / NAS Mount' },
              ]}
            />
          </Form.Item>
          <Form.Item label="URI / Bucket Endpoint" required>
            <Input value={provEndpoint} onChange={(e) => setProvEndpoint(e.target.value)} />
          </Form.Item>
          <Form.Item label="Tier Penyimpanan">
            <Select
              value={provTier}
              onChange={(v) => setProvTier(v)}
              options={[
                { value: 'HOT (Tier 1)', label: 'HOT (Tier 1 - Akses Instan)' },
                { value: 'WARM (Tier 2)', label: 'WARM (Tier 2 - Cloud Standar)' },
                { value: 'COLD (Tier 3)', label: 'COLD (Tier 3 - Arsip Jangka Panjang)' },
              ]}
            />
          </Form.Item>
          <Form.Item label="Kuota Penyimpanan (GB)">
            <InputNumber value={provQuota} onChange={(v) => setProvQuota(Number(v || 500))} min={50} max={50000} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
};

