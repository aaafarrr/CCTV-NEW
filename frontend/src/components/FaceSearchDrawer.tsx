import React, { useState, useRef } from 'react';
import { Drawer, Button, Slider, Tag, Card, Empty, Spin, Typography, Space, Alert, message } from 'antd';
import { SearchOutlined, UploadOutlined, WarningOutlined, CheckCircleOutlined, VideoCameraOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { ENTERPRISE_TOKENS } from '../theme/enterpriseTheme';
import { apiFetch } from '../utils/api';

const { Text, Title } = Typography;

interface FaceSearchDrawerProps {
  open: boolean;
  onClose: () => void;
}

export const FaceSearchDrawer: React.FC<FaceSearchDrawerProps> = ({ open, onClose }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [threshold, setThreshold] = useState<number>(0.35);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const f = e.target.files[0];
      setSelectedFile(f);
      setPreviewUrl(URL.createObjectURL(f));
    }
  };

  const executeVectorSearch = async (fileToSearch: File | null = selectedFile) => {
    if (!fileToSearch) {
      message.warning('Silakan pilih atau unggah foto wajah terlebih dahulu');
      return;
    }
    setLoading(true);
    setHasSearched(true);
    try {
      const formData = new FormData();
      formData.append('file', fileToSearch);
      formData.append('threshold', String(threshold));

      const res = await apiFetch('/api/v1/search/by-image', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Gagal memproses pencarian vektor');
      }
      const data = await res.json();
      setResults(Array.isArray(data) ? data : []);
      message.success(`Ditemukan ${data.length} kecocokan vektor di Qdrant DB`);
    } catch (e: any) {
      message.error(e.message || 'Terjadi kesalahan saat mencari wajah');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickSampleSearch = async (samplePath: string, sampleLabel: string) => {
    try {
      setLoading(true);
      const resp = await fetch(samplePath);
      const blob = await resp.blob();
      const file = new File([blob], `${sampleLabel}.jpg`, { type: 'image/jpeg' });
      setSelectedFile(file);
      setPreviewUrl(samplePath);
      await executeVectorSearch(file);
    } catch {
      message.error('Gagal memuat sampel gambar');
      setLoading(false);
    }
  };

  return (
    <Drawer
      title={
        <Space>
          <SearchOutlined style={{ color: ENTERPRISE_TOKENS.primaryColor }} />
          <span>Pencarian Wajah Vektor (Google Photos Style • Qdrant 512-d)</span>
        </Space>
      }
      placement="right"
      width={560}
      onClose={onClose}
      open={open}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Alert
          type="info"
          showIcon
          message="Mesin Vektor Cosine Similarity 512-Dimensi"
          description="Unggah foto target atau gunakan sampel di bawah untuk melacak kemunculan orang tersebut di seluruh kamera CCTV secara instan."
        />

        <div
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${ENTERPRISE_TOKENS.primaryColor}`,
            borderRadius: 10,
            padding: 20,
            textAlign: 'center',
            background: ENTERPRISE_TOKENS.bgSubtle,
            cursor: 'pointer',
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          {previewUrl ? (
            <div>
              <img
                src={previewUrl}
                alt="Target Preview"
                style={{ width: 110, height: 110, objectFit: 'cover', borderRadius: 8, border: `2px solid ${ENTERPRISE_TOKENS.primaryColor}` }}
              />
              <div style={{ marginTop: 8 }}>
                <Text strong>{selectedFile?.name}</Text>
                <div><Text type="secondary" style={{ fontSize: 12 }}>Klik untuk mengganti foto target</Text></div>
              </div>
            </div>
          ) : (
            <div>
              <UploadOutlined style={{ fontSize: 32, color: ENTERPRISE_TOKENS.primaryColor, marginBottom: 8 }} />
              <div><Text strong>Klik atau Seret Foto Wajah Target (JPG / PNG)</Text></div>
              <Text type="secondary" style={{ fontSize: 12 }}>Maksimal 10 MB • Ekstraksi otomatis vektor 512-dimensi</Text>
            </div>
          )}
        </div>

        <Card size="small" style={{ background: ENTERPRISE_TOKENS.bgSubtle }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Sistem mencocokkan vektor embedding 512-dimensi InsightFace dengan database Qdrant secara real-time.
          </Text>
        </Card>

        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text type="secondary">Ambang Kemiripan Minimum (Confidence Threshold):</Text>
            <Text strong>{Math.round(threshold * 100)}%</Text>
          </div>
          <Slider
            min={0.15}
            max={0.95}
            step={0.05}
            value={threshold}
            onChange={(val) => setThreshold(val)}
          />
        </div>

        <Button
          type="primary"
          icon={<SearchOutlined />}
          size="large"
          block
          loading={loading}
          onClick={() => executeVectorSearch()}
        >
          Cari di Database Vektor Qdrant
        </Button>

        <div style={{ marginTop: 8 }}>
          <Title level={5} style={{ margin: '0 0 12px 0' }}>
            Hasil Pencocokan Vektor ({results.length})
          </Title>

          {loading ? (
            <div style={{ textAlign: 'center', padding: 32 }}>
              <Spin size="large" />
              <div style={{ marginTop: 12 }}><Text type="secondary">Mengekstraksi embedding 512-d & memindai indeks Qdrant...</Text></div>
            </div>
          ) : results.length > 0 ? (
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              {results.map((item, idx) => {
                const pct = Math.min(99.9, Math.max(50, (item.similarity_score || 0.85) * 100)).toFixed(1);
                return (
                  <Card
                    key={item.face_id || idx}
                    size="small"
                    style={{
                      borderLeft: `4px solid ${item.is_watchlist ? ENTERPRISE_TOKENS.alertDanger : ENTERPRISE_TOKENS.badgeFace}`,
                    }}
                  >
                    <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                      <img
                        src={item.image_crop_url || '/media/faces/default_face.png'}
                        alt={item.person_name}
                        style={{ width: 64, height: 64, borderRadius: 8, objectFit: 'cover', border: `1px solid ${ENTERPRISE_TOKENS.borderLight}` }}
                      />
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Text strong>{item.person_name}</Text>
                          <Tag color={item.is_watchlist ? 'error' : 'processing'}>
                            Match {pct}%
                          </Tag>
                        </div>
                        <div style={{ marginTop: 4 }}>
                          {item.is_watchlist ? (
                            <Tag icon={<WarningOutlined />} color="red">WATCHLIST / DPO</Tag>
                          ) : (
                            <Tag icon={<CheckCircleOutlined />} color="blue">TERIDENTIFIKASI</Tag>
                          )}
                        </div>
                        <div style={{ marginTop: 6, fontSize: 12, color: ENTERPRISE_TOKENS.textSecondary, display: 'flex', gap: 12 }}>
                          <span><VideoCameraOutlined /> {item.camera_name}</span>
                          <span><ClockCircleOutlined /> {new Date((item.timestamp || Date.now() / 1000) * 1000).toLocaleTimeString('id-ID')}</span>
                        </div>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </Space>
          ) : hasSearched ? (
            <Empty description="Tidak ditemukan wajah yang melewati ambang kemiripan ini" />
          ) : (
            <Empty description="Unggah foto atau klik tombol sampel di atas untuk memulai pencarian" />
          )}
        </div>
      </Space>
    </Drawer>
  );
};

