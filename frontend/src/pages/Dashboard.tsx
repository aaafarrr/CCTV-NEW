import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Select, Button, Space, Typography, Progress, Badge } from 'antd';
import {
  VideoCameraOutlined,
  UserOutlined,
  CarOutlined,
  AlertOutlined,
  CloudServerOutlined,
  ReloadOutlined,
  ArrowUpOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { ENTERPRISE_TOKENS } from '../theme/enterpriseTheme';

const { Title, Text } = Typography;

interface DashboardProps {
  onNavigate: (tab: string) => void;
}

export const DashboardPage: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [timeRange, setTimeRange] = useState('today');
  const [summary, setSummary] = useState<any>(null);
  const [chartData, setChartData] = useState<any>(null);
  const [storageInfo, setStorageInfo] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [sumRes, chartRes, storeRes] = await Promise.all([
        fetch(`/api/v1/analytics/summary?time_range=${timeRange}`),
        fetch(`/api/v1/analytics/chart-data?time_range=${timeRange}`),
        fetch('/api/v1/storage/overview'),
      ]);
      if (sumRes.ok) setSummary(await sumRes.json());
      if (chartRes.ok) setChartData(await chartRes.json());
      if (storeRes.ok) setStorageInfo(await storeRes.json());
    } catch {
      // silent fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const timer = setInterval(fetchDashboardData, 6000);
    return () => clearInterval(timer);
  }, [timeRange]);

  const cameraColumns = [
    {
      title: 'Kamera CCTV',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: any) => (
        <div>
          <Text strong>{text}</Text>
          <div style={{ fontSize: 12, color: ENTERPRISE_TOKENS.textSecondary }}>{record.location}</div>
        </div>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Badge
          status={status === 'ONLINE' ? 'success' : 'default'}
          text={<Tag color={status === 'ONLINE' ? 'success' : 'default'}>{status}</Tag>}
        />
      ),
    },
    {
      title: 'Pejalan Kaki (IN / OUT)',
      key: 'people',
      render: (_: any, r: any) => (
        <Space>
          <Tag color="cyan">{r.people_in} IN</Tag>
          <Tag>{r.people_out} OUT</Tag>
        </Space>
      ),
    },
    {
      title: 'Kendaraan (IN)',
      dataIndex: 'vehicles_in',
      key: 'vehicles_in',
      render: (v: number) => <Tag color="purple">{v} Unit</Tag>,
    },
    {
      title: 'FPS / AI Engine',
      dataIndex: 'fps',
      key: 'fps',
      render: (fps: number) => <span className="mono-text">{fps} FPS (Motion Pre-Filter)</span>,
    },
    {
      title: 'Aksi',
      key: 'action',
      render: () => (
        <Button size="small" type="link" icon={<EyeOutlined />} onClick={() => onNavigate('live')}>
          Pantau Live
        </Button>
      ),
    },
  ];

  const labels: string[] = chartData?.labels || [];
  const peopleSeries: number[] = chartData?.datasets?.[0]?.data || [];
  const vehicleSeries: number[] = chartData?.datasets?.[1]?.data || [];
  const maxVal = Math.max(10, ...peopleSeries, ...vehicleSeries);

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {/* Header Filter Bar */}
      <Card size="small">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>Dashboard Operasional Keamanan & AI Analitik</Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Zona Waktu: {summary?.timezone_name || 'WIB (UTC+7)'} • Pemantauan Multi-Kamera Real-time
            </Text>
          </div>

          <Space>
            <Select
              value={timeRange}
              onChange={(val) => setTimeRange(val)}
              style={{ width: 170 }}
              options={[
                { value: 'today', label: 'Hari Ini (Real-time)' },
                { value: '24h', label: '24 Jam Terakhir' },
                { value: '7d', label: '7 Hari Terakhir' },
                { value: '30d', label: '30 Hari Terakhir' },
              ]}
            />
            <Button icon={<ReloadOutlined spin={loading} />} onClick={fetchDashboardData}>
              Segarkan
            </Button>
            <Button type="primary" icon={<VideoCameraOutlined />} onClick={() => onNavigate('live')}>
              Buka Live Matrix
            </Button>
          </Space>
        </div>
      </Card>

      {/* Top 4 KPI Cards */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" style={{ borderTop: `3px solid ${ENTERPRISE_TOKENS.statusOnline}` }}>
            <Statistic
              title="Kamera CCTV Aktif"
              value={summary?.active_cameras ?? 4}
              suffix="Unit Online"
              prefix={<VideoCameraOutlined style={{ color: ENTERPRISE_TOKENS.statusOnline }} />}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: ENTERPRISE_TOKENS.textSecondary }}>
              Semua stream terhubung (25 FPS)
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card size="small" style={{ borderTop: `3px solid ${ENTERPRISE_TOKENS.badgePerson}` }}>
            <Statistic
              title="Total Pejalan Kaki (Foot Traffic)"
              value={summary?.people_count ?? 27}
              prefix={<UserOutlined style={{ color: ENTERPRISE_TOKENS.badgePerson }} />}
              suffix={
                <Tag color="success" style={{ marginLeft: 8 }}>
                  <ArrowUpOutlined /> {summary?.people_growth_pct ?? 14.5}%
                </Tag>
              }
            />
            <div style={{ marginTop: 8, fontSize: 12, color: ENTERPRISE_TOKENS.textSecondary }}>
              Okupansi Saat Ini: <strong>{summary?.stats?.current_occupancy ?? 9} Orang</strong>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card size="small" style={{ borderTop: `3px solid ${ENTERPRISE_TOKENS.badgeVehicle}` }}>
            <Statistic
              title="Total Kendaraan Terdeteksi"
              value={summary?.vehicle_count ?? 38}
              prefix={<CarOutlined style={{ color: ENTERPRISE_TOKENS.badgeVehicle }} />}
              suffix={
                <Tag color="purple" style={{ marginLeft: 8 }}>
                  <ArrowUpOutlined /> {summary?.vehicle_growth_pct ?? 8.2}%
                </Tag>
              }
            />
            <div style={{ marginTop: 8, fontSize: 12, color: ENTERPRISE_TOKENS.textSecondary }}>
              Mobil: {summary?.vehicle_breakdown?.cars ?? 21} • Motor: {summary?.vehicle_breakdown?.motorcycles ?? 11} • Truk: {summary?.vehicle_breakdown?.trucks ?? 4}
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card size="small" style={{ borderTop: `3px solid ${ENTERPRISE_TOKENS.alertDanger}` }}>
            <Statistic
              title="Insiden & Peringatan AI"
              value={summary?.active_alerts ?? 4}
              prefix={<AlertOutlined style={{ color: ENTERPRISE_TOKENS.alertDanger }} />}
              suffix={
                <Tag color="error" style={{ marginLeft: 8 }}>
                  {summary?.alerts_breakdown?.critical ?? 2} Kritis
                </Tag>
              }
            />
            <div style={{ marginTop: 8, fontSize: 12 }}>
              <a onClick={() => onNavigate('events')}>Lihat Log Insiden & Ringkasan AI →</a>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Traffic Chart + Cloud Storage Pool Status */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card
            size="small"
            title="Grafik Tren Lalu Lintas Objek (Pejalan Kaki vs Kendaraan)"
            extra={
              <Space>
                <Tag color="#06b6d4">Pejalan Kaki</Tag>
                <Tag color="#8b5cf6">Kendaraan</Tag>
              </Space>
            }
          >
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10, height: 210, padding: '16px 8px 4px 8px' }}>
              {labels.map((lbl, i) => {
                const pVal = peopleSeries[i] || 0;
                const vVal = vehicleSeries[i] || 0;
                const pHeight = Math.max(8, Math.round((pVal / maxVal) * 155));
                const vHeight = Math.max(8, Math.round((vVal / maxVal) * 155));
                return (
                  <div key={lbl} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 165 }}>
                      <div
                        title={`Pejalan Kaki: ${pVal}`}
                        style={{
                          width: 12,
                          height: pHeight,
                          background: ENTERPRISE_TOKENS.badgePerson,
                          borderRadius: '4px 4px 0 0',
                        }}
                      />
                      <div
                        title={`Kendaraan: ${vVal}`}
                        style={{
                          width: 12,
                          height: vHeight,
                          background: ENTERPRISE_TOKENS.badgeVehicle,
                          borderRadius: '4px 4px 0 0',
                        }}
                      />
                    </div>
                    <div className="mono-text" style={{ fontSize: 11, color: ENTERPRISE_TOKENS.textSecondary, marginTop: 6 }}>
                      {lbl}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card
            size="small"
            title={
              <Space>
                <CloudServerOutlined style={{ color: ENTERPRISE_TOKENS.primaryColor }} />
                <span>Multi-Cloud Storage Pool (Clospol)</span>
              </Space>
            }
            extra={<a onClick={() => onNavigate('storage')}>Kelola Pool</a>}
          >
            <div style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <Text type="secondary">Kapasitas Terpakai Gabungan:</Text>
                <Text strong>{storageInfo?.total_used_gb ?? 1626.7} GB / {storageInfo?.total_quota_gb ?? 8500} GB</Text>
              </div>
              <Progress percent={storageInfo?.usage_percent ?? 19.1} status="active" strokeColor={ENTERPRISE_TOKENS.primaryColor} />
            </div>

            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              {(storageInfo?.providers || []).slice(0, 3).map((prov: any) => (
                <div
                  key={prov.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '6px 10px',
                    borderRadius: 6,
                    background: ENTERPRISE_TOKENS.bgSubtle,
                    border: `1px solid ${ENTERPRISE_TOKENS.borderLight}`,
                  }}
                >
                  <div>
                    <Text strong style={{ fontSize: 12 }}>{prov.name}</Text>
                    <div style={{ fontSize: 11, color: ENTERPRISE_TOKENS.textSecondary }}>{prov.tier} • {prov.used_gb} / {prov.quota_gb} GB</div>
                  </div>
                  <Tag color={prov.status === 'CONNECTED' ? 'success' : 'default'}>{prov.status}</Tag>
                </div>
              ))}
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Camera Health Matrix Table */}
      <Card size="small" title="Matriks Status Kesehatan & Telemetri Kamera">
        <Table
          dataSource={summary?.camera_health || []}
          columns={cameraColumns}
          rowKey="id"
          pagination={false}
          size="small"
        />
      </Card>
    </Space>
  );
};
