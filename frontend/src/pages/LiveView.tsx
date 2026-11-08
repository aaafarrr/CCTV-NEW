import React, { useEffect, useState, useRef } from 'react';
import {
  Card,
  Button,
  Space,
  Tag,
  Switch,
  Segmented,
  Tooltip,
  Typography,
  Badge,
  Drawer,
  Form,
  Input,
  Select,
  message,
} from 'antd';
import {
  CameraOutlined,
  FullscreenOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
  ReloadOutlined,
  EditOutlined,
  BorderOuterOutlined,
  DeleteOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import { ENTERPRISE_TOKENS } from '../theme/enterpriseTheme';
import { TimelineScrubber, TimelineBand } from '../components/TimelineScrubber';

const { Title, Text } = Typography;

interface LiveViewProps {
  initialEditCameraId?: string | null;
  onClearInitialEditCameraId?: () => void;
}

export const LiveViewPage: React.FC<LiveViewProps> = ({
  initialEditCameraId,
  onClearInitialEditCameraId,
}) => {
  const [cameras, setCameras] = useState<any[]>([]);
  const [gridSize, setGridSize] = useState<number>(2); // 1=1x1, 2=2x2, 3=3x3, 4=4x4
  const [selectedCamId, setSelectedCamId] = useState<string>('cam_1');
  const [showBoxes, setShowBoxes] = useState<boolean>(true);
  const [timelineBands, setTimelineBands] = useState<TimelineBand[]>([]);
  const [preBufferCount, setPreBufferCount] = useState<number>(75);

  // ROI & Counting Line Drawer State
  const [roiDrawerOpen, setRoiDrawerOpen] = useState<boolean>(false);
  const [editingCam, setEditingCam] = useState<any | null>(null);
  const [drawMode, setDrawMode] = useState<'ROI_INTRUSION' | 'ROI_LOITERING' | 'COUNTING_LINE'>('ROI_INTRUSION');
  const [zoneName, setZoneName] = useState<string>('Area Terbatas Baru');
  const [draftPoints, setDraftPoints] = useState<{ x: number; y: number }[]>([]);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const fetchCameras = async () => {
    try {
      const res = await fetch('/api/v1/cameras');
      if (res.ok) {
        const data = await res.json();
        setCameras(data);
        if (data.length > 0 && !data.some((c: any) => c.id === selectedCamId)) {
          setSelectedCamId(data[0].id);
        }
        if (initialEditCameraId) {
          const target = data.find((c: any) => c.id === initialEditCameraId);
          if (target) {
            setEditingCam(target);
            setRoiDrawerOpen(true);
            onClearInitialEditCameraId?.();
          }
        }
      }
    } catch {
      // ignore
    }
  };

  const fetchTimeline = async (camId: string) => {
    try {
      const res = await fetch(`/api/v1/cameras/${camId}/timeline`);
      if (res.ok) {
        const data = await res.json();
        setTimelineBands(data.bands || []);
        setPreBufferCount(data.pre_event_buffer_frames || 75);
      }
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchCameras();
    const t = setInterval(fetchCameras, 5000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (selectedCamId) {
      fetchTimeline(selectedCamId);
    }
  }, [selectedCamId]);

  const sendPtzCommand = async (camId: string, action: string) => {
    try {
      const res = await fetch(`/api/v1/cameras/${camId}/ptz`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, step: 0.18 }),
      });
      if (res.ok) {
        const data = await res.json();
        setCameras((prev) =>
          prev.map((c) => (c.id === camId ? { ...c, ptz: data.ptz } : c))
        );
      }
    } catch {
      message.error('Gagal mengirim instruksi PTZ');
    }
  };

  const handleTakeSnapshot = async (camId: string, camName: string) => {
    try {
      const res = await fetch(`/api/v1/cameras/${camId}/snapshot`, { method: 'POST' });
      if (!res.ok) throw new Error('Snapshot gagal');
      const data = await res.json();
      message.success(`Snapshot ${camName} tersimpan (${data.filename})`);
      window.open(data.download_url, '_blank');
    } catch {
      message.error('Gagal mengambil snapshot kamera');
    }
  };

  // Draw draft polygon/line on ROI Editor Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !editingCam) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw existing ROI zones
    (editingCam.roi_zones || []).forEach((z: any) => {
      const pts = z.polygon || [];
      if (pts.length >= 3) {
        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        pts.slice(1).forEach((p: any) => ctx.lineTo(p.x, p.y));
        ctx.closePath();
        ctx.fillStyle = z.type === 'INTRUSION' ? 'rgba(239, 68, 68, 0.25)' : 'rgba(245, 158, 11, 0.25)';
        ctx.fill();
        ctx.strokeStyle = z.type === 'INTRUSION' ? '#ef4444' : '#f59e0b';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    });

    // Draw existing Counting Lines
    (editingCam.counting_lines || []).forEach((l: any) => {
      if (l.start && l.end) {
        ctx.beginPath();
        ctx.moveTo(l.start.x, l.start.y);
        ctx.lineTo(l.end.x, l.end.y);
        ctx.strokeStyle = '#06b6d4';
        ctx.lineWidth = 3;
        ctx.stroke();
      }
    });

    // Draw current draft points
    if (draftPoints.length > 0) {
      ctx.beginPath();
      ctx.moveTo(draftPoints[0].x, draftPoints[0].y);
      draftPoints.slice(1).forEach((p) => ctx.lineTo(p.x, p.y));
      if (drawMode !== 'COUNTING_LINE' && draftPoints.length >= 3) {
        ctx.closePath();
      }
      ctx.strokeStyle = '#1677ff';
      ctx.lineWidth = 2;
      ctx.stroke();
      draftPoints.forEach((p) => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#1677ff';
        ctx.fill();
      });
    }
  }, [editingCam, draftPoints, drawMode, roiDrawerOpen]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const scaleX = 640 / rect.width;
    const scaleY = 420 / rect.height;
    const x = Math.round((e.clientX - rect.left) * scaleX);
    const y = Math.round((e.clientY - rect.top) * scaleY);

    if (drawMode === 'COUNTING_LINE') {
      if (draftPoints.length >= 2) {
        setDraftPoints([{ x, y }]);
      } else {
        setDraftPoints((prev) => [...prev, { x, y }]);
      }
    } else {
      setDraftPoints((prev) => [...prev, { x, y }]);
    }
  };

  const handleAddDraftToCamera = () => {
    if (!editingCam) return;
    if (drawMode === 'COUNTING_LINE') {
      if (draftPoints.length < 2) {
        message.warning('Klik 2 titik pada gambar untuk membuat Garis Hitung');
        return;
      }
      const newLine = {
        id: `line_${Date.now()}`,
        name: zoneName || 'Garis Sensor',
        start: draftPoints[0],
        end: draftPoints[1],
      };
      setEditingCam({
        ...editingCam,
        counting_lines: [...(editingCam.counting_lines || []), newLine],
      });
      setDraftPoints([]);
      message.success('Garis hitung ditambahkan ke draf');
    } else {
      if (draftPoints.length < 3) {
        message.warning('Klik minimal 3 titik pada gambar untuk membentuk zona poligon');
        return;
      }
      const newZone = {
        id: `zone_${Date.now()}`,
        name: zoneName || 'Zona Terlarang',
        type: drawMode === 'ROI_INTRUSION' ? 'INTRUSION' : 'LOITERING',
        polygon: draftPoints,
        max_dwell_sec: 5,
      };
      setEditingCam({
        ...editingCam,
        roi_zones: [...(editingCam.roi_zones || []), newZone],
      });
      setDraftPoints([]);
      message.success('Zona ROI ditambahkan ke draf');
    }
  };

  const handleSaveRoiConfig = async () => {
    if (!editingCam) return;
    try {
      const res = await fetch(`/api/v1/cameras/${editingCam.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editingCam.name,
          location: editingCam.location,
          stream_url: editingCam.stream_url,
          enable_counting: editingCam.enable_counting,
          enable_suspicious: editingCam.enable_suspicious,
          enable_face_rec: editingCam.enable_face_rec,
          roi_zones: editingCam.roi_zones || [],
          counting_lines: editingCam.counting_lines || [],
        }),
      });
      if (!res.ok) throw new Error('Gagal menyimpan ROI');
      message.success(`Zona ROI & Garis Hitung untuk ${editingCam.name} berhasil disimpan`);
      setRoiDrawerOpen(false);
      fetchCameras();
    } catch (e: any) {
      message.error(e.message || 'Gagal menyimpan konfigurasi');
    }
  };

  const displayedCameras =
    gridSize === 1
      ? cameras.filter((c) => c.id === selectedCamId)
      : cameras.slice(0, gridSize * gridSize);

  const selectedCamObj = cameras.find((c) => c.id === selectedCamId) || cameras[0];

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {/* Top Matrix Control Bar */}
      <Card size="small">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <Space size="middle" wrap>
            <Title level={4} style={{ margin: 0 }}>Live Multi-Camera Matrix & PTZ</Title>
            <Segmented
              value={gridSize}
              onChange={(val) => setGridSize(Number(val))}
              options={[
                { label: '1x1 Focus', value: 1 },
                { label: '2x2 Quad', value: 2 },
                { label: '3x3 Matrix (9)', value: 3 },
                { label: '4x4 Matrix (16)', value: 4 },
              ]}
            />
          </Space>

          <Space size="middle" wrap>
            <Space size="small">
              <BorderOuterOutlined style={{ color: ENTERPRISE_TOKENS.primaryColor }} />
              <Text strong style={{ fontSize: 13 }}>AI Bounding Box & ROI Overlay:</Text>
              <Switch checked={showBoxes} onChange={(v) => setShowBoxes(v)} />
            </Space>

            {selectedCamObj && (
              <Button
                icon={<EditOutlined />}
                onClick={() => {
                  setEditingCam(selectedCamObj);
                  setDraftPoints([]);
                  setRoiDrawerOpen(true);
                }}
              >
                Konfigurasi Zona ROI ({selectedCamObj.name})
              </Button>
            )}
          </Space>
        </div>
      </Card>

      {/* Adaptive Video Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${gridSize}, minmax(0, 1fr))`,
          gap: 14,
        }}
      >
        {displayedCameras.map((cam) => {
          const isSelected = cam.id === selectedCamId;
          return (
            <Card
              key={cam.id}
              size="small"
              onClick={() => setSelectedCamId(cam.id)}
              style={{
                border: isSelected
                  ? `2px solid ${ENTERPRISE_TOKENS.primaryColor}`
                  : `1px solid ${ENTERPRISE_TOKENS.borderLight}`,
                cursor: 'pointer',
              }}
              title={
                <Space size="small">
                  <Badge status={cam.status === 'ONLINE' ? 'success' : 'default'} />
                  <Text strong style={{ fontSize: 13 }}>{cam.name}</Text>
                  <Tag color="blue" style={{ margin: 0 }}>{cam.location}</Tag>
                </Space>
              }
              extra={
                <Space size={4}>
                  <Tooltip title="Ambil Snapshot">
                    <Button
                      size="small"
                      icon={<CameraOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleTakeSnapshot(cam.id, cam.name);
                      }}
                    />
                  </Tooltip>
                  <Tooltip title="Atur Zona ROI & Garis Hitung">
                    <Button
                      size="small"
                      icon={<EditOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingCam(cam);
                        setDraftPoints([]);
                        setRoiDrawerOpen(true);
                      }}
                    />
                  </Tooltip>
                  <Tooltip title={gridSize === 1 ? 'Kembali ke 2x2 Quad' : 'Fokus 1x1 Layar Penuh'}>
                    <Button
                      size="small"
                      icon={<FullscreenOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedCamId(cam.id);
                        setGridSize(gridSize === 1 ? 2 : 1);
                      }}
                    />
                  </Tooltip>
                </Space>
              }
            >
              {/* Pure Black Video Surface */}
              <div className="cctv-video-surface" style={{ aspectRatio: '16 / 10' }}>
                <img
                  src={`/api/v1/cameras/${cam.id}/stream?show_boxes=${showBoxes}`}
                  alt={cam.name}
                  style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                />
              </div>

              {/* Quick PTZ & Telemetry Bar below video */}
              <div
                style={{
                  marginTop: 8,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: 6,
                }}
              >
                <Space size={4}>
                  <Tag color="#10b981">Person: {cam.live_people ?? 0}</Tag>
                  <Tag color="#8b5cf6">Vehicle: {cam.live_vehicles ?? 0}</Tag>
                  <Tag>Zoom: {cam.ptz?.zoom ?? 1}x</Tag>
                </Space>

                <Space size={4}>
                  <Tooltip title="Pan Left">
                    <Button size="small" icon={<ArrowLeftOutlined />} onClick={() => sendPtzCommand(cam.id, 'pan_left')} />
                  </Tooltip>
                  <Tooltip title="Tilt Up">
                    <Button size="small" icon={<ArrowUpOutlined />} onClick={() => sendPtzCommand(cam.id, 'tilt_up')} />
                  </Tooltip>
                  <Tooltip title="Tilt Down">
                    <Button size="small" icon={<ArrowDownOutlined />} onClick={() => sendPtzCommand(cam.id, 'tilt_down')} />
                  </Tooltip>
                  <Tooltip title="Pan Right">
                    <Button size="small" icon={<ArrowRightOutlined />} onClick={() => sendPtzCommand(cam.id, 'pan_right')} />
                  </Tooltip>
                  <Tooltip title="Zoom In">
                    <Button size="small" icon={<ZoomInOutlined />} onClick={() => sendPtzCommand(cam.id, 'zoom_in')} />
                  </Tooltip>
                  <Tooltip title="Zoom Out">
                    <Button size="small" icon={<ZoomOutOutlined />} onClick={() => sendPtzCommand(cam.id, 'zoom_out')} />
                  </Tooltip>
                  <Tooltip title="Reset PTZ">
                    <Button size="small" icon={<ReloadOutlined />} onClick={() => sendPtzCommand(cam.id, 'reset')} />
                  </Tooltip>
                </Space>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Incident Timeline Scrubber */}
      {selectedCamObj && (
        <TimelineScrubber
          cameraName={selectedCamObj.name}
          bands={timelineBands}
          preEventBufferFrames={preBufferCount}
        />
      )}

      {/* ROI Polygon & Counting Line Interactive Drawer */}
      <Drawer
        title={`Editor Zona AI & Garis Hitung — ${editingCam?.name || ''}`}
        width={700}
        open={roiDrawerOpen}
        onClose={() => setRoiDrawerOpen(false)}
        extra={
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSaveRoiConfig}>
            Simpan ke Kamera
          </Button>
        }
      >
        {editingCam && (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Form layout="inline">
              <Form.Item label="Mode Gambar">
                <Select
                  value={drawMode}
                  onChange={(v) => {
                    setDrawMode(v);
                    setDraftPoints([]);
                  }}
                  style={{ width: 220 }}
                  options={[
                    { value: 'ROI_INTRUSION', label: '🔴 Zona Intrusion (Terlarang)' },
                    { value: 'ROI_LOITERING', label: '🟡 Zona Loitering (Berdiam Diri)' },
                    { value: 'COUNTING_LINE', label: '🔵 Garis Traffic Counting' },
                  ]}
                />
              </Form.Item>
              <Form.Item label="Nama Zona/Garis">
                <Input value={zoneName} onChange={(e) => setZoneName(e.target.value)} style={{ width: 180 }} />
              </Form.Item>
              <Button type="primary" onClick={handleAddDraftToCamera}>
                Tambahkan Titik ({draftPoints.length})
              </Button>
            </Form>

            <div style={{ position: 'relative', width: '100%', maxWidth: 640, border: `1px solid ${ENTERPRISE_TOKENS.borderStrong}`, borderRadius: 8, overflow: 'hidden', background: '#000' }}>
              <img
                src={`/api/v1/cameras/${editingCam.id}/thumbnail?show_boxes=false`}
                alt="Preview ROI"
                style={{ width: '100%', height: 420, objectFit: 'fill', display: 'block' }}
              />
              <canvas
                ref={canvasRef}
                width={640}
                height={420}
                onClick={handleCanvasClick}
                style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', cursor: 'crosshair' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Klik pada gambar di atas untuk menaruh titik koordinat, lalu klik <strong>Tambahkan Titik</strong> dan <strong>Simpan ke Kamera</strong>.
              </Text>
              <Space>
                <Button size="small" onClick={() => setDraftPoints([])}>Reset Titik Baru</Button>
                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => setEditingCam({ ...editingCam, roi_zones: [], counting_lines: [] })}
                >
                  Bersihkan Semua Zona
                </Button>
              </Space>
            </div>
          </Space>
        )}
      </Drawer>
    </Space>
  );
};
