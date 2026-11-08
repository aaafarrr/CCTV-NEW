import React, { useEffect, useState, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Tag,
  Space,
  Typography,
  Segmented,
  Modal,
  Form,
  Input,
  Switch,
  Empty,
  Popconfirm,
  message,
} from 'antd';
import {
  SearchOutlined,
  UserAddOutlined,
  EditOutlined,
  DeleteOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  VideoCameraOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { ENTERPRISE_TOKENS } from '../theme/enterpriseTheme';
import { apiFetch } from '../utils/api';

const { Title, Text } = Typography;

interface FaceGalleryProps {
  onOpenSearch: () => void;
}

export const FaceGalleryPage: React.FC<FaceGalleryProps> = ({ onOpenSearch }) => {
  const [clusters, setClusters] = useState<any[]>([]);
  const [filterMode, setFilterMode] = useState<string>('ALL');
  const [registerModalOpen, setRegisterModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingPerson, setEditingPerson] = useState<any | null>(null);

  // Registration Form
  const [regName, setRegName] = useState('');
  const [regNotes, setRegNotes] = useState('');
  const [regWatchlist, setRegWatchlist] = useState(false);
  const [regFile, setRegFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const fetchClusters = async () => {
    try {
      const res = await fetch('/api/v1/faces/people-clusters');
      if (res.ok) {
        setClusters(await res.json());
      }
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchClusters();
  }, []);

  const handleRegisterIdentity = async () => {
    if (!regName.trim() || !regFile) {
      message.warning('Masukkan nama lengkap dan pilih foto wajah terlebih dahulu');
      return;
    }
    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append('name', regName.trim());
      fd.append('notes', regNotes.trim());
      fd.append('is_watchlist', String(regWatchlist));
      fd.append('file', regFile);

      const res = await fetch('/api/v1/search/register-identity', {
        method: 'POST',
        body: fd,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Gagal mendaftarkan wajah');
      }
      message.success(`Identitas ${regName} berhasil diindeks ke Qdrant Vector DB`);
      setRegisterModalOpen(false);
      setRegName('');
      setRegNotes('');
      setRegWatchlist(false);
      setRegFile(null);
      fetchClusters();
    } catch (e: any) {
      message.error(e.message || 'Gagal menyimpan identitas');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdatePerson = async () => {
    if (!editingPerson) return;
    try {
      const res = await apiFetch(`/api/v1/faces/people-clusters/${editingPerson.person_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editingPerson.name,
          is_watchlist: editingPerson.is_watchlist,
          notes: editingPerson.notes,
        }),
      });
      if (!res.ok) throw new Error('Gagal memperbarui profil wajah');
      message.success('Profil wajah diperbarui');
      setEditModalOpen(false);
      fetchClusters();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleDeletePerson = async (personId: string) => {
    try {
      const res = await apiFetch(`/api/v1/faces/people-clusters/${personId}`, { method: 'DELETE' });
      if (res.ok) {
        message.success('Identitas dihapus dari SQL & Qdrant');
        fetchClusters();
      }
    } catch {
      message.error('Gagal menghapus identitas');
    }
  };

  const filteredClusters = clusters.filter((c) => {
    if (filterMode === 'WATCHLIST') return c.is_watchlist;
    if (filterMode === 'VIP') return !c.is_watchlist;
    return true;
  });

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card size="small">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>Galeri Klaster Wajah & Watchlist (InsightFace + Qdrant 512-d)</Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Pengelompokan otomatis subjek wajah di seluruh kamera & pencarian kemiripan kosinus
            </Text>
          </div>

          <Space wrap>
            <Segmented
              value={filterMode}
              onChange={(v) => setFilterMode(String(v))}
              options={[
                { label: `Semua (${clusters.length})`, value: 'ALL' },
                { label: `Watchlist DPO (${clusters.filter((c) => c.is_watchlist).length})`, value: 'WATCHLIST' },
                { label: 'Terdaftar / VIP', value: 'VIP' },
              ]}
            />
            <Button icon={<UserAddOutlined />} onClick={() => setRegisterModalOpen(true)}>
              Daftarkan Wajah Baru
            </Button>
            <Button type="primary" icon={<SearchOutlined />} onClick={onOpenSearch}>
              Cari Wajah dengan Foto
            </Button>
          </Space>
        </div>
      </Card>

      {filteredClusters.length === 0 ? (
        <Card><Empty description="Belum ada klaster wajah pada kategori ini" /></Card>
      ) : (
        <Row gutter={[16, 16]}>
          {filteredClusters.map((person) => (
            <Col xs={24} sm={12} md={8} lg={6} key={person.person_id}>
              <Card
                size="small"
                style={{
                  borderTop: `3px solid ${person.is_watchlist ? ENTERPRISE_TOKENS.alertDanger : ENTERPRISE_TOKENS.badgeFace}`,
                }}
                actions={[
                  <Button
                    key="edit"
                    type="text"
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => {
                      setEditingPerson({ ...person });
                      setEditModalOpen(true);
                    }}
                  >
                    Edit
                  </Button>,
                  <Popconfirm
                    key="del"
                    title="Hapus identitas ini dari Qdrant & Database?"
                    onConfirm={() => handleDeletePerson(person.person_id)}
                  >
                    <Button type="text" size="small" danger icon={<DeleteOutlined />}>
                      Hapus
                    </Button>
                  </Popconfirm>,
                ]}
              >
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  <img
                    src={person.thumbnail_url || '/media/faces/default_face.png'}
                    alt={person.name}
                    style={{
                      width: 72,
                      height: 72,
                      borderRadius: 10,
                      objectFit: 'cover',
                      border: `2px solid ${person.is_watchlist ? ENTERPRISE_TOKENS.alertDanger : ENTERPRISE_TOKENS.borderLight}`,
                    }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Text strong style={{ display: 'block' }} ellipsis>{person.name}</Text>
                    <div style={{ marginTop: 4 }}>
                      {person.is_watchlist ? (
                        <Tag icon={<WarningOutlined />} color="error">WATCHLIST DPO</Tag>
                      ) : (
                        <Tag icon={<CheckCircleOutlined />} color="processing">TERIDENTIFIKASI</Tag>
                      )}
                    </div>
                    <div style={{ marginTop: 6, fontSize: 12, color: ENTERPRISE_TOKENS.textSecondary }}>
                      Kemunculan: <strong>{person.appearance_count}x</strong>
                    </div>
                  </div>
                </div>

                <div
                  style={{
                    marginTop: 10,
                    paddingTop: 8,
                    borderTop: `1px solid ${ENTERPRISE_TOKENS.borderLight}`,
                    fontSize: 12,
                    color: ENTERPRISE_TOKENS.textSecondary,
                  }}
                >
                  <div><VideoCameraOutlined /> {person.last_seen_camera}</div>
                  {person.notes && (
                    <div style={{ marginTop: 4, color: ENTERPRISE_TOKENS.textPrimary }}>{person.notes}</div>
                  )}
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* Modal Registrasi Identitas Baru */}
      <Modal
        title="Daftarkan Identitas Wajah Baru ke Qdrant Vector DB"
        open={registerModalOpen}
        onCancel={() => setRegisterModalOpen(false)}
        onOk={handleRegisterIdentity}
        confirmLoading={submitting}
        okText="Indeks & Simpan"
      >
        <Form layout="vertical">
          <Form.Item label="Nama Lengkap / Label Subjek" required>
            <Input
              value={regName}
              onChange={(e) => setRegName(e.target.value)}
              placeholder="Contoh: Hendra Wijaya (Manajer Gudang)"
            />
          </Form.Item>
          <Form.Item label="Catatan / Hak Akses">
            <Input
              value={regNotes}
              onChange={(e) => setRegNotes(e.target.value)}
              placeholder="Contoh: Akses Ruang Server / DPO Prioritas"
            />
          </Form.Item>
          <Form.Item label="Tandai sebagai Target Watchlist / DPO">
            <Switch checked={regWatchlist} onChange={(v) => setRegWatchlist(v)} />
          </Form.Item>
          <Form.Item label="Unggah Foto Wajah (JPG/PNG)" required>
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png"
              onChange={(e) => setRegFile(e.target.files?.[0] || null)}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Modal Edit Identitas */}
      <Modal
        title="Edit Identitas Wajah"
        open={editModalOpen}
        onCancel={() => setEditModalOpen(false)}
        onOk={handleUpdatePerson}
        okText="Simpan Perubahan"
      >
        {editingPerson && (
          <Form layout="vertical">
            <Form.Item label="Nama Subjek">
              <Input
                value={editingPerson.name}
                onChange={(e) => setEditingPerson({ ...editingPerson, name: e.target.value })}
              />
            </Form.Item>
            <Form.Item label="Catatan">
              <Input
                value={editingPerson.notes}
                onChange={(e) => setEditingPerson({ ...editingPerson, notes: e.target.value })}
              />
            </Form.Item>
            <Form.Item label="Status Watchlist / DPO">
              <Switch
                checked={editingPerson.is_watchlist}
                onChange={(v) => setEditingPerson({ ...editingPerson, is_watchlist: v })}
              />
            </Form.Item>
          </Form>
        )}
      </Modal>
    </Space>
  );
};

