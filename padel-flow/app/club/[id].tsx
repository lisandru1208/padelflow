// app/club/[id].tsx
// Écran détail d'un club avec onglets

import React, { useState, useCallback, useRef } from 'react';
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
  Dimensions,
  Animated,
  PanResponder,
} from 'react-native';
import { useLocalSearchParams, router, Stack, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../context/AuthContext';
import {
  getClubs,
  getCourts,
  getTournaments,
  createCourt,
  deleteCourt,
  deleteTournament,
  deleteClub,
  updateClub,
  Club,
  Court,
  Tournament,
} from '../../services/api';
import { Button, Input, Card } from '../../components';
import { Colors, Spacing, FontSizes, BorderRadius } from '../../constants/theme';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

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

  // Onglets
  const [activeTab, setActiveTab] = useState(0);
  const translateX = useRef(new Animated.Value(0)).current;

  // Modal création courts
  const [showCourtModal, setShowCourtModal] = useState(false);
  const [courtForms, setCourtForms] = useState<CourtForm[]>([
    { id: '1', name: '', indoor: false }
  ]);
  const [isCreatingCourts, setIsCreatingCourts] = useState(false);

  // Modal options/édition club
  const [showOptionsModal, setShowOptionsModal] = useState(false);
  const [showEditClubModal, setShowEditClubModal] = useState(false);
  const [editClubName, setEditClubName] = useState('');
  const [editClubCity, setEditClubCity] = useState('');
  const [isUpdatingClub, setIsUpdatingClub] = useState(false);

  const fetchData = async () => {
    if (!token || !id) return;
    try {
      const clubs = await getClubs(token);
      const foundClub = clubs.find((c) => c.id === id);
      setClub(foundClub || null);
      if (foundClub) {
        setEditClubName(foundClub.name);
        setEditClubCity(foundClub.city || '');
      }

      const courtsData = await getCourts(token, id);
      const sortedCourts = Array.isArray(courtsData) 
        ? courtsData.sort((a, b) => a.name.localeCompare(b.name))
        : [];
      setCourts(sortedCourts);

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

  // ===== ONGLETS =====

  const switchTab = (index: number) => {
    setActiveTab(index);
    Animated.spring(translateX, {
      toValue: -index * SCREEN_WIDTH,
      useNativeDriver: true,
      friction: 8,
    }).start();
  };

  const handleSwipe = (gestureState: any) => {
    if (gestureState.dx < -50 && activeTab === 0) {
      // Swipe vers la gauche -> aller à l'onglet 1
      switchTab(1);
    } else if (gestureState.dx > 50 && activeTab === 1) {
      // Swipe vers la droite -> aller à l'onglet 0
      switchTab(0);
    }
  };

  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, gestureState) => {
        return Math.abs(gestureState.dx) > 20;
      },
      onPanResponderRelease: (_, gestureState) => {
        handleSwipe(gestureState);
      },
    })
  ).current;

  // ===== GESTION DU CLUB =====

  const handleUpdateClub = async () => {
    if (!editClubName.trim()) {
      Alert.alert('Erreur', 'Le nom du club est requis');
      return;
    }

    if (!token || !id) return;

    setIsUpdatingClub(true);
    try {
      await updateClub(token, id, editClubName.trim(), editClubCity.trim());
      setShowEditClubModal(false);
      fetchData();
      Alert.alert('Succès', 'Club modifié');
    } catch (e: any) {
      Alert.alert('Erreur', e.message || 'Impossible de modifier le club');
    } finally {
      setIsUpdatingClub(false);
    }
  };

  const handleDeleteClub = () => {
    setShowOptionsModal(false);
    Alert.alert(
      'Supprimer le club',
      `Êtes-vous sûr de vouloir supprimer "${club?.name}" ?\n\n⚠️ Toutes les compétitions, équipes et courts seront définitivement supprimés.`,
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Supprimer',
          style: 'destructive',
          onPress: async () => {
            if (!token || !id) return;
            try {
              await deleteClub(token, id);
              Alert.alert('Succès', 'Club supprimé');
              router.replace('/(tabs)');
            } catch (e: any) {
              Alert.alert('Erreur', e.message || 'Impossible de supprimer le club');
            }
          },
        },
      ]
    );
  };

  // ===== GESTION DES COURTS =====

  const addCourtForm = () => {
    const newId = Date.now().toString();
    setCourtForms([...courtForms, { id: newId, name: '', indoor: false }]);
  };

  const removeCourtForm = (formId: string) => {
    if (courtForms.length === 1) {
      Alert.alert('Info', 'Vous devez avoir au moins un court à créer');
      return;
    }
    setCourtForms(courtForms.filter((f) => f.id !== formId));
  };

  const updateCourtForm = (formId: string, field: 'name' | 'indoor', value: string | boolean) => {
    setCourtForms(
      courtForms.map((f) =>
        f.id === formId ? { ...f, [field]: value } : f
      )
    );
  };

  const resetCourtModal = () => {
    setCourtForms([{ id: '1', name: '', indoor: false }]);
    setShowCourtModal(false);
  };

  const handleCreateCourts = async () => {
    const validCourts = courtForms.filter((f) => f.name.trim() !== '');
    if (validCourts.length === 0) {
      Alert.alert('Erreur', 'Veuillez renseigner au moins un nom de court');
      return;
    }

    if (!token || !id) return;

    setIsCreatingCourts(true);
    try {
      await Promise.all(
        validCourts.map((court) =>
          createCourt(token, id, court.name.trim(), court.indoor)
        )
      );

      resetCourtModal();
      Alert.alert(
        'Succès',
        `${validCourts.length} court${validCourts.length > 1 ? 's' : ''} créé${validCourts.length > 1 ? 's' : ''} !`
      );
      fetchData();
    } catch (e: any) {
      Alert.alert('Erreur', e.message || 'Impossible de créer les courts');
    } finally {
      setIsCreatingCourts(false);
    }
  };

  const handleDeleteCourt = (court: Court) => {
    Alert.alert(
      'Supprimer le court',
      `Êtes-vous sûr de vouloir supprimer "${court.name}" ?`,
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Supprimer',
          style: 'destructive',
          onPress: async () => {
            if (!token || !id) return;
            try {
              await deleteCourt(token, id, court.id);
              setCourts(courts.filter((c) => c.id !== court.id));
            } catch (e: any) {
              Alert.alert('Erreur', e.message || 'Impossible de supprimer le court');
            }
          },
        },
      ]
    );
  };

  // ===== GESTION DES TOURNOIS =====

  const handleDeleteTournament = (tournament: Tournament) => {
    Alert.alert(
      'Supprimer la compétition',
      `Êtes-vous sûr de vouloir supprimer "${tournament.name}" ?\n\nToutes les équipes et matchs seront supprimés.`,
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Supprimer',
          style: 'destructive',
          onPress: async () => {
            if (!token || !id) return;
            try {
              await deleteTournament(token, id, tournament.id);
              setTournaments(tournaments.filter((t) => t.id !== tournament.id));
            } catch (e: any) {
              Alert.alert('Erreur', e.message || 'Impossible de supprimer la compétition');
            }
          },
        },
      ]
    );
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
          headerShown: false,
        }}
      />
      
      <View style={styles.container}>
        {/* Header personnalisé avec SafeArea */}
        <View style={styles.headerContainer}>
          <View style={styles.statusBarSpacer} />
          <View style={styles.headerBar}>
            <TouchableOpacity onPress={() => router.back()} style={styles.headerButton}>
              <Ionicons name="arrow-back" size={24} color={Colors.textInverse} />
            </TouchableOpacity>
            <Text style={styles.headerTitle} numberOfLines={1}>{club.name}</Text>
            <TouchableOpacity onPress={() => setShowOptionsModal(true)} style={styles.headerButton}>
              <Ionicons name="ellipsis-vertical" size={24} color={Colors.textInverse} />
            </TouchableOpacity>
          </View>
          
          {/* Info club */}
          <View style={styles.clubInfo}>
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

          {/* Onglets */}
          <View style={styles.tabsContainer}>
            <TouchableOpacity
              style={[styles.tab, activeTab === 0 && styles.tabActive]}
              onPress={() => switchTab(0)}
            >
              <Ionicons 
                name="trophy" 
                size={20} 
                color={activeTab === 0 ? Colors.primary : Colors.textInverse} 
              />
              <Text style={[styles.tabText, activeTab === 0 && styles.tabTextActive]}>
                Compétitions ({tournaments.length})
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.tab, activeTab === 1 && styles.tabActive]}
              onPress={() => switchTab(1)}
            >
              <Ionicons 
                name="tennisball" 
                size={20} 
                color={activeTab === 1 ? Colors.primary : Colors.textInverse} 
              />
              <Text style={[styles.tabText, activeTab === 1 && styles.tabTextActive]}>
                Courts ({courts.length})
              </Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Contenu swipable */}
        <Animated.View
          style={[
            styles.tabContent,
            { transform: [{ translateX }] }
          ]}
          {...panResponder.panHandlers}
        >
          {/* Onglet Compétitions */}
          <ScrollView
            style={styles.tabPage}
            refreshControl={
              <RefreshControl
                refreshing={isRefreshing}
                onRefresh={handleRefresh}
                colors={[Colors.primary]}
              />
            }
          >
            <View style={styles.tabPageContent}>
              {tournaments.length === 0 ? (
                <Card variant="outlined" style={styles.emptyCard}>
                  <Ionicons name="trophy-outline" size={48} color={Colors.textLight} />
                  <Text style={styles.emptyText}>Aucune compétition</Text>
                  <Text style={styles.emptySubtext}>
                    {courts.length === 0 
                      ? 'Créez d\'abord des courts pour pouvoir organiser une compétition'
                      : 'Créez votre première compétition'}
                  </Text>
                  <Button
                    title={courts.length === 0 ? "Créer des courts d'abord" : "Créer une compétition"}
                    onPress={() => {
                      if (courts.length === 0) {
                        switchTab(1);
                        setTimeout(() => setShowCourtModal(true), 300);
                      } else {
                        router.push(`/tournament/create?clubId=${id}`);
                      }
                    }}
                    style={{ marginTop: Spacing.md }}
                  />
                </Card>
              ) : (
                tournaments.map((tournament) => (
                  <Card
                    key={tournament.id}
                    variant="elevated"
                    onPress={() => router.push(`/tournament/${tournament.id}?clubId=${id}`)}
                    style={styles.listCard}
                  >
                    <View style={styles.listRow}>
                      <View style={[styles.listIcon, { backgroundColor: Colors.warningLight }]}>
                        <Ionicons name="trophy" size={24} color={Colors.accent} />
                      </View>
                      <View style={styles.listInfo}>
                        <Text style={styles.listTitle}>{tournament.name}</Text>
                        <Text style={styles.listSubtitle}>
                          {tournament.category} • {tournament.gender} • {tournament.indoor ? 'Indoor' : 'Outdoor'}
                        </Text>
                        <Text style={styles.listDate}>{formatDate(tournament.start_date)}</Text>
                      </View>
                      <TouchableOpacity
                        onPress={() => handleDeleteTournament(tournament)}
                        style={styles.deleteButton}
                      >
                        <Ionicons name="trash-outline" size={20} color={Colors.error} />
                      </TouchableOpacity>
                    </View>
                  </Card>
                ))
              )}
            </View>
          </ScrollView>

          {/* Onglet Courts */}
          <ScrollView
            style={styles.tabPage}
            refreshControl={
              <RefreshControl
                refreshing={isRefreshing}
                onRefresh={handleRefresh}
                colors={[Colors.primary]}
              />
            }
          >
            <View style={styles.tabPageContent}>
              {courts.length === 0 ? (
                <Card variant="outlined" style={styles.emptyCard}>
                  <Ionicons name="tennisball-outline" size={48} color={Colors.textLight} />
                  <Text style={styles.emptyText}>Aucun court</Text>
                  <Text style={styles.emptySubtext}>Ajoutez vos courts de padel</Text>
                  <Button
                    title="Ajouter des courts"
                    onPress={() => setShowCourtModal(true)}
                    style={{ marginTop: Spacing.md }}
                  />
                </Card>
              ) : (
                courts.map((court) => (
                  <Card key={court.id} variant="elevated" style={styles.listCard}>
                    <View style={styles.listRow}>
                      <View style={[
                        styles.listIcon,
                        { backgroundColor: court.indoor ? Colors.infoLight : Colors.warningLight }
                      ]}>
                        <Ionicons
                          name={court.indoor ? 'home' : 'sunny'}
                          size={24}
                          color={court.indoor ? Colors.info : Colors.accent}
                        />
                      </View>
                      <View style={styles.listInfo}>
                        <Text style={styles.listTitle}>{court.name}</Text>
                        <Text style={styles.listSubtitle}>
                          {court.indoor ? 'Indoor (couvert)' : 'Outdoor (extérieur)'}
                        </Text>
                      </View>
                      <TouchableOpacity
                        onPress={() => handleDeleteCourt(court)}
                        style={styles.deleteButton}
                      >
                        <Ionicons name="trash-outline" size={20} color={Colors.error} />
                      </TouchableOpacity>
                    </View>
                  </Card>
                ))
              )}
            </View>
          </ScrollView>
        </Animated.View>

        {/* FAB (bouton flottant) */}
        <TouchableOpacity
          style={styles.fab}
          onPress={() => {
            if (activeTab === 0) {
              // Vérifier s'il y a des courts avant de créer une compétition
              if (courts.length === 0) {
                Alert.alert(
                  'Courts requis',
                  'Vous devez d\'abord créer au moins un court avant de pouvoir créer une compétition.',
                  [
                    { text: 'Annuler', style: 'cancel' },
                    { 
                      text: 'Créer un court', 
                      onPress: () => {
                        switchTab(1);
                        setTimeout(() => setShowCourtModal(true), 300);
                      }
                    },
                  ]
                );
              } else {
                router.push(`/tournament/create?clubId=${id}`);
              }
            } else {
              setShowCourtModal(true);
            }
          }}
        >
          <Ionicons name="add" size={28} color={Colors.textInverse} />
        </TouchableOpacity>
      </View>

      {/* Modal création courts */}
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
                      <TouchableOpacity onPress={() => removeCourtForm(form.id)}>
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
                      <Text style={styles.switchLabel}>Indoor (couvert)</Text>
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
                title="Créer"
                onPress={handleCreateCourts}
                loading={isCreatingCourts}
                style={styles.modalButton}
              />
            </View>
          </View>
        </View>
      </Modal>

      {/* Modal options club */}
      <Modal
        visible={showOptionsModal}
        animationType="fade"
        transparent
        onRequestClose={() => setShowOptionsModal(false)}
      >
        <TouchableOpacity
          style={styles.optionsModalOverlay}
          activeOpacity={1}
          onPress={() => setShowOptionsModal(false)}
        >
          <View style={styles.optionsModalContent}>
            <TouchableOpacity
              style={styles.optionItem}
              onPress={() => {
                setShowOptionsModal(false);
                setShowEditClubModal(true);
              }}
            >
              <Ionicons name="create-outline" size={24} color={Colors.primary} />
              <Text style={[styles.optionText, { color: Colors.primary }]}>Modifier le club</Text>
            </TouchableOpacity>
            <View style={styles.optionDivider} />
            <TouchableOpacity
              style={styles.optionItem}
              onPress={handleDeleteClub}
            >
              <Ionicons name="trash-outline" size={24} color={Colors.error} />
              <Text style={[styles.optionText, { color: Colors.error }]}>Supprimer le club</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </Modal>

      {/* Modal édition club */}
      <Modal
        visible={showEditClubModal}
        animationType="slide"
        transparent
        onRequestClose={() => setShowEditClubModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Modifier le Club</Text>
              <TouchableOpacity onPress={() => setShowEditClubModal(false)}>
                <Ionicons name="close" size={24} color={Colors.text} />
              </TouchableOpacity>
            </View>

            <Input
              label="Nom du club"
              placeholder="Nom du club"
              value={editClubName}
              onChangeText={setEditClubName}
              leftIcon="business-outline"
            />

            <Input
              label="Ville"
              placeholder="Ville (optionnel)"
              value={editClubCity}
              onChangeText={setEditClubCity}
              leftIcon="location-outline"
            />

            <View style={styles.modalButtons}>
              <Button
                title="Annuler"
                onPress={() => setShowEditClubModal(false)}
                variant="outline"
                style={styles.modalButton}
              />
              <Button
                title="Enregistrer"
                onPress={handleUpdateClub}
                loading={isUpdatingClub}
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
  headerContainer: {
    backgroundColor: Colors.primary,
  },
  statusBarSpacer: {
    height: 44, // Hauteur approximative de la barre de statut
  },
  headerBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.sm,
    height: 56,
  },
  headerButton: {
    padding: Spacing.sm,
  },
  headerTitle: {
    flex: 1,
    fontSize: FontSizes.lg,
    fontWeight: '600',
    color: Colors.textInverse,
    textAlign: 'center',
    marginHorizontal: Spacing.sm,
  },
  clubInfo: {
    alignItems: 'center',
    paddingVertical: Spacing.md,
  },
  clubIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.sm,
  },
  clubName: {
    fontSize: FontSizes.xl,
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
  tabsContainer: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0,0,0,0.1)',
    marginHorizontal: Spacing.md,
    marginBottom: Spacing.md,
    borderRadius: BorderRadius.lg,
    padding: 4,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.md,
    gap: Spacing.xs,
  },
  tabActive: {
    backgroundColor: Colors.surface,
  },
  tabText: {
    fontSize: FontSizes.sm,
    color: Colors.textInverse,
    fontWeight: '500',
  },
  tabTextActive: {
    color: Colors.primary,
  },
  tabContent: {
    flexDirection: 'row',
    width: SCREEN_WIDTH * 2,
    flex: 1,
  },
  tabPage: {
    width: SCREEN_WIDTH,
  },
  tabPageContent: {
    padding: Spacing.md,
    paddingBottom: 100,
  },
  emptyCard: {
    alignItems: 'center',
    padding: Spacing.xl,
  },
  emptyText: {
    fontSize: FontSizes.lg,
    fontWeight: '600',
    color: Colors.text,
    marginTop: Spacing.md,
  },
  emptySubtext: {
    fontSize: FontSizes.md,
    color: Colors.textSecondary,
    marginTop: Spacing.xs,
    textAlign: 'center',
  },
  listCard: {
    marginBottom: Spacing.sm,
  },
  listRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  listIcon: {
    width: 48,
    height: 48,
    borderRadius: BorderRadius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  listInfo: {
    flex: 1,
    marginLeft: Spacing.md,
  },
  listTitle: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.text,
  },
  listSubtitle: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    marginTop: 2,
  },
  listDate: {
    fontSize: FontSizes.xs,
    color: Colors.textLight,
    marginTop: 2,
  },
  deleteButton: {
    padding: Spacing.sm,
  },
  fab: {
    position: 'absolute',
    bottom: Spacing.xl,
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
  // Options modal
  optionsModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  optionsModalContent: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    padding: Spacing.sm,
    minWidth: 250,
  },
  optionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: Spacing.md,
    borderRadius: BorderRadius.md,
  },
  optionText: {
    fontSize: FontSizes.md,
    marginLeft: Spacing.md,
    fontWeight: '500',
  },
  optionDivider: {
    height: 1,
    backgroundColor: Colors.border,
    marginHorizontal: Spacing.sm,
  },
});