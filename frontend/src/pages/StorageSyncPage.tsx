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
  Switch,
  Alert,
  message,
} from 'antd';
import {
  CloudServerOutlined,
  CloudUploadOutlined,
  SettingOutlined,
  HddOutlined,
  SafetyOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { ENTERPRISE_TOKENS } from '../theme/enterpriseTheme';
import { apiFetch } from '../utils/api';

const { Title, Text } = Typography;

export const StorageSyncPage: React.FC = () => {
  const [overview, setOverview] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  // Policy Form State
  const [s3Bucket, setS3Bucket] = useState('');
  const [s3Endpoint, setS3Endpoint] = useState('');
  const [s3Region, setS3Region] = useState('auto');
  const [s3Prefix, setS3Prefix] = useState('cctv');
  const [localDays, setLocalDays] = useState(7);
  const [cloudDays, setCloudDays] = useState(90);
  const [autoSync, setAutoSync] = useState(true);

  const fetchOverview = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/v1/storage/overview');
      if (res.ok) {
        const data = await res.json();
        setOverview(data);
        if (data.policy) {
          setS3Bucket(data.policy.s3_bucket || '');
          setS3Endpoint(data.policy.s3_endpoint_url || '');
          setS3Region(data.policy.s3_region || 'auto');
          setS3Prefix(data.policy.s3_prefix || 'cctv');
          setLocalDays(data.policy.local_retention_days || 7);
          setCloudDays(data.policy.cloud_retention_days || 90);
          setAutoSync(data.policy.auto_sync_critical_events ?? true);
        }
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  const handleSavePolicy = async () => {
    try {
      const res = await apiFetch('/api/v1/storage/policy', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          s3_bucket: s3Bucket.trim(),
          s3_endpoint_url: s3Endpoint.trim(),
          s3_region: s3Region.trim(),
          s3_prefix: s3Prefix.trim(),
          local_retention_days: localDays,
          cloud_retention_days: cloudDays,
          auto_sync_critical_events: autoSync,
        }),
      });
      if (!res.ok) throw new Error('Gagal menyimpan konfigurasi');
      message.success('Konfigurasi S3 Cloud Storage berhasil diperbarui');
      setModalOpen(false);
      fetchOverview();
    } catch (e: any) {
      message.error(e.message || 'Gagal menyimpan');
    }
  };

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card size="small">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              <CloudServerOutlined style={{ color: ENTERPRISE_TOKENS.primaryColor, marginRight: 8 }} />
              S3 Object Storage & Cloud Archival (Boto3 Engine)
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Integrasi langsung AWS S3, Cloudflare R2, MinIO, atau Wasabi untuk pengarsipan snapshot dan bukti rekaman insiden.
            </Text>
          </div>

          <Button type="primary" icon={<SettingOutlined />} onClick={() => setModalOpen(true)}>
            Atur Konfigurasi S3 & Retensi
          </Button>
        </div>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title="Status Koneksi S3"
              value={overview?.s3_configured ? 'Terhubung' : 'Belum Terhubung'}
              valueStyle={{ color: overview?.s3_configured ? '#10b981' : '#f59e0b' }}
              prefix={overview?.s3_configured ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
            />
            <div style={{ marginTop: 6, fontSize: 12, color: ENTERPRISE_TOKENS.textSecondary }}>
              Bucket: <strong>{overview?.s3_bucket || '-'}</strong>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title="Penyimpanan Lokal Snapshot"
              value={overview?.local_used_mb ?? 0}
              suffix="MB"
              prefix={<HddOutlined style={{ color: ENTERPRISE_TOKENS.primaryColor }} />}
            />
            <div style={{ marginTop: 6, fontSize: 12, color: ENTERPRISE_TOKENS.textSecondary }}>
              Total File Snapshot: <strong>{overview?.local_snapshots_count ?? 0} File</strong>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title="Kebijakan Retensi Data"
              value={`${overview?.policy?.local_retention_days ?? 7} Hari Lokal`}
              prefix={<SafetyOutlined style={{ color: ENTERPRISE_TOKENS.badgeVehicle }} />}
            />
            <div style={{ marginTop: 6, fontSize: 12, color: ENTERPRISE_TOKENS.textSecondary }}>
              Auto-Sync Insiden Kritis: <strong>{overview?.policy?.auto_sync_critical_events ? 'Aktif' : 'Nonaktif'}</strong>
            </div>
          </Card>
        </Col>
      </Row>

      <Card size="small" title="Riwayat Job Upload ke S3 Cloud Storage">
        <Table
          dataSource={overview?.recent_jobs || []}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 5 }}
          columns={[
            { title: 'Nama File', dataIndex: 'filename', key: 'filename', render: (t: string) => <span className="mono-text">{t}</span> },
            { title: 'S3 Key / Lokasi', dataIndex: 's3_key', key: 's3_key', render: (k: string) => <Tag color="blue">{k || 'Lokal'}</Tag> },
            { title: 'Ukuran', dataIndex: 'size_mb', key: 'size_mb', render: (v: number) => `${v} MB` },
            {
              title: 'Status',
              dataIndex: 'status',
              key: 'status',
              render: (s: string) => (
                <Tag color={s === 'COMPLETED' ? 'success' : s === 'FAILED' ? 'error' : 'default'}>{s}</Tag>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="Pengaturan S3 Object Storage & Retensi"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSavePolicy}
        okText="Simpan Konfigurasi"
      >
        <Form layout="vertical">
          <Form.Item label="S3 Bucket Name" required>
            <Input value={s3Bucket} onChange={(e) => setS3Bucket(e.target.value)} placeholder="Contoh: cctv-enterprise-bucket" />
          </Form.Item>
          <Form.Item label="S3 Endpoint URL (Kosongkan jika menggunakan AWS Default)">
            <Input value={s3Endpoint} onChange={(e) => setS3Endpoint(e.target.value)} placeholder="Contoh: https://<account>.r2.cloudflarestorage.com" />
          </Form.Item>
          <Form.Item label="AWS Region">
            <Input value={s3Region} onChange={(e) => setS3Region(e.target.value)} placeholder="auto atau us-east-1" />
          </Form.Item>
          <Form.Item label="Prefix / Folder Path di S3">
            <Input value={s3Prefix} onChange={(e) => setS3Prefix(e.target.value)} placeholder="cctv" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="Retensi Lokal (Hari)">
                <InputNumber value={localDays} onChange={(v) => setLocalDays(Number(v || 7))} min={1} max={365} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Retensi Cloud (Hari)">
                <InputNumber value={cloudDays} onChange={(v) => setCloudDays(Number(v || 90))} min={7} max={3650} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="Auto-Upload Bukti Insiden Kritis ke Cloud">
            <Switch checked={autoSync} onChange={(v) => setAutoSync(v)} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
};
