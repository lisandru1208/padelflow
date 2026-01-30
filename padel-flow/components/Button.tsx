// components/Button.tsx
// Bouton personnalisé réutilisable

import React from 'react';
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
  ViewStyle,
  TextStyle,
} from 'react-native';
import { Colors, Spacing, FontSizes, BorderRadius } from '../constants/theme';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'outline' | 'danger';
  size?: 'small' | 'medium' | 'large';
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
}

export default function Button({
  title,
  onPress,
  variant = 'primary',
  size = 'medium',
  disabled = false,
  loading = false,
  style,
  textStyle,
}: ButtonProps) {
  const getButtonStyle = (): ViewStyle[] => {
    const styles: ViewStyle[] = [baseStyles.button, baseStyles[size]];

    switch (variant) {
      case 'primary':
        styles.push(baseStyles.primary);
        break;
      case 'secondary':
        styles.push(baseStyles.secondary);
        break;
      case 'outline':
        styles.push(baseStyles.outline);
        break;
      case 'danger':
        styles.push(baseStyles.danger);
        break;
    }

    if (disabled || loading) {
      styles.push(baseStyles.disabled);
    }

    return styles;
  };

  const getTextStyle = (): TextStyle[] => {
    const styles: TextStyle[] = [baseStyles.text, baseStyles[`${size}Text`]];

    if (variant === 'outline') {
      styles.push(baseStyles.outlineText);
    } else {
      styles.push(baseStyles.lightText);
    }

    return styles;
  };

  return (
    <TouchableOpacity
      style={[...getButtonStyle(), style]}
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.7}
    >
      {loading ? (
        <ActivityIndicator
          color={variant === 'outline' ? Colors.primary : Colors.textInverse}
          size="small"
        />
      ) : (
        <Text style={[...getTextStyle(), textStyle]}>{title}</Text>
      )}
    </TouchableOpacity>
  );
}

const baseStyles = StyleSheet.create({
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: BorderRadius.md,
  },
  small: {
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.md,
  },
  medium: {
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.lg,
  },
  large: {
    paddingVertical: Spacing.lg,
    paddingHorizontal: Spacing.xl,
  },
  primary: {
    backgroundColor: Colors.primary,
  },
  secondary: {
    backgroundColor: Colors.secondary,
  },
  outline: {
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: Colors.primary,
  },
  danger: {
    backgroundColor: Colors.error,
  },
  disabled: {
    opacity: 0.5,
  },
  text: {
    fontWeight: '600',
  },
  smallText: {
    fontSize: FontSizes.sm,
  },
  mediumText: {
    fontSize: FontSizes.md,
  },
  largeText: {
    fontSize: FontSizes.lg,
  },
  lightText: {
    color: Colors.textInverse,
  },
  outlineText: {
    color: Colors.primary,
  },
});
