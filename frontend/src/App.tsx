import React, { useState } from 'react';
import {
  ConfigProvider,
  Layout,
  Menu,
  Breadcrumb,
  Button,
  Space,
  Typography,
  Tag,
  Avatar,
} from 'antd';
import {
  DashboardOutlined,
  VideoCameraOutlined,
  GoogleOutlined,
  SettingOutlined,
  LogoutOutlined,
  UserOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import { enterpriseAntdTheme, ENTERPRISE_TOKENS } from './theme/enterpriseTheme';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/Dashboard';
import { LiveViewPage } from './pages/LiveView';
import { GoogleDrivePage } from './pages/GoogleDrivePage';
import { SettingsPage } from './pages/SettingsPage';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const TAB_LABELS: Record<string, string> = {
  dashboard: 'Dashboard Utama',
  live: 'Live CCTV Matrix & Gallery',
  gdrive: 'Google Drive Cloud Storage',
  settings: 'Manajemen Pengguna',
};

export function App() {
  const [user, setUser] = useState<any | null>(() => {
    const saved = localStorage.getItem('cctv_user');
    return saved ? JSON.parse(saved) : null;
  });

  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [collapsed, setCollapsed] = useState<boolean>(false);

  const handleLoginSuccess = (tokenData: any) => {
    const userData = {
      username: tokenData.username,
      full_name: tokenData.full_name,
      role: tokenData.role,
    };
    setUser(userData);
    localStorage.setItem('cctv_user', JSON.stringify(userData));
    localStorage.setItem('cctv_token', tokenData.access_token);
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('cctv_user');
    localStorage.removeItem('cctv_token');
  };

  return (
    <ConfigProvider theme={enterpriseAntdTheme}>
      {!user ? (
        <LoginPage onLoginSuccess={handleLoginSuccess} />
      ) : (
        <Layout style={{ minHeight: '100vh' }}>
          {/* Left Navigation Sidebar */}
          <Sider
            collapsible
            collapsed={collapsed}
            onCollapse={(val) => setCollapsed(val)}
            width={245}
            theme="light"
            style={{
              borderRight: `1px solid ${ENTERPRISE_TOKENS.borderLight}`,
              background: ENTERPRISE_TOKENS.bgSurface,
            }}
          >
            <div
              style={{
                height: 60,
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: collapsed ? '0 24px' : '0 20px',
                borderBottom: `1px solid ${ENTERPRISE_TOKENS.borderLight}`,
              }}
            >
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 8,
                  background: ENTERPRISE_TOKENS.primaryColor,
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 18,
                  flexShrink: 0,
                }}
              >
                <VideoCameraOutlined />
              </div>
              {!collapsed && (
                <div style={{ lineHeight: 1.2 }}>
                  <Text strong style={{ fontSize: 15, color: ENTERPRISE_TOKENS.textPrimary, display: 'block' }}>
                    CLOSPOL CCTV
                  </Text>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    Cloud Storage NVR
                  </Text>
                </div>
              )}
            </div>

            <Menu
              mode="inline"
              selectedKeys={[activeTab]}
              onClick={({ key }) => setActiveTab(key)}
              style={{ borderRight: 0, paddingTop: 8 }}
              items={[
                { key: 'dashboard', icon: <DashboardOutlined />, label: 'Dashboard Utama' },
                { key: 'live', icon: <VideoCameraOutlined />, label: 'Live CCTV & Galeri' },
                { key: 'gdrive', icon: <GoogleOutlined />, label: 'Google Drive Storage' },
                { key: 'settings', icon: <SettingOutlined />, label: 'Manajemen Pengguna' },
              ]}
            />
          </Sider>

          {/* Main Layout Area */}
          <Layout>
            <Header
              style={{
                height: 60,
                padding: '0 20px',
                background: ENTERPRISE_TOKENS.bgSurface,
                borderBottom: `1px solid ${ENTERPRISE_TOKENS.borderLight}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <Space size="middle">
                <Button
                  type="text"
                  icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                  onClick={() => setCollapsed(!collapsed)}
                />
                <Breadcrumb
                  items={[
                    { title: 'Clospol CCTV' },
                    { title: TAB_LABELS[activeTab] || 'Overview' },
                  ]}
                />
              </Space>

              <Space size="middle">
                <Space size="small" style={{ paddingLeft: 8 }}>
                  <Avatar size="small" style={{ backgroundColor: ENTERPRISE_TOKENS.primaryColor }} icon={<UserOutlined />} />
                  <Text strong style={{ fontSize: 13 }}>{user.full_name}</Text>
                  <Tag color="blue" style={{ margin: 0 }}>{user.role}</Tag>
                  <Button type="text" danger icon={<LogoutOutlined />} onClick={handleLogout} title="Keluar" />
                </Space>
              </Space>
            </Header>

            <Content style={{ padding: 20, background: ENTERPRISE_TOKENS.bgApp, overflowY: 'auto' }}>
              {activeTab === 'dashboard' && <DashboardPage onNavigate={(tab) => setActiveTab(tab)} />}
              {activeTab === 'live' && <LiveViewPage />}
              {activeTab === 'gdrive' && <GoogleDrivePage />}
              {activeTab === 'settings' && <SettingsPage />}
            </Content>
          </Layout>
        </Layout>
      )}
    </ConfigProvider>
  );
}

export default App;
