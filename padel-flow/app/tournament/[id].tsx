// app/tournament/[id].tsx
// Écran détail d'un tournoi

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
  SafeAreaView,
} from 'react-native';
import { useLocalSearchParams, router, Stack, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../context/AuthContext';
import {
  getCourts,
  getTeams,
  getTournamentInfo,
  getBracketInfo,
  createTeam,
  deleteTeam,
  generateBracket,
  deleteBracket,
  Court,
  Team,
  TeamCreate,
  Player,
  TournamentInfo,
  BracketInfo,
} from '../../services/api';
import { Button, Input, Card } from '../../components';
import { Colors, Spacing, FontSizes, BorderRadius } from '../../constants/theme';

// Type pour un joueur en cours de saisie
interface PlayerForm {
  first_name: string;
  last_name: string;
  license_number: string;
  ranking: string;
}

// Type pour une équipe en cours de saisie
interface TeamForm {
  id: string;
  player1: PlayerForm;
  player2: PlayerForm;
}

const emptyPlayer = (): PlayerForm => ({
  first_name: '',
  last_name: '',
  license_number: '',
  ranking: '',
});

const emptyTeam = (): TeamForm => ({
  id: Date.now().toString(),
  player1: emptyPlayer(),
  player2: emptyPlayer(),
});

export default function TournamentDetailScreen() {
  const { id, clubId } = useLocalSearchParams<{ id: string; clubId: string }>();
  const { token } = useAuth();

  const [tournament, setTournament] = useState<TournamentInfo | null>(null);
  const [courts, setCourts] = useState<Court[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedCourts, setSelectedCourts] = useState<string[]>([]);
  const [bracketInfo, setBracketInfo] = useState<BracketInfo | null>(null);
  
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Modal ajout équipe
  const [showTeamModal, setShowTeamModal] = useState(false);
  const [teamForms, setTeamForms] = useState<TeamForm[]>([emptyTeam()]);
  const [isCreatingTeams, setIsCreatingTeams] = useState(false);

  // Modal sélection courts
  const [showCourtsModal, setShowCourtsModal] = useState(false);

  const fetchData = async () => {
    if (!token || !id || !clubId) return;
    try {
      // Récupérer les infos du tournoi (incluant bracket_generated et selected_court_ids)
      const tournamentData = await getTournamentInfo(token, id);
      setTournament(tournamentData);
      
      // Restaurer les courts sélectionnés
      if (tournamentData.selected_court_ids && tournamentData.selected_court_ids.length > 0) {
        setSelectedCourts(tournamentData.selected_court_ids);
      }

      // Récupérer les courts du club (filtrés selon indoor/outdoor du tournoi)
      const courtsData = await getCourts(token, clubId);
      // Filtrer les courts selon le type du tournoi et trier par nom
      const filteredCourts = Array.isArray(courtsData) 
        ? courtsData
            .filter(c => c.indoor === tournamentData.indoor)
            .sort((a, b) => a.name.localeCompare(b.name))
        : [];
      setCourts(filteredCourts);

      // Récupérer les équipes du tournoi
      try {
        const teamsData = await getTeams(token, id);
        setTeams(Array.isArray(teamsData) ? teamsData : []);
        
        // Récupérer les infos du bracket si équipes > 0
        if (teamsData && teamsData.length > 0) {
          const info = await getBracketInfo(token, id);
          setBracketInfo(info);
        }
      } catch (e) {
        console.log('Pas d\'équipes ou erreur:', e);
        setTeams([]);
      }
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
    }, [token, id, clubId])
  );

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchData();
  };

  // ===== GESTION DES ÉQUIPES =====

  const addTeamForm = () => {
    setTeamForms([...teamForms, emptyTeam()]);
  };

  const removeTeamForm = (formId: string) => {
    if (teamForms.length === 1) {
      Alert.alert('Info', 'Vous devez avoir au moins une équipe à créer');
      return;
    }
    setTeamForms(teamForms.filter((f) => f.id !== formId));
  };

  const updatePlayerField = (
    formId: string,
    playerKey: 'player1' | 'player2',
    field: keyof PlayerForm,
    value: string
  ) => {
    setTeamForms(
      teamForms.map((f) =>
        f.id === formId
          ? {
              ...f,
              [playerKey]: { ...f[playerKey], [field]: value },
            }
          : f
      )
    );
  };

  const resetTeamModal = () => {
  };

  const resetTeamModal = () => {
    setTeamForms([emptyTeam()]);
    setShowTeamModal(false);
  };

  const validateTeamForm = (form: TeamForm): boolean => {
    const p1 = form.player1;
    const p2 = form.player2;
    return (
      p1.first_name.trim() !== '' &&
      p1.last_name.trim() !== '' &&
      p1.license_number.trim() !== '' &&
      p1.ranking.trim() !== '' &&
      p2.first_name.trim() !== '' &&
      p2.last_name.trim() !== '' &&
      p2.license_number.trim() !== '' &&
      p2.ranking.trim() !== ''
    );
  };

  const handleCreateTeams = async () => {
    const validForms = teamForms.filter(validateTeamForm);
    
    if (validForms.length === 0) {
      Alert.alert('Erreur', 'Veuillez remplir tous les champs pour au moins une équipe');
      return;
    }

    if (!token || !id) return;

    setIsCreatingTeams(true);
    try {
      for (const form of validForms) {
        const teamData: TeamCreate = {
          players: [
            {
              first_name: form.player1.first_name.trim(),
              last_name: form.player1.last_name.trim(),
              license_number: form.player1.license_number.trim(),
              ranking: parseInt(form.player1.ranking),
            },
            {
              first_name: form.player2.first_name.trim(),
              last_name: form.player2.last_name.trim(),
              license_number: form.player2.license_number.trim(),
              ranking: parseInt(form.player2.ranking),
            },
          ],
        };
        
        await createTeam(token, id, teamData);
      }

      resetTeamModal();
      Alert.alert(
        'Succès',
        `${validForms.length} équipe${validForms.length > 1 ? 's' : ''} créée${validForms.length > 1 ? 's' : ''} !`
      );
      fetchData();
    } catch (e: any) {
      Alert.alert('Erreur', e.message || 'Impossible de créer les équipes');
    } finally {
      setIsCreatingTeams(false);
    }
  };

  const handleDeleteTeam = (teamId: string) => {
    if (tournament?.bracket_generated) {
      Alert.alert('Erreur', 'Impossible de supprimer une équipe après la génération du bracket. Réinitialisez d\'abord le bracket.');
      return;
    }
    
    Alert.alert(
      'Supprimer l\'équipe',
      'Êtes-vous sûr de vouloir supprimer cette équipe ?',
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Supprimer',
          style: 'destructive',
          onPress: async () => {
            if (!token || !id) return;
            try {
              await deleteTeam(token, id, teamId);
              setTeams(teams.filter((t) => t.id !== teamId));
            } catch (e: any) {
              Alert.alert('Erreur', e.message || 'Impossible de supprimer l\'équipe');
            }
          },
        },
      ]
    );
  };

  // ===== GESTION DES COURTS =====

  const toggleCourtSelection = (courtId: string) => {
    if (tournament?.bracket_generated) {
      Alert.alert('Info', 'Les courts ne peuvent plus être modifiés après la génération du bracket.');
      return;
    }
    
    if (selectedCourts.includes(courtId)) {
      setSelectedCourts(selectedCourts.filter((c) => c !== courtId));
    } else {
      setSelectedCourts([...selectedCourts, courtId]);
    }
  };

  // ===== GÉNÉRATION DU BRACKET =====

  const handleGenerateBracket = async () => {
    if (teams.length < 2) {
      Alert.alert('Erreur', 'Il faut au moins 2 équipes pour générer le bracket');
      return;
    }

    if (selectedCourts.length === 0) {
      Alert.alert('Erreur', 'Veuillez sélectionner au moins un court');
      return;
    }

    if (!token || !id) return;

    Alert.alert(
      'Générer le bracket',
      `Générer le bracket avec ${teams.length} équipes et ${selectedCourts.length} court(s) ?\n\nLes courts seront automatiquement assignés aux matchs.`,
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Générer',
          onPress: async () => {
            try {
              await generateBracket(token, id, selectedCourts);
              fetchData();
              Alert.alert('Succès', 'Bracket généré avec succès !', [
                {
                  text: 'Voir le bracket',
                  onPress: () => router.push(`/tournament/${id}/bracket?clubId=${clubId}`),
                },
              ]);
            } catch (e: any) {
              Alert.alert('Erreur', e.message || 'Impossible de générer le bracket');
            }
          },
        },
      ]
    );
  };

  const handleResetBracket = () => {
    Alert.alert(
      'Réinitialiser le bracket',
      'Êtes-vous sûr ? Tous les matchs et scores seront supprimés.',
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Réinitialiser',
          style: 'destructive',
          onPress: async () => {
            if (!token || !id) return;
            try {
              await deleteBracket(token, id);
              setSelectedCourts([]);
              fetchData();
              Alert.alert('Succès', 'Bracket réinitialisé');
            } catch (e: any) {
              Alert.alert('Erreur', e.message || 'Impossible de réinitialiser le bracket');
            }
          },
        },
      ]
    );
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  const getPlayerName = (player: Player) => {
    return `${player.first_name} ${player.last_name}`;
  };

  const getTeamDisplay = (team: Team) => {
    if (team.players && team.players.length >= 2) {
      return `${team.players[0].last_name} / ${team.players[1].last_name}`;
    }
    return 'Équipe incomplète';
  };

  const getPlayersRankingDisplay = (team: Team) => {
    if (team.players && team.players.length >= 2) {
      return `${team.players[0].ranking} + ${team.players[1].ranking} = ${team.combined_ranking}`;
    }
    return '';
  };

  if (isLoading) {
    return (
      <SafeAreaView style={styles.loadingContainer}>
        <Text>Chargement...</Text>
      </SafeAreaView>
    );
  }

  if (!tournament) {
    return (
      <SafeAreaView style={styles.loadingContainer}>
        <Text>Tournoi introuvable</Text>
        <Button title="Retour" onPress={() => router.back()} style={{ marginTop: 20 }} />
      </SafeAreaView>
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
        {/* Header personnalisé */}
        <View style={styles.headerContainer}>
          <View style={styles.statusBarSpacer} />
          <View style={styles.headerBar}>
            <TouchableOpacity onPress={() => router.back()} style={styles.headerButton}>
              <Ionicons name="arrow-back" size={24} color={Colors.textInverse} />
            </TouchableOpacity>
            <Text style={styles.headerTitle} numberOfLines={1}>{tournament.name}</Text>
            <View style={styles.headerButton} />
          </View>
          
          {/* Info tournoi */}
          <View style={styles.tournamentInfo}>
            <View style={styles.tournamentIcon}>
              <Ionicons name="trophy" size={32} color={Colors.textInverse} />
            </View>
            <Text style={styles.tournamentName}>{tournament.name}</Text>
            <View style={styles.tagsRow}>
              <View style={styles.tag}>
                <Text style={styles.tagText}>{tournament.category}</Text>
              </View>
              <View style={styles.tag}>
                <Text style={styles.tagText}>{tournament.gender}</Text>
              </View>
              <View style={styles.tag}>
                <Ionicons 
                  name={tournament.indoor ? 'home' : 'sunny'} 
                  size={12} 
                  color={Colors.textInverse} 
                />
                <Text style={styles.tagText}>{tournament.indoor ? 'Indoor' : 'Outdoor'}</Text>
              </View>
            </View>
            <Text style={styles.dateText}>{formatDate(tournament.start_date)}</Text>
            
            {tournament.bracket_generated && (
              <View style={styles.statusBadge}>
                <Ionicons name="checkmark-circle" size={16} color={Colors.success} />
                <Text style={styles.statusText}>Bracket généré</Text>
              </View>
            )}
          </View>
        </View>

        <ScrollView
          style={styles.scrollContent}
          refreshControl={
            <RefreshControl
              refreshing={isRefreshing}
              onRefresh={handleRefresh}
              colors={[Colors.primary]}
            />
          }
        >
          <View style={styles.content}>
            {/* Section Équipes */}
            <View style={styles.section}>
              <View style={styles.sectionHeader}>
                <Text style={styles.sectionTitle}>Équipes ({teams.length})</Text>
                {!tournament.bracket_generated && (
                  <TouchableOpacity
                    style={styles.addButton}
                    onPress={() => setShowTeamModal(true)}
                  >
                    <Ionicons name="add-circle" size={28} color={Colors.primary} />
                  </TouchableOpacity>
                )}
              </View>

              {teams.length === 0 ? (
                <Card variant="outlined" style={styles.emptyCard}>
                  <Ionicons name="people-outline" size={40} color={Colors.textLight} />
                  <Text style={styles.emptyText}>Aucune équipe</Text>
                  <Text style={styles.emptySubtext}>Ajoutez les équipes participantes</Text>
                </Card>
              ) : (
                <>
                  {/* Info bracket si équipes > 1 */}
                  {bracketInfo && teams.length >= 2 && (
                    <Card variant="outlined" style={styles.bracketInfoCard}>
                      <View style={styles.bracketInfoRow}>
                        <View style={styles.bracketInfoItem}>
                          <Text style={styles.bracketInfoValue}>{bracketInfo.bracket_size}</Text>
                          <Text style={styles.bracketInfoLabel}>Bracket</Text>
                        </View>
                        <View style={styles.bracketInfoItem}>
                          <Text style={styles.bracketInfoValue}>{bracketInfo.num_byes}</Text>
                          <Text style={styles.bracketInfoLabel}>BYE</Text>
                        </View>
                        <View style={styles.bracketInfoItem}>
                          <Text style={styles.bracketInfoValue}>{bracketInfo.num_seeds}</Text>
                          <Text style={styles.bracketInfoLabel}>Têtes série</Text>
                        </View>
                        <View style={styles.bracketInfoItem}>
                          <Text style={styles.bracketInfoValue}>{bracketInfo.recommended_courts}</Text>
                          <Text style={styles.bracketInfoLabel}>Courts rec.</Text>
                        </View>
                      </View>
                      {bracketInfo.recommendation === 'poule' && (
                        <View style={styles.warningBanner}>
                          <Ionicons name="warning" size={16} color={Colors.warning} />
                          <Text style={styles.warningText}>{bracketInfo.message}</Text>
                        </View>
                      )}
                    </Card>
                  )}

                  {teams.map((team, index) => (
                    <Card key={team.id} variant="elevated" style={[
                      styles.teamCard,
                      team.is_seeded && styles.teamCardSeeded
                    ]}>
                      <View style={styles.teamRow}>
                        <View style={[
                          styles.seedBadge,
                          team.is_seeded && styles.seedBadgeSeeded
                        ]}>
                          {team.is_seeded ? (
                            <Text style={styles.seedText}>T{team.seed_position}</Text>
                          ) : (
                            <Text style={styles.seedText}>{index + 1}</Text>
                          )}
                        </View>
                        <View style={styles.teamInfo}>
                          <View style={styles.teamNameRow}>
                            <Text style={styles.teamName}>{getTeamDisplay(team)}</Text>
                            {team.is_seeded && (
                              <View style={styles.seededBadge}>
                                <Ionicons name="star" size={12} color={Colors.accent} />
                              </View>
                            )}
                          </View>
                          <Text style={styles.teamPlayers}>
                            {team.players ? team.players.map(getPlayerName).join(' & ') : 'Joueurs non définis'}
                          </Text>
                          <Text style={styles.teamRanking}>
                            Classement : {getPlayersRankingDisplay(team)}
                          </Text>
                        </View>
                        {!tournament.bracket_generated && (
                          <TouchableOpacity
                            onPress={() => handleDeleteTeam(team.id)}
                            style={styles.deleteButton}
                          >
                            <Ionicons name="trash-outline" size={20} color={Colors.error} />
                          </TouchableOpacity>
                        )}
                      </View>
                    </Card>
                  ))}
                </>
              )}
            </View>

            {/* Section Courts sélectionnés */}
            <View style={styles.section}>
              <View style={styles.sectionHeader}>
                <Text style={styles.sectionTitle}>
                  Courts {tournament.indoor ? '(Indoor)' : '(Outdoor)'} ({selectedCourts.length})
                </Text>
                {!tournament.bracket_generated && (
                  <TouchableOpacity
                    style={styles.addButton}
                    onPress={() => setShowCourtsModal(true)}
                  >
                    <Ionicons name="tennisball" size={24} color={Colors.primary} />
                  </TouchableOpacity>
                )}
              </View>

              {selectedCourts.length === 0 ? (
                <Card variant="outlined" style={styles.emptyCard}>
                  <Ionicons name="tennisball-outline" size={40} color={Colors.textLight} />
                  <Text style={styles.emptyText}>Aucun court sélectionné</Text>
                  <Text style={styles.emptySubtext}>
                    {courts.length === 0 
                      ? `Aucun court ${tournament.indoor ? 'indoor' : 'outdoor'} disponible` 
                      : 'Sélectionnez les courts pour le tournoi'}
                  </Text>
                </Card>
              ) : (
                <View style={styles.courtsRow}>
                  {selectedCourts
                    .map((courtId) => courts.find((c) => c.id === courtId))
                    .filter((court): court is Court => court !== undefined)
                    .map((court) => (
                      <View key={court.id} style={styles.selectedCourtChip}>
                        <Ionicons
                          name={court.indoor ? 'home' : 'sunny'}
                          size={16}
                          color={Colors.primary}
                        />
                        <Text style={styles.selectedCourtText}>{court.name}</Text>
                      </View>
                    ))}
                </View>
              )}
            </View>

            {/* Boutons d'action */}
            {!tournament.bracket_generated ? (
              <Button
                title="Générer le bracket"
                onPress={handleGenerateBracket}
                style={styles.actionButton}
                disabled={teams.length < 2 || selectedCourts.length === 0}
              />
            ) : (
              <View style={styles.actionButtons}>
                <Button
                  title="Voir le bracket"
                  onPress={() => router.push(`/tournament/${id}/bracket?clubId=${clubId}`)}
                  style={styles.actionButtonHalf}
                />
                <Button
                  title="Réinitialiser"
                  onPress={handleResetBracket}
                  variant="danger"
                  style={styles.actionButtonHalf}
                />
              </View>
            )}
          </View>
        </ScrollView>
      </View>

      {/* Modal ajout équipes */}
      <Modal
        visible={showTeamModal}
        animationType="slide"
        transparent
        onRequestClose={resetTeamModal}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Ajouter des Équipes</Text>
              <TouchableOpacity onPress={resetTeamModal}>
                <Ionicons name="close" size={24} color={Colors.text} />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalScroll}>
              {teamForms.map((form, index) => (
                <View key={form.id} style={styles.teamFormItem}>
                  <View style={styles.teamFormHeader}>
                    <Text style={styles.teamFormTitle}>Équipe {index + 1}</Text>
                    {teamForms.length > 1 && (
                      <TouchableOpacity onPress={() => removeTeamForm(form.id)}>
                        <Ionicons name="trash-outline" size={20} color={Colors.error} />
                      </TouchableOpacity>
                    )}
                  </View>

                  <Text style={styles.playerLabel}>Joueur 1</Text>
                  <View style={styles.playerRow}>
                    <Input
                      placeholder="Prénom"
                      value={form.player1.first_name}
                      onChangeText={(v) => updatePlayerField(form.id, 'player1', 'first_name', v)}
                      containerStyle={styles.halfInput}
                    />
                    <Input
                      placeholder="Nom"
                      value={form.player1.last_name}
                      onChangeText={(v) => updatePlayerField(form.id, 'player1', 'last_name', v)}
                      containerStyle={styles.halfInput}
                    />
                  </View>
                  <View style={styles.playerRow}>
                    <Input
                      placeholder="N° Licence"
                      value={form.player1.license_number}
                      onChangeText={(v) => updatePlayerField(form.id, 'player1', 'license_number', v)}
                      containerStyle={styles.halfInput}
                    />
                    <Input
                      placeholder="Classement"
                      value={form.player1.ranking}
                      onChangeText={(v) => updatePlayerField(form.id, 'player1', 'ranking', v)}
                      keyboardType="numeric"
                      containerStyle={styles.halfInput}
                    />
                  </View>

                  <Text style={styles.playerLabel}>Joueur 2</Text>
                  <View style={styles.playerRow}>
                    <Input
                      placeholder="Prénom"
                      value={form.player2.first_name}
                      onChangeText={(v) => updatePlayerField(form.id, 'player2', 'first_name', v)}
                      containerStyle={styles.halfInput}
                    />
                    <Input
                      placeholder="Nom"
                      value={form.player2.last_name}
                      onChangeText={(v) => updatePlayerField(form.id, 'player2', 'last_name', v)}
                      containerStyle={styles.halfInput}
                    />
                  </View>
                  <View style={styles.playerRow}>
                    <Input
                      placeholder="N° Licence"
                      value={form.player2.license_number}
                      onChangeText={(v) => updatePlayerField(form.id, 'player2', 'license_number', v)}
                      containerStyle={styles.halfInput}
                    />
                    <Input
                      placeholder="Classement"
                      value={form.player2.ranking}
                      onChangeText={(v) => updatePlayerField(form.id, 'player2', 'ranking', v)}
                      keyboardType="numeric"
                      containerStyle={styles.halfInput}
                    />
                  </View>
                </View>
              ))}

              <TouchableOpacity style={styles.addTeamButton} onPress={addTeamForm}>
                <Ionicons name="add-circle-outline" size={24} color={Colors.primary} />
                <Text style={styles.addTeamText}>Ajouter une autre équipe</Text>
              </TouchableOpacity>
            </ScrollView>

            <View style={styles.modalButtons}>
              <Button
                title="Annuler"
                onPress={resetTeamModal}
                variant="outline"
                style={styles.modalButton}
              />
              <Button
                title="Créer"
                onPress={handleCreateTeams}
                loading={isCreatingTeams}
                style={styles.modalButton}
              />
            </View>
          </View>
        </View>
      </Modal>

      {/* Modal sélection courts */}
      <Modal
        visible={showCourtsModal}
        animationType="slide"
        transparent
        onRequestClose={() => setShowCourtsModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>
                Sélectionner les Courts {tournament.indoor ? '(Indoor)' : '(Outdoor)'}
              </Text>
              <TouchableOpacity onPress={() => setShowCourtsModal(false)}>
                <Ionicons name="close" size={24} color={Colors.text} />
              </TouchableOpacity>
            </View>

            {courts.length === 0 ? (
              <View style={styles.emptyCard}>
                <Ionicons name="tennisball-outline" size={40} color={Colors.textLight} />
                <Text style={styles.emptyText}>Aucun court {tournament.indoor ? 'indoor' : 'outdoor'}</Text>
                <Text style={styles.emptySubtext}>Ajoutez d'abord des courts au club</Text>
              </View>
            ) : (
              <ScrollView style={styles.modalScroll}>
                {courts.map((court) => (
                  <TouchableOpacity
                    key={court.id}
                    style={[
                      styles.courtSelectItem,
                      selectedCourts.includes(court.id) && styles.courtSelectItemActive,
                    ]}
                    onPress={() => toggleCourtSelection(court.id)}
                  >
                    <View style={styles.courtSelectInfo}>
                      <Ionicons
                        name={court.indoor ? 'home' : 'sunny'}
                        size={24}
                        color={selectedCourts.includes(court.id) ? Colors.primary : Colors.textSecondary}
                      />
                      <View style={styles.courtSelectText}>
                        <Text style={styles.courtSelectName}>{court.name}</Text>
                        <Text style={styles.courtSelectType}>
                          {court.indoor ? 'Indoor' : 'Outdoor'}
                        </Text>
                      </View>
                    </View>
                    <Ionicons
                      name={selectedCourts.includes(court.id) ? 'checkmark-circle' : 'ellipse-outline'}
                      size={24}
                      color={selectedCourts.includes(court.id) ? Colors.primary : Colors.textLight}
                    />
                  </TouchableOpacity>
                ))}
              </ScrollView>
            )}

            <Button
              title="Confirmer"
              onPress={() => setShowCourtsModal(false)}
              style={styles.confirmButton}
            />
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
    backgroundColor: Colors.accent,
  },
  statusBarSpacer: {
    height: 44,
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
    width: 48,
  },
  headerTitle: {
    flex: 1,
    fontSize: FontSizes.lg,
    fontWeight: '600',
    color: Colors.textInverse,
    textAlign: 'center',
  },
  tournamentInfo: {
    alignItems: 'center',
    paddingVertical: Spacing.md,
    paddingBottom: Spacing.xl,
  },
  tournamentIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.md,
  },
  tournamentName: {
    fontSize: FontSizes.xl,
    fontWeight: 'bold',
    color: Colors.textInverse,
    textAlign: 'center',
  },
  tagsRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
    marginTop: Spacing.sm,
  },
  tag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingHorizontal: Spacing.sm,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.sm,
  },
  tagText: {
    color: Colors.textInverse,
    fontSize: FontSizes.sm,
    fontWeight: '500',
  },
  dateText: {
    color: Colors.textInverse,
    fontSize: FontSizes.sm,
    marginTop: Spacing.sm,
    opacity: 0.9,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    backgroundColor: Colors.successLight,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.full,
    marginTop: Spacing.md,
  },
  statusText: {
    color: Colors.success,
    fontSize: FontSizes.sm,
    fontWeight: '600',
  },
  scrollContent: {
    flex: 1,
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
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    borderWidth: 1,
    borderColor: Colors.border,
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
    textAlign: 'center',
  },
  teamCard: {
    marginBottom: Spacing.sm,
  },
  teamCardSeeded: {
    borderLeftWidth: 3,
    borderLeftColor: Colors.accent,
  },
  teamRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  teamNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
  },
  seedBadge: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  seedBadgeSeeded: {
    backgroundColor: Colors.accent,
  },
  seededBadge: {
    backgroundColor: Colors.warningLight,
    borderRadius: 10,
    padding: 2,
  },
  seedText: {
    color: Colors.textInverse,
    fontWeight: 'bold',
    fontSize: FontSizes.xs,
  },
  teamInfo: {
    flex: 1,
    marginLeft: Spacing.md,
  },
  teamName: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.text,
  },
  teamPlayers: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    marginTop: 2,
  },
  teamRanking: {
    fontSize: FontSizes.xs,
    color: Colors.textLight,
    marginTop: 2,
  },
  bracketInfoCard: {
    marginBottom: Spacing.md,
    padding: Spacing.md,
  },
  bracketInfoRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  bracketInfoItem: {
    alignItems: 'center',
  },
  bracketInfoValue: {
    fontSize: FontSizes.xl,
    fontWeight: 'bold',
    color: Colors.primary,
  },
  bracketInfoLabel: {
    fontSize: FontSizes.xs,
    color: Colors.textSecondary,
  },
  warningBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.warningLight,
    padding: Spacing.sm,
    borderRadius: BorderRadius.sm,
    marginTop: Spacing.sm,
    gap: Spacing.xs,
  },
  warningText: {
    flex: 1,
    fontSize: FontSizes.sm,
    color: Colors.warning,
  },
  deleteButton: {
    padding: Spacing.sm,
  },
  courtsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  selectedCourtChip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.infoLight,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.full,
    gap: Spacing.xs,
  },
  selectedCourtText: {
    color: Colors.primary,
    fontWeight: '500',
  },
  actionButton: {
    marginTop: Spacing.md,
  },
  actionButtons: {
    flexDirection: 'row',
    gap: Spacing.md,
    marginTop: Spacing.md,
  },
  actionButtonHalf: {
    flex: 1,
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
    maxHeight: '85%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.md,
  },
  modalTitle: {
    fontSize: FontSizes.lg,
    fontWeight: 'bold',
    color: Colors.text,
    flex: 1,
  },
  modalScroll: {
    maxHeight: 450,
  },
  teamFormItem: {
    backgroundColor: Colors.surfaceSecondary,
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    marginBottom: Spacing.md,
  },
  teamFormHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  teamFormTitle: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.text,
  },
  playerLabel: {
    fontSize: FontSizes.sm,
    fontWeight: '600',
    color: Colors.primary,
    marginTop: Spacing.sm,
    marginBottom: Spacing.xs,
  },
  playerRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
  },
  halfInput: {
    flex: 1,
  },
  addTeamButton: {
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
  addTeamText: {
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
  courtSelectItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: Spacing.md,
    borderRadius: BorderRadius.md,
    marginBottom: Spacing.sm,
    backgroundColor: Colors.surfaceSecondary,
  },
  courtSelectItemActive: {
    backgroundColor: Colors.infoLight,
    borderWidth: 1,
    borderColor: Colors.primary,
  },
  courtSelectInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  courtSelectText: {
    marginLeft: Spacing.md,
  },
  courtSelectName: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.text,
  },
  courtSelectType: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
  },
  confirmButton: {
    marginTop: Spacing.md,
  },
});