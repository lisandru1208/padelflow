// app/(tabs)/index.tsx
// Écran principal - Liste des clubs

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { useFocusEffect, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../context/AuthContext';
import { getClubs, Club } from '../../services/api';
import { Card } from '../../components';
import { Colors, Spacing, FontSizes, BorderRadius } from '../../constants/theme';

export default function ClubsScreen() {
  const { token, logout } = useAuth();
  const [clubs, setClubs] = useState<Club[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchClubs = async () => {
    if (!token) {
      setIsLoading(false);
      return;
    }
    try {
      const data = await getClubs(token);
      setClubs(Array.isArray(data) ? data : []);
    } catch (e: any) {
      // Si erreur de token, on déconnecte silencieusement
      if (e.status === 401 || e.message === 'Invalid token') {
        await logout();
        router.replace('/(auth)/login');
      } else {
        console.error('Erreur lors du chargement des clubs:', e);
        Alert.alert('Erreur', e.message || 'Impossible de charger les clubs');
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  // Recharger les clubs quand l'écran est focus
  useFocusEffect(
    useCallback(() => {
      fetchClubs();
    }, [token])
  );

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchClubs();
  };

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

  const renderClubItem = ({ item }: { item: Club }) => (
    <Card
      variant="elevated"
      onPress={() => router.push(`/club/${item.id}`)}
      style={styles.clubCard}
    >
      <View style={styles.clubHeader}>
        <View style={styles.clubIcon}>
          <Ionicons name="business" size={24} color={Colors.primary} />
        </View>
        <View style={styles.clubInfo}>
          <Text style={styles.clubName}>{item.name}</Text>
          {item.city && (
            <View style={styles.locationRow}>
              <Ionicons name="location-outline" size={14} color={Colors.textSecondary} />
              <Text style={styles.clubCity}>{item.city}</Text>
            </View>
          )}
        </View>
        <Ionicons name="chevron-forward" size={24} color={Colors.textLight} />
      </View>
    </Card>
  );

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <Ionicons name="business-outline" size={64} color={Colors.textLight} />
      <Text style={styles.emptyTitle}>Aucun club</Text>
      <Text style={styles.emptyText}>
        Créez votre premier club pour commencer à organiser des compétitions
      </Text>
    </View>
  );

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Bienvenue 👋</Text>
          <Text style={styles.title}>Mes Clubs</Text>
        </View>
        <TouchableOpacity onPress={handleLogout} style={styles.logoutButton}>
          <Ionicons name="log-out-outline" size={24} color={Colors.textSecondary} />
        </TouchableOpacity>
      </View>

      {/* Liste des clubs */}
      <FlatList
        data={clubs}
        keyExtractor={(item) => item.id}
        renderItem={renderClubItem}
        contentContainerStyle={[
          styles.list,
          clubs.length === 0 && styles.listEmpty,
        ]}
        ListEmptyComponent={!isLoading ? renderEmpty : null}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={handleRefresh}
            colors={[Colors.primary]}
            tintColor={Colors.primary}
          />
        }
      />

      {/* Bouton flottant pour créer un club */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => router.push('/club/create')}
        activeOpacity={0.8}
      >
        <Ionicons name="add" size={28} color={Colors.textInverse} />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.xxl,
    paddingBottom: Spacing.md,
    backgroundColor: Colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  greeting: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
  },
  title: {
    fontSize: FontSizes.xxl,
    fontWeight: 'bold',
    color: Colors.text,
  },
  logoutButton: {
    padding: Spacing.sm,
  },
  list: {
    padding: Spacing.md,
  },
  listEmpty: {
    flex: 1,
  },
  clubCard: {
    marginBottom: Spacing.sm,
  },
  clubHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  clubIcon: {
    width: 48,
    height: 48,
    borderRadius: BorderRadius.md,
    backgroundColor: Colors.infoLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  clubInfo: {
    flex: 1,
    marginLeft: Spacing.md,
  },
  clubName: {
    fontSize: FontSizes.lg,
    fontWeight: '600',
    color: Colors.text,
  },
  locationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: Spacing.xs,
  },
  clubCity: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    marginLeft: Spacing.xs,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: Spacing.xl,
  },
  emptyTitle: {
    fontSize: FontSizes.lg,
    fontWeight: '600',
    color: Colors.text,
    marginTop: Spacing.md,
  },
  emptyText: {
    fontSize: FontSizes.md,
    color: Colors.textSecondary,
    textAlign: 'center',
    marginTop: Spacing.sm,
  },
  fab: {
    position: 'absolute',
    bottom: Spacing.lg,
    right: Spacing.lg,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 8,
  },
});