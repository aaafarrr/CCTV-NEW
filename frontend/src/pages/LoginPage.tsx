import React, { useState } from 'react';
import { Card, Form, Input, Button, Typography, Space, Alert, Divider, Tag } from 'antd';
import { LockOutlined, UserOutlined, SafetyCertificateOutlined, VideoCameraOutlined } from '@ant-design/icons';
import { ENTERPRISE_TOKENS } from '../theme/enterpriseTheme';

const { Title, Text } = Typography;

interface LoginPageProps {
  onLoginSuccess: (tokenData: any) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (u = username, p = password) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const formBody = new URLSearchParams();
      formBody.append('username', u);
      formBody.append('password', p);

      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formBody.toString(),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Gagal melakukan autentikasi');
      }

      const data = await res.json();
      onLoginSuccess(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Koneksi ke server gagal');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        background: ENTERPRISE_TOKENS.bgApp,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <Card
        style={{
          width: '100%',
          maxWidth: 440,
          borderRadius: 12,
          boxShadow: '0 10px 30px rgba(15, 23, 42, 0.08)',
          border: `1px solid ${ENTERPRISE_TOKENS.borderLight}`,
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 12,
              background: ENTERPRISE_TOKENS.primaryBg,
              color: ENTERPRISE_TOKENS.primaryColor,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 28,
              marginBottom: 12,
            }}
          >
            <VideoCameraOutlined />
          </div>
          <Title level={4} style={{ margin: 0, color: ENTERPRISE_TOKENS.textPrimary }}>
            CCTV NEW ENTERPRISE
          </Title>
          <Text type="secondary" style={{ fontSize: 13 }}>
            AI Surveillance, Vector Face Search & Multi-Cloud NVR
          </Text>
        </div>

        {errorMsg && (
          <Alert
            type="error"
            showIcon
            message={errorMsg}
            style={{ marginBottom: 16 }}
          />
        )}

        <Form layout="vertical" onFinish={() => handleSubmit()}>
          <Form.Item label="Username" required>
            <Input
              size="large"
              prefix={<UserOutlined style={{ color: ENTERPRISE_TOKENS.textMuted }} />}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Masukkan username"
            />
          </Form.Item>

          <Form.Item label="Password" required>
            <Input.Password
              size="large"
              prefix={<LockOutlined style={{ color: ENTERPRISE_TOKENS.textMuted }} />}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Masukkan password"
            />
          </Form.Item>

          <Button
            type="primary"
            htmlType="submit"
            size="large"
            block
            loading={loading}
            icon={<SafetyCertificateOutlined />}
          >
            Masuk ke Ruang Kontrol
          </Button>
        </Form>

        <Divider style={{ margin: '20px 0 12px 0' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>Akses Cepat Akun Demo</Text>
        </Divider>

        <div style={{ display: 'flex', gap: 8 }}>
          <Button
            size="small"
            block
            onClick={() => {
              setUsername('admin');
              setPassword('admin123');
              handleSubmit('admin', 'admin123');
            }}
          >
            Admin (<Tag color="blue" style={{ margin: 0 }}>admin123</Tag>)
          </Button>
          <Button
            size="small"
            block
            onClick={() => {
              setUsername('operator');
              setPassword('operator123');
              handleSubmit('operator', 'operator123');
            }}
          >
            Operator (<Tag color="green" style={{ margin: 0 }}>operator123</Tag>)
          </Button>
        </div>
      </Card>
    </div>
  );
};

