import React, { useState, useEffect } from 'react';
import {
  ConfigProvider,
  Layout,
  Menu,
  Breadcrumb,
  Button,
  Badge,
  Space,
  Typography,
  Tag,
  Popover,
  List,
  Avatar,
} from 'antd';
import {
  DashboardOutlined,
  VideoCameraOutlined,
  TeamOutlined,
  AlertOutlined,
  CloudServerOutlined,
  SettingOutlined,
  SearchOutlined,
  BellOutlined,
  LogoutOutlined,
  UserOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import { enterpriseAntdTheme, ENTERPRISE_TOKENS } from './theme/enterpriseTheme';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/Dashboard';
import { LiveViewPage } from './pages/LiveView';
import { FaceGalleryPage } from './pages/FaceGallery';
import { EventsPage } from './pages/EventsPage';
import { StorageSyncPage } from './pages/StorageSyncPage';
import { SettingsPage } from './pages/SettingsPage';
import { FaceSearchDrawer } from './components/FaceSearchDrawer';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const TAB_LABELS: Record<string, string> = {
  dashboard: 'Dashboard Overview',
  live: 'Live Multi-Cam Grid',
  faces: 'People Gallery & Face Search',
  events: 'Events & Incidents Log',
  storage: 'Storage & Cloud Sync',
  settings: 'System & Camera Settings',
};

export function App() {
  const [user, setUser] = useState<any | null>(() => {
    const saved = localStorage.getItem('cctv_user');
    return saved ? JSON.parse(saved) : null;
  });

  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [collapsed, setCollapsed] = useState<boolean>(false);
  const [faceSearchOpen, setFaceSearchOpen] = useState<boolean>(false);
  const [targetEditCamId, setTargetEditCamId] = useState<string | null>(null);
  const [recentAlerts, setRecentAlerts] = useState<any[]>([]);

  const fetchBellAlerts = async () => {
    try {
      const res = await fetch('/api/v1/alerts?limit=5');
      if (res.ok) setRecentAlerts(await res.json());
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    if (user) {
      fetchBellAlerts();
      const timer = setInterval(fetchBellAlerts, 8000);
      return () => clearInterval(timer);
    }
  }, [user]);

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

  const alarmPopoverContent = (
    <div style={{ width: 340 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <Text strong>Insiden AI Terbaru</Text>
        <a onClick={() => setActiveTab('events')}>Lihat Semua</a>
      </div>
      <List
        size="small"
        dataSource={recentAlerts.slice(0, 4)}
        renderItem={(item: any) => (
          <List.Item style={{ padding: '6px 0' }}>
            <List.Item.Meta
              title={
                <Space size={4}>
                  <Tag color={item.severity === 'CRITICAL' ? 'error' : 'warning'} style={{ margin: 0 }}>
                    {item.event_type}
                  </Tag>
                  <Text strong style={{ fontSize: 12 }}>{item.camera_name}</Text>
                </Space>
              }
              description={<Text style={{ fontSize: 12 }}>{item.description}</Text>}
            />
          </List.Item>
        )}
      />
    </div>
  );

  return (
    <ConfigProvider theme={enterpriseAntdTheme}>
      {!user ? (
        <LoginPage onLoginSuccess={handleLoginSuccess} />
      ) : (
        <Layout style={{ minHeight: '100vh' }}>
          {/* Left Collapsible Enterprise Sidebar */}
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
                    CCTV NEW
                  </Text>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    Enterprise AI NVR
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
                { key: 'dashboard', icon: <DashboardOutlined />, label: 'Dashboard Overview' },
                { key: 'live', icon: <VideoCameraOutlined />, label: 'Live Multi-Cam Grid' },
                { key: 'faces', icon: <TeamOutlined />, label: 'People & Face Search' },
                { key: 'events', icon: <AlertOutlined />, label: 'Events & Incidents' },
                { key: 'storage', icon: <CloudServerOutlined />, label: 'Cloud Storage Pool' },
                { key: 'settings', icon: <SettingOutlined />, label: 'Settings & V380 Scan' },
              ]}
            />
          </Sider>

          {/* Main Content Shell */}
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
                    { title: 'CCTV NEW Enterprise' },
                    { title: TAB_LABELS[activeTab] || 'Overview' },
                  ]}
                />
              </Space>

              <Space size="middle">
                <Button
                  type="primary"
                  ghost
                  icon={<SearchOutlined />}
                  onClick={() => setFaceSearchOpen(true)}
                >
                  Vector Face Search (Qdrant)
                </Button>

                <Popover content={alarmPopoverContent} trigger="click" placement="bottomRight">
                  <Badge count={recentAlerts.length} size="small">
                    <Button shape="circle" icon={<BellOutlined />} />
                  </Badge>
                </Popover>

                <Space size="small" style={{ paddingLeft: 8, borderLeft: `1px solid ${ENTERPRISE_TOKENS.borderLight}` }}>
                  <Avatar size="small" style={{ backgroundColor: ENTERPRISE_TOKENS.primaryColor }} icon={<UserOutlined />} />
                  <Text strong style={{ fontSize: 13 }}>{user.full_name}</Text>
                  <Tag color="blue" style={{ margin: 0 }}>{user.role}</Tag>
                  <Button type="text" danger icon={<LogoutOutlined />} onClick={handleLogout} title="Keluar" />
                </Space>
              </Space>
            </Header>

            <Content style={{ padding: 20, background: ENTERPRISE_TOKENS.bgApp, overflowY: 'auto' }}>
              {activeTab === 'dashboard' && <DashboardPage onNavigate={(tab) => setActiveTab(tab)} />}
              {activeTab === 'live' && (
                <LiveViewPage
                  initialEditCameraId={targetEditCamId}
                  onClearInitialEditCameraId={() => setTargetEditCamId(null)}
                />
              )}
              {activeTab === 'faces' && <FaceGalleryPage onOpenSearch={() => setFaceSearchOpen(true)} />}
              {activeTab === 'events' && <EventsPage />}
              {activeTab === 'storage' && <StorageSyncPage />}
              {activeTab === 'settings' && (
                <SettingsPage
                  onOpenRoiDrawer={(cam) => {
                    setTargetEditCamId(cam.id);
                    setActiveTab('live');
                  }}
                />
              )}
            </Content>
          </Layout>

          {/* Google Photos-style Face Search Drawer */}
          <FaceSearchDrawer open={faceSearchOpen} onClose={() => setFaceSearchOpen(false)} />
        </Layout>
      )}
    </ConfigProvider>
  );
}

export default App;
