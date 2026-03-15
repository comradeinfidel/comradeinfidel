export const theme = {
  colors: {
    background: '#0A0A0F',
    surface: '#13131A',
    surfaceElevated: '#1C1C28',
    border: '#2A2A3A',
    borderLight: '#3A3A50',

    primary: '#6C5CE7',
    primaryLight: '#A29BFE',
    primaryDark: '#4A3AB5',
    primaryGlow: 'rgba(108, 92, 231, 0.25)',

    accent: '#00CEC9',
    accentGlow: 'rgba(0, 206, 201, 0.2)',

    success: '#00B894',
    successGlow: 'rgba(0, 184, 148, 0.2)',
    warning: '#FDCB6E',
    warningGlow: 'rgba(253, 203, 110, 0.2)',
    danger: '#E84393',
    dangerGlow: 'rgba(232, 67, 147, 0.2)',

    textPrimary: '#F0F0FF',
    textSecondary: '#9090B0',
    textMuted: '#5A5A75',
    textOnPrimary: '#FFFFFF',

    userBubble: '#6C5CE7',
    aiBubble: '#1C1C28',
    thinkingBubble: '#1A1A2E',
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
  },
  radius: {
    sm: 8,
    md: 14,
    lg: 20,
    xl: 28,
    full: 999,
  },
  font: {
    sizeXs: 11,
    sizeSm: 13,
    sizeMd: 15,
    sizeLg: 17,
    sizeXl: 20,
    sizeXxl: 28,
    weightNormal: '400' as const,
    weightMedium: '500' as const,
    weightSemibold: '600' as const,
    weightBold: '700' as const,
  },
};

export type Theme = typeof theme;
