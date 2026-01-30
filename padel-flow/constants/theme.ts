// constants/theme.ts
// Thème et couleurs de l'application PadelFlow

export const Colors = {
  // Couleurs principales
  primary: '#2563eb',
  primaryDark: '#1d4ed8',
  primaryLight: '#3b82f6',
  
  // Couleurs secondaires
  secondary: '#10b981',
  secondaryDark: '#059669',
  
  // Couleurs d'accent
  accent: '#f59e0b',
  accentDark: '#d97706',
  
  // Couleurs de fond
  background: '#f8fafc',
  surface: '#ffffff',
  surfaceSecondary: '#f1f5f9',
  
  // Couleurs de texte
  text: '#1e293b',
  textSecondary: '#64748b',
  textLight: '#94a3b8',
  textInverse: '#ffffff',
  
  // Couleurs d'état
  error: '#ef4444',
  errorLight: '#fee2e2',
  warning: '#f59e0b',
  warningLight: '#fef3c7',
  success: '#10b981',
  successLight: '#d1fae5',
  info: '#3b82f6',
  infoLight: '#dbeafe',
  
  // Bordures
  border: '#e2e8f0',
  borderDark: '#cbd5e1',
  
  // Ombres
  shadow: 'rgba(0, 0, 0, 0.1)',
};

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const FontSizes = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 18,
  xl: 20,
  xxl: 24,
  xxxl: 32,
};

export const BorderRadius = {
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
};

export const CommonStyles = {
  shadow: {
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  shadowLight: {
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.18,
    shadowRadius: 1.0,
    elevation: 1,
  },
};