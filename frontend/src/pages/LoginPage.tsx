import React, { useState, useEffect } from 'react';
import { Card, Form, Input, Button, Typography, Alert, message, Steps } from 'antd';
import { LockOutlined, UserOutlined, MailOutlined, SafetyCertificateOutlined, VideoCameraOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { ENTERPRISE_TOKENS } from '../theme/enterpriseTheme';

const { Title, Text } = Typography;

interface LoginPageProps {
  onLoginSuccess: (tokenData: any) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [isConfigured, setIsConfigured] = useState<boolean | null>(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const checkSetupStatus = async () => {
    try {
      const res = await fetch('/api/v1/auth/status');
      if (res.ok) {
        const data = await res.json();
        setIsConfigured(data.is_configured);
      }
    } catch {
      setIsConfigured(true);
    }
  };

  useEffect(() => {
    checkSetupStatus();
  }, []);

  const handleLogin = async () => {
    if (!username.trim() || !password.trim()) {
      setErrorMsg('Username dan Password wajib diisi');
      return;
    }
    setLoading(true);
    setErrorMsg(null);
    try {
      const formBody = new URLSearchParams();
      formBody.append('username', username.trim());
      formBody.append('password', password);

      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formBody.toString(),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Gagal login');
      }

      const data = await res.json();
      message.success(`Selamat datang, ${data.full_name}`);
      onLoginSuccess(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Koneksi ke server gagal');
    } finally {
      setLoading(false);
    }
  };

  const handleSetupInitialAdmin = async () => {
    if (!username.trim() || !password || !fullName.trim() || !email.trim()) {
      setErrorMsg('Semua data wajib diisi untuk membuat akun Administrator');
      return;
    }
    if (password.length < 8) {
      setErrorMsg('Password Administrator minimal 8 karakter');
      return;
    }
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch('/api/v1/auth/setup-admin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: username.trim(),
          password,
          full_name: fullName.trim(),
          email: email.trim(),
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Gagal membuat akun');
      }

      const data = await res.json();
      message.success('Akun Administrator berhasil dibuat! Mengalihkan ke Ruang Kontrol...');
      onLoginSuccess(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Setup gagal');
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
          maxWidth: 460,
          borderRadius: 12,
          boxShadow: '0 10px 30px rgba(15, 23, 42, 0.08)',
          border: `1px solid ${ENTERPRISE_TOKENS.borderLight}`,
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
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
            Production AI Surveillance & NVR System
          </Text>
        </div>

        {isConfigured === false ? (
          <div>
            <Alert
              type="warning"
              showIcon
              message="Setup Awal Sistem (First-Time Initialization)"
              description="Sistem baru belum memiliki akun Administrator. Silakan daftarkan akun administrator pertama Anda di bawah ini."
              style={{ marginBottom: 16 }}
            />

            {errorMsg && (
              <Alert type="error" showIcon message={errorMsg} style={{ marginBottom: 16 }} />
            )}

            <Form layout="vertical" onFinish={handleSetupInitialAdmin}>
              <Form.Item label="Username Administrator" required>
                <Input
                  size="large"
                  prefix={<UserOutlined style={{ color: ENTERPRISE_TOKENS.textMuted }} />}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Misal: admin"
                />
              </Form.Item>

              <Form.Item label="Nama Lengkap" required>
                <Input
                  size="large"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Misal: Security Administrator"
                />
              </Form.Item>

              <Form.Item label="Email Administrator" required>
                <Input
                  size="large"
                  prefix={<MailOutlined style={{ color: ENTERPRISE_TOKENS.textMuted }} />}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@enterprise.local"
                />
              </Form.Item>

              <Form.Item label="Password Administrator (min. 8 karakter)" required>
                <Input.Password
                  size="large"
                  prefix={<LockOutlined style={{ color: ENTERPRISE_TOKENS.textMuted }} />}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Masukkan password aman"
                />
              </Form.Item>

              <Button
                type="primary"
                htmlType="submit"
                size="large"
                block
                loading={loading}
                icon={<CheckCircleOutlined />}
              >
                Inisialisasi & Masuk
              </Button>
            </Form>
          </div>
        ) : (
          <div>
            {errorMsg && (
              <Alert type="error" showIcon message={errorMsg} style={{ marginBottom: 16 }} />
            )}

            <Form layout="vertical" onFinish={handleLogin}>
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
          </div>
        )}
      </Card>
    </div>
  );
};
