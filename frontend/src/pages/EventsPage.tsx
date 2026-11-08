import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Space,
  Button,
  Select,
  Input,
  Typography,
  Popconfirm,
  Modal,
  message,
} from 'antd';
import {
  AlertOutlined,
  DownloadOutlined,
  DeleteOutlined,
  ReloadOutlined,
  CloudUploadOutlined,
  RobotOutlined,
  EyeOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { ENTERPRISE_TOKENS } from '../theme/enterpriseTheme';
import { apiFetch } from '../utils/api';

const { Title, Text } = Typography;

interface EventsPageProps {
  onCriticalTriggered?: () => void;
}

export const EventsPage: React.FC<EventsPageProps> = ({ onCriticalTriggered }) => {
  const [events, setEvents] = useState<any[]>([]);
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [searchText, setSearchText] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedEvent, setSelectedEvent] = useState<any | null>(null);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const q = severityFilter !== 'ALL' ? `?severity=${severityFilter}` : '';
      const res = await apiFetch(`/api/v1/alerts${q}`);
      if (res.ok) {
        setEvents(await res.json());
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [severityFilter]);

  const handleSimulateFall = async () => {
    try {
      const res = await apiFetch('/api/v1/alerts/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_type: 'FALL_DETECTED', camera_id: 'cam_1' }),
      });
      if (!res.ok) throw new Error('Gagal memicu simulasi');
      const data = await res.json();
      message.warning(`ALERT KRITIS: ${data.description}`);
      onCriticalTriggered?.();
      fetchAlerts();
    } catch {
      message.error('Gagal memicu simulasi deteksi jatuh');
    }
  };

  const handleDeleteOne = async (id: string) => {
    try {
      await apiFetch(`/api/v1/alerts/${id}`, { method: 'DELETE' });
      message.success('Log insiden dihapus');
      fetchAlerts();
    } catch {
      message.error('Gagal menghapus log');
    }
  };

  const handleClearAll = async () => {
    try {
      await apiFetch('/api/v1/alerts', { method: 'DELETE' });
      message.success('Seluruh log insiden dibersihkan');
      fetchAlerts();
    } catch {
      message.error('Gagal membersihkan log');
    }
  };

  const handleExportCsv = () => {
    if (events.length === 0) {
      message.warning('Tidak ada data untuk diekspor');
      return;
    }
    const headers = ['ID', 'Waktu', 'Kamera', 'Tipe', 'Severity', 'Deskripsi', 'AI Summary'];
    const rows = events.map((e) => [
      e.id,
      new Date((e.timestamp || 0) * 1000).toISOString(),
      `"${e.camera_name}"`,
      e.event_type,
      e.severity,
      `"${(e.description || '').replace(/"/g, '""')}"`,
      `"${(e.ai_summary || '').replace(/"/g, '""')}"`,
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `cctv_incidents_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filteredEvents = events.filter((ev) => {
    if (!searchText.trim()) return true;
    const s = searchText.toLowerCase();
    return (
      (ev.description || '').toLowerCase().includes(s) ||
      (ev.camera_name || '').toLowerCase().includes(s) ||
      (ev.ai_summary || '').toLowerCase().includes(s)
    );
  });

  const columns = [
    {
      title: 'Waktu Kejadian',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 155,
      render: (ts: number) => (
        <span className="mono-text" style={{ fontSize: 12 }}>
          {new Date((ts || Date.now() / 1000) * 1000).toLocaleString('id-ID')}
        </span>
      ),
    },
    {
      title: 'Tingkat & Tipe',
      key: 'severity',
      width: 170,
      render: (_: any, r: any) => (
        <Space direction="vertical" size={2}>
          <Tag color={r.severity === 'CRITICAL' ? 'error' : r.severity === 'WARNING' ? 'warning' : 'processing'}>
            {r.severity}
          </Tag>
          <Tag>{r.event_type}</Tag>
        </Space>
      ),
    },
    {
      title: 'Kamera Sumber',
      dataIndex: 'camera_name',
      key: 'camera_name',
      width: 180,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: 'Deskripsi & Ringkasan Naratif AI (ClearCam / DeepCamera Engine)',
      key: 'description',
      render: (_: any, r: any) => (
        <div>
          <Text strong style={{ display: 'block' }}>{r.description}</Text>
          <div
            style={{
              marginTop: 4,
              padding: '4px 8px',
              background: ENTERPRISE_TOKENS.primaryBg,
              borderRadius: 6,
              fontSize: 12,
              color: ENTERPRISE_TOKENS.textSecondary,
            }}
          >
            <RobotOutlined style={{ color: ENTERPRISE_TOKENS.primaryColor, marginRight: 6 }} />
            {r.ai_summary}
          </div>
        </div>
      ),
    },
    {
      title: 'Arsip Cloud',
      dataIndex: 'cloud_synced',
      key: 'cloud_synced',
      width: 120,
      render: (synced: boolean) =>
        synced ? (
          <Tag icon={<CloudUploadOutlined />} color="success">Tersinkron</Tag>
        ) : (
          <Tag>Lokal Buffer</Tag>
        ),
    },
    {
      title: 'Aksi',
      key: 'action',
      width: 120,
      render: (_: any, r: any) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => setSelectedEvent(r)} />
          <Popconfirm title="Hapus log insiden ini?" onConfirm={() => handleDeleteOne(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
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
              <AlertOutlined style={{ color: ENTERPRISE_TOKENS.alertDanger, marginRight: 8 }} />
              Log Insiden Keamanan & Ringkasan AI
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Pencatatan otomatis Intrusion, Loitering, Fall Detection (DeepCamera), dan Pencocokan Wajah Watchlist
            </Text>
          </div>

          <Space wrap>
            <Input.Search
              placeholder="Cari deskripsi atau kamera..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: 200 }}
              allowClear
            />
            <Select
              value={severityFilter}
              onChange={(v) => setSeverityFilter(v)}
              style={{ width: 145 }}
              options={[
                { value: 'ALL', label: 'Semua Tingkat' },
                { value: 'CRITICAL', label: '🔴 Kritis (Critical)' },
                { value: 'WARNING', label: '🟡 Peringatan (Warning)' },
                { value: 'INFO', label: '🔵 Informasi (Info)' },
              ]}
            />
            <Button type="primary" danger ghost icon={<ThunderboltOutlined />} onClick={handleSimulateFall}>
              Uji Deteksi Jatuh (Fall Alert)
            </Button>
            <Button icon={<ReloadOutlined spin={loading} />} onClick={fetchAlerts}>
              Segarkan
            </Button>
            <Button icon={<DownloadOutlined />} onClick={handleExportCsv}>
              Export CSV
            </Button>
            <Popconfirm title="Bersihkan seluruh log insiden?" onConfirm={handleClearAll}>
              <Button danger icon={<DeleteOutlined />}>Bersihkan</Button>
            </Popconfirm>
          </Space>
        </div>
      </Card>

      <Card size="small">
        <Table
          dataSource={filteredEvents}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 8 }}
          size="small"
        />
      </Card>

      <Modal
        title={`Detail Bukti Insiden — ${selectedEvent?.camera_name || ''}`}
        open={!!selectedEvent}
        onCancel={() => setSelectedEvent(null)}
        footer={[
          <Button key="close" type="primary" onClick={() => setSelectedEvent(null)}>
            Tutup
          </Button>,
        ]}
      >
        {selectedEvent && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <div className="cctv-video-surface" style={{ height: 240 }}>
              <img
                src={selectedEvent.snapshot_url}
                alt="Snapshot Bukti"
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            </div>
            <Text strong>{selectedEvent.description}</Text>
            <div style={{ padding: 10, background: ENTERPRISE_TOKENS.primaryBg, borderRadius: 8 }}>
              <Text>{selectedEvent.ai_summary}</Text>
            </div>
          </Space>
        )}
      </Modal>
    </Space>
  );
};
