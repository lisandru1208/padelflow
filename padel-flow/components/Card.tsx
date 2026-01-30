// components/Card.tsx
// Carte personnalisée réutilisable

import React from 'react';
import { View, StyleSheet, TouchableOpacity, ViewStyle } from 'react-native';
import { Colors, Spacing, BorderRadius, CommonStyles } from '../constants/theme';

interface CardProps {
  children: React.ReactNode;
  style?: ViewStyle;
  onPress?: () => void;
  variant?: 'default' | 'elevated' | 'outlined';
}

export default function Card({
  children,
  style,
  onPress,
  variant = 'default',
}: CardProps) {
  const getCardStyle = (): ViewStyle[] => {
    const styles: ViewStyle[] = [baseStyles.card];

    switch (variant) {
      case 'elevated':
        styles.push(baseStyles.elevated, CommonStyles.shadow);
        break;
      case 'outlined':
        styles.push(baseStyles.outlined);
        break;
      default:
        styles.push(baseStyles.default);
    }

    return styles;
  };

  if (onPress) {
    return (
      <TouchableOpacity
        style={[...getCardStyle(), style]}
        onPress={onPress}
        activeOpacity={0.7}
      >
        {children}
      </TouchableOpacity>
    );
  }

  return <View style={[...getCardStyle(), style]}>{children}</View>;
}

const baseStyles = StyleSheet.create({
  card: {
    borderRadius: BorderRadius.lg,
    padding: Spacing.md,
    marginBottom: Spacing.md,
  },
  default: {
    backgroundColor: Colors.surface,
  },
  elevated: {
    backgroundColor: Colors.surface,
  },
  outlined: {
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: Colors.border,
  },
});