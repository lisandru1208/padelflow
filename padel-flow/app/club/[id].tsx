// app/club/[id].tsx
// Écran détail d'un club

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  Alert,
  Modal,
  Switch,
} from 'react-native';
import { useLocalSearchParams, router, Stack, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../context/AuthContext';
import {
  getClubs,
  getCourts,
  getTournaments,
  createCourt,
  Club,
  Court,
  Tournament,
} from '../../services/api';
import { Button, Input, Card } from '../../components';
import { Colors, Spacing, FontSizes, BorderRadius } from '../../constants/theme';

// Type pour un court en cours de création
interface CourtForm {
  id: string;
  name: string;
  indoor: boolean;
}

export default function ClubDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { token } = useAuth();

  const [club, setClub] = useState<Club | null>(null);
  const [courts, setCourts] = useState<Court[]>([]);
  const [tournaments, setTournaments] = useState<Tournament[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Modal création courts (multiple)
  const [showCourtModal, setShowCourtModal] = useState(false);
  const [courtForms, setCourtForms] = useState<CourtForm[]>([
    { id: '1', name: '', indoor: false }
  ]);
  const [isCreatingCourts, setIsCreatingCourts] = useState(false);

  const fetchData = async () => {
    if (!token || !id) return;
    try {
      const clubs = await getClubs(token);
      const foundClub = clubs.find((c) => c.id === id);
      setClub(foundClub || null);

      const courtsData = await getCourts(token, id);
      setCourts(Array.isArray(courtsData) ? courtsData : []);

      const tournamentsData = await getTournaments(token, id);
      setTournaments(Array.isArray(tournamentsData) ? tournamentsData : []);
    } catch (e: any) {
      console.error('Erreur:', e);
      Alert.alert('Erreur', e.message || 'Impossible de charger les données');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchData();
    }, [token, id])
  );

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchData();
  };

  // Ajouter un nouveau formulaire de court
  const addCourtForm = () => {
    const newId = Date.now().toString();
    setCourtForms([...courtForms, { id: newId, name: '', indoor: false }]);
  };

  // Supprimer un formulaire de court
  const removeCourtForm = (formId: string) => {
    if (courtForms.length === 1) {
      Alert.alert('Info', 'Vous devez avoir au moins un court à créer');
      return;
    }
    setCourtForms(courtForms.filter((f) => f.id !== formId));
  };

  // Mettre à jour un formulaire de court
  const updateCourtForm = (formId: string, field: 'name' | 'indoor', value: string | boolean) => {
    setCourtForms(
      courtForms.map((f) =>
        f.id === formId ? { ...f, [field]: value } : f
      )
    );
  };

  // Réinitialiser le modal
  const resetCourtModal = () => {
    setCourtForms([{ id: '1', name: '', indoor: false }]);
    setShowCourtModal(false);
  };

  // Créer tous les courts
  const handleCreateCourts = async () => {
    // Validation
    const validCourts = courtForms.filter((f) => f.name.trim() !== '');
    if (validCourts.length === 0) {
      Alert.alert('Erreur', 'Veuillez renseigner au moins un nom de court');
      return;
    }

    if (!token || !id) return;

    setIsCreatingCourts(true);
    try {
      // Créer tous les courts en parallèle
      await Promise.all(
        validCourts.map((court) =>
          createCourt(token, id, court.name.trim(), court.indoor)
        )
      );

      resetCourtModal();
      Alert.alert(
        'Succès',
        `${validCourts.length} court${validCourts.length > 1 ? 's' : ''} créé${validCourts.length > 1 ? 's' : ''} avec succès !`
      );
      fetchData();
    } catch (e: any) {
      Alert.alert('Erreur', e.message || 'Impossible de créer les courts');
    } finally {
      setIsCreatingCourts(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <Text>Chargement...</Text>
      </View>
    );
  }

  if (!club) {
    return (
      <View style={styles.loadingContainer}>
        <Text>Club introuvable</Text>
        <Button title="Retour" onPress={() => router.back()} style={{ marginTop: 20 }} />
      </View>
    );
  }

  return (
    <>
      <Stack.Screen
        options={{
          title: club.name,
          headerShown: true,
          headerStyle: { backgroundColor: Colors.primary },
          headerTintColor: Colors.textInverse,
          headerLeft: () => (
            <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
              <Ionicons name="arrow-back" size={24} color={Colors.textInverse} />
            </TouchableOpacity>
          ),
        }}
      />
      <ScrollView
        style={styles.container}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={handleRefresh}
            colors={[Colors.primary]}
            tintColor={Colors.primary}
          />
        }
      >
        {/* Header du club */}
        <View style={styles.header}>
          <View style={styles.clubIcon}>
            <Ionicons name="business" size={32} color={Colors.textInverse} />
          </View>
          <Text style={styles.clubName}>{club.name}</Text>
          {club.city && (
            <View style={styles.locationRow}>
              <Ionicons name="location" size={16} color={Colors.textInverse} />
              <Text style={styles.clubCity}>{club.city}</Text>
            </View>
          )}
        </View>

        <View style={styles.content}>
          {/* Section Courts */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Courts de Padel ({courts.length})</Text>
              <TouchableOpacity
                style={styles.addButton}
                onPress={() => setShowCourtModal(true)}
              >
                <Ionicons name="add-circle" size={28} color={Colors.primary} />
              </TouchableOpacity>
            </View>

            {courts.length === 0 ? (
              <Card variant="outlined" style={styles.emptyCard}>
                <Ionicons name="tennisball-outline" size={40} color={Colors.textLight} />
                <Text style={styles.emptyText}>Aucun court</Text>
                <Text style={styles.emptySubtext}>Ajoutez vos courts de padel</Text>
              </Card>
            ) : (
              <View style={styles.courtsGrid}>
                {courts.map((court) => (
                  <Card key={court.id} variant="elevated" style={styles.courtCard}>
                    <View style={styles.courtIcon}>
                      <Ionicons
                        name={court.indoor ? 'home' : 'sunny'}
                        size={24}
                        color={court.indoor ? Colors.info : Colors.accent}
                      />
                    </View>
                    <Text style={styles.courtName}>{court.name}</Text>
                    <Text style={styles.courtType}>
                      {court.indoor ? 'Indoor' : 'Outdoor'}
                    </Text>
                  </Card>
                ))}
              </View>
            )}
          </View>

          {/* Section Compétitions */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Compétitions ({tournaments.length})</Text>
              <TouchableOpacity
                style={styles.addButton}
                onPress={() => router.push(`/tournament/create?clubId=${id}`)}
              >
                <Ionicons name="add-circle" size={28} color={Colors.primary} />
              </TouchableOpacity>
            </View>

            {tournaments.length === 0 ? (
              <Card variant="outlined" style={styles.emptyCard}>
                <Ionicons name="trophy-outline" size={40} color={Colors.textLight} />
                <Text style={styles.emptyText}>Aucune compétition</Text>
                <Text style={styles.emptySubtext}>Créez votre première compétition</Text>
              </Card>
            ) : (
              tournaments.map((tournament) => (
                <Card
                  key={tournament.id}
                  variant="elevated"
                  onPress={() => router.push(`/tournament/${tournament.id}?clubId=${id}`)}
                  style={styles.tournamentCard}
                >
                  <View style={styles.tournamentRow}>
                    <View style={styles.tournamentIcon}>
                      <Ionicons name="trophy" size={24} color={Colors.accent} />
                    </View>
                    <View style={styles.tournamentInfo}>
                      <Text style={styles.tournamentName}>{tournament.name}</Text>
                      <Text style={styles.tournamentDetails}>
                        {tournament.category} • {tournament.gender}
                      </Text>
                      <Text style={styles.tournamentDate}>
                        {formatDate(tournament.start_date)}
                      </Text>
                    </View>
                    <Ionicons name="chevron-forward" size={24} color={Colors.textLight} />
                  </View>
                </Card>
              ))
            )}
          </View>
        </View>
      </ScrollView>

      {/* Modal création courts (multiple) */}
      <Modal
        visible={showCourtModal}
        animationType="slide"
        transparent
        onRequestClose={resetCourtModal}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Ajouter des Courts</Text>
              <TouchableOpacity onPress={resetCourtModal}>
                <Ionicons name="close" size={24} color={Colors.text} />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalScroll} showsVerticalScrollIndicator={false}>
              {courtForms.map((form, index) => (
                <View key={form.id} style={styles.courtFormItem}>
                  <View style={styles.courtFormHeader}>
                    <Text style={styles.courtFormTitle}>Court {index + 1}</Text>
                    {courtForms.length > 1 && (
                      <TouchableOpacity
                        onPress={() => removeCourtForm(form.id)}
                        style={styles.removeButton}
                      >
                        <Ionicons name="trash-outline" size={20} color={Colors.error} />
                      </TouchableOpacity>
                    )}
                  </View>

                  <Input
                    placeholder="Nom du court (ex: Court 1)"
                    value={form.name}
                    onChangeText={(value) => updateCourtForm(form.id, 'name', value)}
                    leftIcon="tennisball-outline"
                  />

                  <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                      <Ionicons
                        name={form.indoor ? 'home' : 'sunny'}
                        size={20}
                        color={Colors.primary}
                      />
                      <Text style={styles.switchLabel}>Indoor</Text>
                    </View>
                    <Switch
                      value={form.indoor}
                      onValueChange={(value) => updateCourtForm(form.id, 'indoor', value)}
                      trackColor={{ false: Colors.border, true: Colors.primaryLight }}
                      thumbColor={form.indoor ? Colors.primary : Colors.surface}
                    />
                  </View>
                </View>
              ))}

              {/* Bouton ajouter un court */}
              <TouchableOpacity style={styles.addCourtButton} onPress={addCourtForm}>
                <Ionicons name="add-circle-outline" size={24} color={Colors.primary} />
                <Text style={styles.addCourtText}>Ajouter un autre court</Text>
              </TouchableOpacity>
            </ScrollView>

            <View style={styles.modalButtons}>
              <Button
                title="Annuler"
                onPress={resetCourtModal}
                variant="outline"
                style={styles.modalButton}
              />
              <Button
                title={`Créer ${courtForms.filter((f) => f.name.trim()).length || ''} court${courtForms.filter((f) => f.name.trim()).length > 1 ? 's' : ''}`}
                onPress={handleCreateCourts}
                loading={isCreatingCourts}
                style={styles.modalButton}
              />
            </View>
          </View>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.background,
  },
  backButton: {
    padding: Spacing.sm,
    marginLeft: Spacing.xs,
  },
  header: {
    backgroundColor: Colors.primary,
    padding: Spacing.lg,
    alignItems: 'center',
    paddingBottom: Spacing.xl,
  },
  clubIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: Colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.md,
  },
  clubName: {
    fontSize: FontSizes.xxl,
    fontWeight: 'bold',
    color: Colors.textInverse,
  },
  locationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: Spacing.xs,
  },
  clubCity: {
    fontSize: FontSizes.md,
    color: Colors.textInverse,
    marginLeft: Spacing.xs,
    opacity: 0.9,
  },
  content: {
    padding: Spacing.md,
  },
  section: {
    marginBottom: Spacing.lg,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.md,
  },
  sectionTitle: {
    fontSize: FontSizes.lg,
    fontWeight: '600',
    color: Colors.text,
  },
  addButton: {
    padding: Spacing.xs,
  },
  emptyCard: {
    alignItems: 'center',
    padding: Spacing.xl,
  },
  emptyText: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.text,
    marginTop: Spacing.sm,
  },
  emptySubtext: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    marginTop: Spacing.xs,
  },
  courtsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  courtCard: {
    width: '48%',
    alignItems: 'center',
    padding: Spacing.md,
  },
  courtIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: Colors.infoLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.sm,
  },
  courtName: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.text,
  },
  courtType: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    marginTop: 2,
  },
  tournamentCard: {
    marginBottom: Spacing.sm,
  },
  tournamentRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  tournamentIcon: {
    width: 48,
    height: 48,
    borderRadius: BorderRadius.md,
    backgroundColor: Colors.warningLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tournamentInfo: {
    flex: 1,
    marginLeft: Spacing.md,
  },
  tournamentName: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.text,
  },
  tournamentDetails: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    marginTop: 2,
  },
  tournamentDate: {
    fontSize: FontSizes.xs,
    color: Colors.textLight,
    marginTop: 2,
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: Colors.surface,
    borderTopLeftRadius: BorderRadius.xl,
    borderTopRightRadius: BorderRadius.xl,
    padding: Spacing.lg,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.md,
  },
  modalTitle: {
    fontSize: FontSizes.xl,
    fontWeight: 'bold',
    color: Colors.text,
  },
  modalScroll: {
    maxHeight: 400,
  },
  courtFormItem: {
    backgroundColor: Colors.surfaceSecondary,
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    marginBottom: Spacing.md,
  },
  courtFormHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  courtFormTitle: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.text,
  },
  removeButton: {
    padding: Spacing.xs,
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: Spacing.xs,
  },
  switchInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  switchLabel: {
    fontSize: FontSizes.md,
    color: Colors.text,
    marginLeft: Spacing.sm,
  },
  addCourtButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: Spacing.md,
    borderWidth: 2,
    borderColor: Colors.primary,
    borderStyle: 'dashed',
    borderRadius: BorderRadius.md,
    marginBottom: Spacing.md,
  },
  addCourtText: {
    fontSize: FontSizes.md,
    color: Colors.primary,
    fontWeight: '600',
    marginLeft: Spacing.sm,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: Spacing.md,
    paddingTop: Spacing.md,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  modalButton: {
    flex: 1,
  },
});