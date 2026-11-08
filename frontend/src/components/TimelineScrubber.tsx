import React, { useState } from 'react';
import { Card, Tag, Space, Typography, Tooltip, Button } from 'antd';
import { HistoryOutlined, PlayCircleOutlined, FastBackwardOutlined } from '@ant-design/icons';
import { ENTERPRISE_TOKENS } from '../theme/enterpriseTheme';

const { Text } = Typography;

export interface TimelineBand {
  id: string;
  hour_offset: number;
  duration_min: number;
  type: 'INTRUSION' | 'LOITERING' | 'PERSON' | 'VEHICLE';
  color: string;
  label: string;
  timestamp: number;
}

interface TimelineScrubberProps {
  cameraName: string;
  bands: TimelineBand[];
  preEventBufferFrames?: number;
  onSelectBand?: (band: TimelineBand | null) => void;
}

export const TimelineScrubber: React.FC<TimelineScrubberProps> = ({
  cameraName,
  bands,
  preEventBufferFrames = 75,
  onSelectBand,
}) => {
  const [playheadPct, setPlayheadPct] = useState<number>(96);
  const [selectedEvent, setSelectedEvent] = useState<TimelineBand | null>(null);

  const hours = Array.from({ length: 13 }, (_, i) => {
    const h = (new Date().getHours() - 12 + i + 24) % 24;
    return `${String(h).padStart(2, '0')}:00`;
  });

  const handleBarClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100));
    setPlayheadPct(Math.round(pct));
  };

  return (
    <Card
      size="small"
      style={{
        marginTop: 12,
        border: `1px solid ${ENTERPRISE_TOKENS.borderLight}`,
        background: ENTERPRISE_TOKENS.bgSurface,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, flexWrap: 'wrap', gap: 8 }}>
        <Space size="small">
          <HistoryOutlined style={{ color: ENTERPRISE_TOKENS.primaryColor }} />
          <Text strong>Incident Timeline Scrubber (24-Jam):</Text>
          <Tag color="blue">{cameraName}</Tag>
          <Tag color="green">Pre-Alarm Circular Buffer: {preEventBufferFrames} Frames (~5s)</Tag>
        </Space>

        <Space size="small" wrap>
          <Tag color="#ef4444">Intrusion / DPO</Tag>
          <Tag color="#f59e0b">Loitering</Tag>
          <Tag color="#06b6d4">Person</Tag>
          <Tag color="#8b5cf6">Vehicle</Tag>
          <Button
            size="small"
            type={playheadPct >= 95 ? 'primary' : 'default'}
            icon={<PlayCircleOutlined />}
            onClick={() => {
              setPlayheadPct(99);
              setSelectedEvent(null);
              onSelectBand?.(null);
            }}
          >
            LIVE
          </Button>
        </Space>
      </div>

      {/* Horizontal Scrubber Track */}
      <div
        onClick={handleBarClick}
        style={{
          position: 'relative',
          height: 36,
          background: '#e2e8f0',
          borderRadius: 6,
          cursor: 'pointer',
          overflow: 'hidden',
          border: `1px solid ${ENTERPRISE_TOKENS.borderStrong}`,
        }}
      >
        {/* Continuous normal recording track */}
        <div
          style={{
            position: 'absolute',
            top: 12,
            bottom: 12,
            left: 0,
            right: 0,
            background: '#cbd5e1',
          }}
        />

        {/* Colored Event Bands */}
        {bands.map((band) => {
          const leftPct = Math.max(4, Math.min(92, 100 + (band.hour_offset / 12) * 100));
          const widthPct = Math.max(2.5, (band.duration_min / 720) * 100);
          return (
            <Tooltip
              key={band.id}
              title={`${band.type}: ${band.label} (${new Date(band.timestamp * 1000).toLocaleTimeString('id-ID')})`}
            >
              <div
                onClick={(ev) => {
                  ev.stopPropagation();
                  setPlayheadPct(Math.round(leftPct));
                  setSelectedEvent(band);
                  onSelectBand?.(band);
                }}
                style={{
                  position: 'absolute',
                  top: 4,
                  bottom: 4,
                  left: `${leftPct}%`,
                  width: `${widthPct}%`,
                  backgroundColor: band.color,
                  borderRadius: 4,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
                }}
              />
            </Tooltip>
          );
        })}

        {/* Playhead Marker */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: `${playheadPct}%`,
            width: 3,
            backgroundColor: ENTERPRISE_TOKENS.primaryColor,
            zIndex: 5,
          }}
        />
      </div>

      {/* Hour Scale Labels */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontSize: 11, color: ENTERPRISE_TOKENS.textMuted }}>
        {hours.map((lbl, idx) => (
          <span key={idx} className="mono-text">{lbl}</span>
        ))}
      </div>

      {selectedEvent && (
        <div
          style={{
            marginTop: 8,
            padding: '6px 12px',
            borderRadius: 6,
            background: ENTERPRISE_TOKENS.primaryBg,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Space>
            <FastBackwardOutlined style={{ color: ENTERPRISE_TOKENS.primaryColor }} />
            <Text strong style={{ fontSize: 12 }}>
              Playback Titik Insiden [{selectedEvent.type}]: {selectedEvent.label} ({new Date(selectedEvent.timestamp * 1000).toLocaleTimeString('id-ID')})
            </Text>
          </Space>
          <Button size="small" type="link" onClick={() => { setSelectedEvent(null); setPlayheadPct(99); onSelectBand?.(null); }}>
            Kembali ke Live Feed
          </Button>
        </div>
      )}
    </Card>
  );
};

