import React, { useState, useEffect } from 'react';
import {
  Card,
  Tabs,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Typography,
  Popconfirm,
  message,
} from 'antd';
import {
  UserAddOutlined,
  DeleteOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { apiFetch } from '../utils/api';

const { Title, Text } = Typography;

export const SettingsPage: React.FC = () => {
  const [users, setUsers] = useState<any[]>([]);
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newRole, setNewRole] = useState('OPERATOR');

  const fetchUsers = async () => {
    try {
      const res = await apiFetch('/api/auth/users');
      if (res.ok) setUsers(await res.json());
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreateUser = async () => {
    if (!newUsername.trim() || !newPassword.trim()) {
      message.warning('Username dan password wajib diisi');
      return;
    }
    try {
      const res = await apiFetch('/api/auth/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: newUsername.trim(),
          password: newPassword,
          full_name: newFullName.trim() || newUsername.trim(),
          email: newEmail.trim() || `${newUsername.trim()}@cctv.local`,
          role: newRole,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Gagal membuat pengguna');
      }
      message.success(`Pengguna ${newUsername} ditambahkan`);
      setUserModalOpen(false);
      setNewUsername('');
      setNewPassword('');
      fetchUsers();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handleDeleteUser = async (username: string) => {
    try {
      const res = await apiFetch(`/api/auth/users/${username}`, { method: 'DELETE' });
      if (res.ok) {
        message.success(`Pengguna ${username} dihapus`);
        fetchUsers();
      } else {
        const err = await res.json();
        message.error(err.detail || 'Gagal menghapus');
      }
    } catch (e: any) {
      message.error(e.message);
    }
  };

  return (
    <Card size="small">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>Manajemen Akun Pengguna (RBAC)</Title>
          <Text type="secondary" style={{ fontSize: 13 }}>Pengaturan otorisasi operator ruang kontrol dan administrator sistem</Text>
        </div>
        <Button type="primary" icon={<UserAddOutlined />} onClick={() => setUserModalOpen(true)}>
          Tambah Pengguna Baru
        </Button>
      </div>

      <Table
        dataSource={users}
        rowKey="username"
        size="small"
        pagination={false}
        columns={[
          { title: 'Username', dataIndex: 'username', key: 'username', render: (t: string) => <Text strong>{t}</Text> },
          { title: 'Nama Lengkap', dataIndex: 'full_name', key: 'full_name' },
          { title: 'Email', dataIndex: 'email', key: 'email' },
          { title: 'Peran (Role)', dataIndex: 'role', key: 'role', render: (r: string) => <Tag color={r === 'ADMIN' ? 'blue' : 'green'}>{r}</Tag> },
          {
            title: 'Aksi',
            key: 'action',
            render: (_: any, r: any) => (
              <Popconfirm title={`Hapus pengguna ${r.username}?`} onConfirm={() => handleDeleteUser(r.username)}>
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            ),
          },
        ]}
      />

      <Modal
        title="Tambah Akun Pengguna Baru"
        open={userModalOpen}
        onCancel={() => setUserModalOpen(false)}
        onOk={handleCreateUser}
        okText="Buat Akun"
      >
        <Form layout="vertical">
          <Form.Item label="Username" required>
            <Input value={newUsername} onChange={(e) => setNewUsername(e.target.value)} />
          </Form.Item>
          <Form.Item label="Password (minimal 8 karakter)" required>
            <Input.Password value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
          </Form.Item>
          <Form.Item label="Nama Lengkap">
            <Input value={newFullName} onChange={(e) => setNewFullName(e.target.value)} />
          </Form.Item>
          <Form.Item label="Email">
            <Input value={newEmail} onChange={(e) => setNewEmail(e.target.value)} />
          </Form.Item>
          <Form.Item label="Role">
            <Select
              value={newRole}
              onChange={(v) => setNewRole(v)}
              options={[
                { value: 'ADMIN', label: 'ADMIN (Akses Penuh)' },
                { value: 'OPERATOR', label: 'OPERATOR (Monitoring & Capture)' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};
