import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Button, Space, Typography, Progress, Badge } from 'antd';
import {
  VideoCameraOutlined,
  GoogleOutlined,
  FileImageOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  HddOutlined,
} from '@ant-design/icons';
import { ENTERPRISE_TOKENS } from '../theme/enterpriseTheme';
import { apiFetch } from '../utils/api';

const { Title, Text } = Typography;

interface DashboardProps {
  onNavigate: (tab: string) => void;
}

export const DashboardPage: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [cameras, setCameras] = useState<any[]>([]);
  const [gdriveStatus, setGdriveStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [camRes, driveRes] = await Promise.all([
        apiFetch('/api/cctv'),
        apiFetch('/api/google-drive/status'),
      ]);
      if (camRes.ok) {
        const d = await camRes.json();
        setCameras(d.cameras || []);
      }
      if (driveRes.ok) {
        setGdriveStatus(await driveRes.json());
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const totalCameras = cameras.length;
  const activeCameras = cameras.filter((c) => c.status === 'active').length;
  const autoRecordCameras = cameras.filter((c) => c.recordStream).length;

  const quota = gdriveStatus?.quota || {};
  const gdriveConnected = gdriveStatus?.is_configured && quota.configured;
  const totalGb = quota.total_bytes ? (quota.total_bytes / (1024 * 1024 * 1024)).toFixed(1) : 'Unlimited';
  const usedGb = quota.used_bytes ? (quota.used_bytes / (1024 * 1024 * 1024)).toFixed(2) : '0';

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {/* Top Header Card */}
      <Card size="small">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>Dashboard Pengawasan CCTV & Google Drive Archival</Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Sistem CCTV terintegrasi dengan Google Drive Storage Multi-Tier (Clospol Engine)
            </Text>
          </div>

          <Space>
            <Button icon={<ReloadOutlined spin={loading} />} onClick={fetchDashboardData}>
              Segarkan Data
            </Button>
            <Button type="primary" icon={<VideoCameraOutlined />} onClick={() => onNavigate('live')}>
              Buka Live Matrix
            </Button>
          </Space>
        </div>
      </Card>

      {/* KPI Statistic Cards */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card size="small" style={{ borderTop: `3px solid ${ENTERPRISE_TOKENS.statusOnline}` }}>
            <Statistic
              title="Kamera CCTV Terhubung"
              value={activeCameras}
              suffix={`/ ${totalCameras} Unit`}
              prefix={<VideoCameraOutlined style={{ color: ENTERPRISE_TOKENS.statusOnline }} />}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: ENTERPRISE_TOKENS.textSecondary }}>
              Auto-Record Aktif: <strong>{autoRecordCameras} Kamera</strong>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={8}>
          <Card size="small" style={{ borderTop: `3px solid #ea4335` }}>
            <Statistic
              title="Integrasi Google Drive"
              value={gdriveConnected ? 'Terhubung' : 'Belum Terhubung'}
              valueStyle={{ color: gdriveConnected ? '#10b981' : '#f59e0b' }}
              prefix={<GoogleOutlined style={{ color: '#ea4335' }} />}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: ENTERPRISE_TOKENS.textSecondary }}>
              Folder: <strong>{gdriveStatus?.root_folder || 'CCTV Recordings'}</strong>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={8}>
          <Card size="small" style={{ borderTop: `3px solid ${ENTERPRISE_TOKENS.primaryColor}` }}>
            <Statistic
              title="Kapasitas Cloud Terpakai"
              value={`${usedGb} GB`}
              suffix={`/ ${totalGb} GB`}
              prefix={<HddOutlined style={{ color: ENTERPRISE_TOKENS.primaryColor }} />}
            />
            <div style={{ marginTop: 8 }}>
              <Progress percent={quota.used_percentage || 0} size="small" strokeColor={ENTERPRISE_TOKENS.primaryColor} />
            </div>
          </Card>
        </Col>
      </Row>

      {/* Cameras Quick Status Table */}
      <Card size="small" title="Daftar Kamera Aktif & Status Stream">
        <Table
          dataSource={cameras}
          rowKey="id"
          size="small"
          pagination={false}
          columns={[
            {
              title: 'Kamera',
              dataIndex: 'name',
              key: 'name',
              render: (name: string, r: any) => (
                <div>
                  <Text strong>{name}</Text>
                  <div className="mono-text" style={{ fontSize: 11, color: ENTERPRISE_TOKENS.textSecondary }}>{r.streamUrl}</div>
                </div>
              ),
            },
            {
              title: 'Status',
              dataIndex: 'status',
              key: 'status',
              render: (st: string) => <Tag color={st === 'active' ? 'success' : 'default'}>{st.toUpperCase()}</Tag>,
            },
            {
              title: 'Perekaman Otomatis',
              dataIndex: 'recordStream',
              key: 'recordStream',
              render: (v: boolean, r: any) =>
                v ? <Tag color="blue">Tiap {r.recordInterval} Menit</Tag> : <Tag>Manual</Tag>,
            },
            {
              title: 'Retensi',
              dataIndex: 'retentionDays',
              key: 'retentionDays',
              render: (d: number) => `${d} Hari`,
            },
            {
              title: 'Aksi',
              key: 'action',
              render: () => (
                <Button size="small" type="link" icon={<PlayCircleOutlined />} onClick={() => onNavigate('live')}>
                  Lihat Live
                </Button>
              ),
            },
          ]}
        />
      </Card>
    </Space>
  );
};
