// app/(tabs)/profile.tsx
// Écran profil utilisateur

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ScrollView,
} from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../context/AuthContext';
import { Colors, Spacing, FontSizes, BorderRadius } from '../../constants/theme';

export default function ProfileScreen() {
  const { logout } = useAuth();

  const handleLogout = () => {
    Alert.alert(
      'Déconnexion',
      'Êtes-vous sûr de vouloir vous déconnecter ?',
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Déconnecter',
          style: 'destructive',
          onPress: async () => {
            await logout();
            router.replace('/(auth)/login');
          },
        },
      ]
    );
  };

  return (
    <ScrollView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.avatarContainer}>
          <Ionicons name="person" size={40} color={Colors.textInverse} />
        </View>
        <Text style={styles.title}>Mon Profil</Text>
        <Text style={styles.subtitle}>Juge-Arbitre</Text>
      </View>

      {/* Menu */}
      <View style={styles.content}>
        <View style={styles.menuCard}>
          <TouchableOpacity
            style={styles.menuItem}
            onPress={() => Alert.alert('Info', 'Fonctionnalité à venir')}
          >
            <View style={styles.menuIcon}>
              <Ionicons name="person-outline" size={22} color={Colors.primary} />
            </View>
            <View style={styles.menuContent}>
              <Text style={styles.menuTitle}>Mon compte</Text>
              <Text style={styles.menuSubtitle}>Gérer mes informations</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={Colors.textLight} />
          </TouchableOpacity>

          <View style={styles.separator} />

          <TouchableOpacity
            style={styles.menuItem}
            onPress={() => Alert.alert('PadelFlow', 'Version 1.0.0\n\nApplication de gestion de compétitions de padel')}
          >
            <View style={styles.menuIcon}>
              <Ionicons name="information-circle-outline" size={22} color={Colors.primary} />
            </View>
            <View style={styles.menuContent}>
              <Text style={styles.menuTitle}>À propos</Text>
              <Text style={styles.menuSubtitle}>Version et informations</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={Colors.textLight} />
          </TouchableOpacity>
        </View>

        {/* Bouton déconnexion */}
        <TouchableOpacity
          style={styles.logoutButton}
          onPress={handleLogout}
          activeOpacity={0.7}
        >
          <Ionicons name="log-out-outline" size={22} color={Colors.error} />
          <Text style={styles.logoutText}>Se déconnecter</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  header: {
    backgroundColor: Colors.primary,
    paddingTop: Spacing.xxl + Spacing.lg,
    paddingBottom: Spacing.xl,
    alignItems: 'center',
  },
  avatarContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: Colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.md,
  },
  title: {
    fontSize: FontSizes.xxl,
    fontWeight: 'bold',
    color: Colors.textInverse,
  },
  subtitle: {
    fontSize: FontSizes.md,
    color: Colors.textInverse,
    opacity: 0.8,
    marginTop: Spacing.xs,
  },
  content: {
    padding: Spacing.md,
  },
  menuCard: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    overflow: 'hidden',
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: Spacing.md,
  },
  separator: {
    height: 1,
    backgroundColor: Colors.border,
    marginLeft: Spacing.md + 40 + Spacing.md,
  },
  menuIcon: {
    width: 40,
    height: 40,
    borderRadius: BorderRadius.md,
    backgroundColor: Colors.infoLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  menuContent: {
    flex: 1,
    marginLeft: Spacing.md,
  },
  menuTitle: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.text,
  },
  menuSubtitle: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    marginTop: 2,
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.errorLight,
    padding: Spacing.md,
    borderRadius: BorderRadius.lg,
    marginTop: Spacing.lg,
  },
  logoutText: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.error,
    marginLeft: Spacing.sm,
  },
});