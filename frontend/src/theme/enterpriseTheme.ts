import type { ThemeConfig } from 'antd';

export const ENTERPRISE_TOKENS = {
  bgApp: '#f4f6f9',
  bgSurface: '#ffffff',
  bgSubtle: '#f8fafc',
  borderLight: '#e2e8f0',
  borderStrong: '#cbd5e1',
  textPrimary: '#0f172a',
  textSecondary: '#475569',
  textMuted: '#94a3b8',
  primaryColor: '#1677ff',
  primaryHover: '#4096ff',
  primaryBg: '#e6f4ff',
  statusOnline: '#10b981',
  statusOffline: '#94a3b8',
  alertDanger: '#ef4444',
  alertWarning: '#f59e0b',
  badgeVehicle: '#8b5cf6',
  badgePerson: '#06b6d4',
  badgeFace: '#3b82f6',
  videoBg: '#000000',
  videoOverlayText: '#ffffff',
};

export const enterpriseAntdTheme: ThemeConfig = {
  token: {
    colorPrimary: ENTERPRISE_TOKENS.primaryColor,
    colorBgLayout: ENTERPRISE_TOKENS.bgApp,
    colorBgContainer: ENTERPRISE_TOKENS.bgSurface,
    colorBorder: ENTERPRISE_TOKENS.borderLight,
    colorBorderSecondary: ENTERPRISE_TOKENS.borderLight,
    colorText: ENTERPRISE_TOKENS.textPrimary,
    colorTextSecondary: ENTERPRISE_TOKENS.textSecondary,
    colorSuccess: ENTERPRISE_TOKENS.statusOnline,
    colorError: ENTERPRISE_TOKENS.alertDanger,
    colorWarning: ENTERPRISE_TOKENS.alertWarning,
    borderRadius: 8,
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  },
  components: {
    Layout: {
      headerBg: ENTERPRISE_TOKENS.bgSurface,
      siderBg: ENTERPRISE_TOKENS.bgSurface,
      bodyBg: ENTERPRISE_TOKENS.bgApp,
    },
    Card: {
      headerBg: ENTERPRISE_TOKENS.bgSurface,
    },
    Table: {
      headerBg: ENTERPRISE_TOKENS.bgSubtle,
      headerColor: ENTERPRISE_TOKENS.textSecondary,
      rowHoverBg: ENTERPRISE_TOKENS.bgSubtle,
    },
  },
};

