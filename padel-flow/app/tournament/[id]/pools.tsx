// app/tournament/[id]/pools.tsx
// Écran d'affichage des poules

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
  ActivityIndicator,
} from 'react-native';
import { useLocalSearchParams, router, Stack, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../../context/AuthContext';
import {
  getPools,
  submitPoolScore,
  generateFinalPhase,
  PoolData,
  PoolMatchData,
  PoolScoreInput,
} from '../../../services/api';
import { Button, Input } from '../../../components';
import { Colors, Spacing, FontSizes, BorderRadius } from '../../../constants/theme';

export default function PoolsScreen() {
  const { id, clubId } = useLocalSearchParams<{ id: string; clubId: string }>();
  const { token } = useAuth();

  const [pools, setPools] = useState<PoolData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activePoolIndex, setActivePoolIndex] = useState(0);

  // Modal score
  const [showScoreModal, setShowScoreModal] = useState(false);
  const [selectedMatch, setSelectedMatch] = useState<PoolMatchData | null>(null);
  const [scores, setScores] = useState({ set1: ['', ''], set2: ['', ''], set3: ['', ''] });
  const [winnerId, setWinnerId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchData = async () => {
    if (!token || !id) return;
    try {
      const data = await getPools(token, id);
      setPools(Array.isArray(data) ? data : []);
    } catch (e: any) {
      console.error('Erreur:', e);
      Alert.alert('Erreur', e.message || 'Impossible de charger les poules');
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

  const openScoreModal = (match: PoolMatchData) => {
    if (match.is_finished) return;
    setSelectedMatch(match);
    setScores({ set1: ['', ''], set2: ['', ''], set3: ['', ''] });
    setWinnerId(null);
    setShowScoreModal(true);
  };

  const parseScore = (): { scoreString: string; team1Sets: number; team2Sets: number; team1Games: number; team2Games: number } | null => {
    const sets: string[] = [];
    let team1Sets = 0;
    let team2Sets = 0;
    let team1Games = 0;
    let team2Games = 0;

    [scores.set1, scores.set2, scores.set3].forEach(([s1, s2]) => {
      if (s1 && s2) {
        const g1 = parseInt(s1);
        const g2 = parseInt(s2);
        sets.push(`${g1}-${g2}`);
        team1Games += g1;
        team2Games += g2;
        if (g1 > g2) team1Sets++;
        else if (g2 > g1) team2Sets++;
      }
    });

    if (sets.length === 0) return null;

    return {
      scoreString: sets.join(' '),
      team1Sets,
      team2Sets,
      team1Games,
      team2Games,
    };
  };

  const handleSubmitScore = async () => {
    if (!selectedMatch || !winnerId || !token || !id) return;

    const parsed = parseScore();
    if (!parsed) {
      Alert.alert('Erreur', 'Veuillez entrer au moins un set');
      return;
    }

    setIsSubmitting(true);
    try {
      const scoreData: PoolScoreInput = {
        score: parsed.scoreString,
        winner_team_id: winnerId,
        team1_sets: parsed.team1Sets,
        team2_sets: parsed.team2Sets,
        team1_games: parsed.team1Games,
        team2_games: parsed.team2Games,
      };

      await submitPoolScore(token, id, selectedMatch.id, scoreData);
      setShowScoreModal(false);
      fetchData();
      Alert.alert('Succès', 'Score enregistré');
    } catch (e: any) {
      Alert.alert('Erreur', e.message || 'Impossible d\'enregistrer le score');
    } finally {
      setIsSubmitting(false);
    }
  };

  const checkAllPoolsFinished = (): boolean => {
    return pools.every(pool => pool.progress.percentage === 100);
  };

  const handleGenerateFinalPhase = async () => {
    if (!checkAllPoolsFinished()) {
      Alert.alert('Erreur', 'Toutes les poules doivent être terminées avant de générer la phase finale');
      return;
    }

    Alert.alert(
      'Générer la phase finale',
      'Les 1ers et 2èmes de chaque poule seront qualifiés pour la phase finale. Continuer ?',
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Générer',
          onPress: async () => {
            if (!token || !id) return;
            try {
              await generateFinalPhase(token, id);
              Alert.alert('Succès', 'Phase finale générée !', [
                {
                  text: 'Voir le bracket',
                  onPress: () => router.push(`/tournament/${id}/bracket?clubId=${clubId}`),
                },
              ]);
            } catch (e: any) {
              Alert.alert('Erreur', e.message || 'Impossible de générer la phase finale');
            }
          },
        },
      ]
    );
  };

  const getTeamName = (team: { players: { first_name: string; last_name: string }[] } | null): string => {
    if (!team || !team.players || team.players.length < 2) return 'Équipe';
    return `${team.players[0].last_name} / ${team.players[1].last_name}`;
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={styles.loadingText}>Chargement des poules...</Text>
      </View>
    );
  }

  if (pools.length === 0) {
    return (
      <>
        <Stack.Screen options={{ headerShown: false }} />
        <View style={styles.container}>
          <View style={styles.headerContainer}>
            <View style={styles.statusBarSpacer} />
            <View style={styles.headerBar}>
              <TouchableOpacity onPress={() => router.back()} style={styles.headerButton}>
                <Ionicons name="arrow-back" size={24} color={Colors.textInverse} />
              </TouchableOpacity>
              <Text style={styles.headerTitle}>Poules</Text>
              <View style={styles.headerButton} />
            </View>
          </View>
          <View style={styles.emptyContainer}>
            <Ionicons name="grid-outline" size={64} color={Colors.textLight} />
            <Text style={styles.emptyText}>Aucune poule générée</Text>
            <Button
              title="Retour"
              onPress={() => router.back()}
              style={{ marginTop: Spacing.lg }}
            />
          </View>
        </View>
      </>
    );
  }

  const activePool = pools[activePoolIndex];

  return (
    <>
      <Stack.Screen options={{ headerShown: false }} />

      <View style={styles.container}>
        {/* Header */}
        <View style={styles.headerContainer}>
          <View style={styles.statusBarSpacer} />
          <View style={styles.headerBar}>
            <TouchableOpacity onPress={() => router.back()} style={styles.headerButton}>
              <Ionicons name="arrow-back" size={24} color={Colors.textInverse} />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Poules</Text>
            <TouchableOpacity 
              onPress={() => router.push(`/tournament/${id}/bracket?clubId=${clubId}`)}
              style={styles.headerButton}
            >
              <Ionicons name="git-branch" size={24} color={Colors.textInverse} />
            </TouchableOpacity>
          </View>

          {/* Onglets des poules */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.poolTabs}>
            {pools.map((pool, index) => (
              <TouchableOpacity
                key={pool.id}
                style={[styles.poolTab, activePoolIndex === index && styles.poolTabActive]}
                onPress={() => setActivePoolIndex(index)}
              >
                <Text style={[styles.poolTabText, activePoolIndex === index && styles.poolTabTextActive]}>
                  {pool.name}
                </Text>
                <Text style={[styles.poolTabProgress, activePoolIndex === index && styles.poolTabProgressActive]}>
                  {pool.progress.percentage}%
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        {/* Contenu */}
        <ScrollView
          style={styles.content}
          refreshControl={
            <RefreshControl refreshing={isRefreshing} onRefresh={handleRefresh} colors={[Colors.primary]} />
          }
        >
          {/* Classement de la poule */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Classement</Text>
            <View style={styles.standingsTable}>
              {/* Header */}
              <View style={styles.standingsHeader}>
                <Text style={[styles.standingsCell, styles.standingsCellRank]}>#</Text>
                <Text style={[styles.standingsCell, styles.standingsCellTeam]}>Équipe</Text>
                <Text style={[styles.standingsCell, styles.standingsCellStat]}>J</Text>
                <Text style={[styles.standingsCell, styles.standingsCellStat]}>G</Text>
                <Text style={[styles.standingsCell, styles.standingsCellStat]}>P</Text>
                <Text style={[styles.standingsCell, styles.standingsCellStat]}>Sets</Text>
                <Text style={[styles.standingsCell, styles.standingsCellPts]}>Pts</Text>
              </View>
              
              {/* Rows */}
              {activePool.teams.map((team, index) => (
                <View 
                  key={team.team_id} 
                  style={[
                    styles.standingsRow,
                    index < 2 && styles.standingsRowQualified
                  ]}
                >
                  <Text style={[styles.standingsCell, styles.standingsCellRank]}>
                    {team.rank}
                  </Text>
                  <View style={[styles.standingsCell, styles.standingsCellTeam]}>
                    <Text style={styles.standingsTeamName} numberOfLines={1}>
                      {team.players.length >= 2 
                        ? `${team.players[0].last_name} / ${team.players[1].last_name}`
                        : 'Équipe'}
                    </Text>
                    {team.is_seeded && (
                      <Ionicons name="star" size={12} color={Colors.accent} />
                    )}
                  </View>
                  <Text style={[styles.standingsCell, styles.standingsCellStat]}>
                    {team.stats.matches_played}
                  </Text>
                  <Text style={[styles.standingsCell, styles.standingsCellStat, styles.statWin]}>
                    {team.stats.matches_won}
                  </Text>
                  <Text style={[styles.standingsCell, styles.standingsCellStat, styles.statLoss]}>
                    {team.stats.matches_lost}
                  </Text>
                  <Text style={[styles.standingsCell, styles.standingsCellStat]}>
                    {team.stats.sets_won}-{team.stats.sets_lost}
                  </Text>
                  <Text style={[styles.standingsCell, styles.standingsCellPts, styles.standingsPts]}>
                    {team.stats.points}
                  </Text>
                </View>
              ))}
            </View>
            
            <View style={styles.legendContainer}>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: Colors.successLight }]} />
                <Text style={styles.legendText}>Qualifié pour la phase finale</Text>
              </View>
            </View>
          </View>

          {/* Matchs de la poule */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Matchs</Text>
            {activePool.matches.map((match) => (
              <TouchableOpacity
                key={match.id}
                style={[
                  styles.matchCard,
                  match.is_finished && styles.matchCardFinished
                ]}
                onPress={() => openScoreModal(match)}
                disabled={match.is_finished}
              >
                <View style={styles.matchTeams}>
                  <View style={styles.matchTeamRow}>
                    <Text style={[
                      styles.matchTeamName,
                      match.winner_id === match.team1_id && styles.matchTeamWinner
                    ]}>
                      {getTeamName(match.team1)}
                    </Text>
                    {match.winner_id === match.team1_id && (
                      <Ionicons name="checkmark-circle" size={18} color={Colors.success} />
                    )}
                  </View>
                  <View style={styles.matchTeamRow}>
                    <Text style={[
                      styles.matchTeamName,
                      match.winner_id === match.team2_id && styles.matchTeamWinner
                    ]}>
                      {getTeamName(match.team2)}
                    </Text>
                    {match.winner_id === match.team2_id && (
                      <Ionicons name="checkmark-circle" size={18} color={Colors.success} />
                    )}
                  </View>
                </View>

                <View style={styles.matchInfo}>
                  {match.is_finished ? (
                    <Text style={styles.matchScore}>{match.score}</Text>
                  ) : (
                    <Text style={styles.matchPending}>À jouer</Text>
                  )}
                  {match.court && (
                    <View style={styles.matchCourt}>
                      <Ionicons name="location" size={12} color={Colors.textSecondary} />
                      <Text style={styles.matchCourtText}>{match.court.name}</Text>
                    </View>
                  )}
                </View>
              </TouchableOpacity>
            ))}
          </View>

          {/* Bouton phase finale */}
          {checkAllPoolsFinished() && (
            <View style={styles.section}>
              <Button
                title="Générer la phase finale"
                onPress={handleGenerateFinalPhase}
                leftIcon="trophy"
              />
            </View>
          )}

          <View style={{ height: 40 }} />
        </ScrollView>
      </View>

      {/* Modal saisie score */}
      <Modal
        visible={showScoreModal}
        animationType="slide"
        transparent
        onRequestClose={() => setShowScoreModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Saisir le Score</Text>
              <TouchableOpacity onPress={() => setShowScoreModal(false)}>
                <Ionicons name="close" size={24} color={Colors.text} />
              </TouchableOpacity>
            </View>

            {selectedMatch && (
              <>
                {/* Sélection du vainqueur */}
                <Text style={styles.modalLabel}>Vainqueur</Text>
                <View style={styles.winnerOptions}>
                  <TouchableOpacity
                    style={[
                      styles.winnerOption,
                      winnerId === selectedMatch.team1_id && styles.winnerOptionActive,
                    ]}
                    onPress={() => setWinnerId(selectedMatch.team1_id)}
                  >
                    <Text style={[
                      styles.winnerOptionText,
                      winnerId === selectedMatch.team1_id && styles.winnerOptionTextActive,
                    ]}>
                      {getTeamName(selectedMatch.team1)}
                    </Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[
                      styles.winnerOption,
                      winnerId === selectedMatch.team2_id && styles.winnerOptionActive,
                    ]}
                    onPress={() => setWinnerId(selectedMatch.team2_id)}
                  >
                    <Text style={[
                      styles.winnerOptionText,
                      winnerId === selectedMatch.team2_id && styles.winnerOptionTextActive,
                    ]}>
                      {getTeamName(selectedMatch.team2)}
                    </Text>
                  </TouchableOpacity>
                </View>

                {/* Score par set */}
                <Text style={styles.modalLabel}>Score</Text>
                {['set1', 'set2', 'set3'].map((setKey, index) => (
                  <View key={setKey} style={styles.setRow}>
                    <Text style={styles.setLabel}>Set {index + 1}</Text>
                    <View style={styles.setInputs}>
                      <Input
                        placeholder="0"
                        value={scores[setKey as keyof typeof scores][0]}
                        onChangeText={(v) => {
                          const newScores = { ...scores };
                          newScores[setKey as keyof typeof scores][0] = v;
                          setScores(newScores);
                        }}
                        keyboardType="numeric"
                        containerStyle={styles.scoreInput}
                      />
                      <Text style={styles.scoreSeparator}>-</Text>
                      <Input
                        placeholder="0"
                        value={scores[setKey as keyof typeof scores][1]}
                        onChangeText={(v) => {
                          const newScores = { ...scores };
                          newScores[setKey as keyof typeof scores][1] = v;
                          setScores(newScores);
                        }}
                        keyboardType="numeric"
                        containerStyle={styles.scoreInput}
                      />
                    </View>
                  </View>
                ))}

                <View style={styles.modalButtons}>
                  <Button
                    title="Annuler"
                    onPress={() => setShowScoreModal(false)}
                    variant="outline"
                    style={styles.modalButton}
                  />
                  <Button
                    title="Valider"
                    onPress={handleSubmitScore}
                    loading={isSubmitting}
                    disabled={!winnerId}
                    style={styles.modalButton}
                  />
                </View>
              </>
            )}
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
  loadingText: {
    marginTop: Spacing.md,
    fontSize: FontSizes.md,
    color: Colors.textSecondary,
  },
  headerContainer: {
    backgroundColor: Colors.primary,
  },
  statusBarSpacer: {
    height: 44,
  },
  headerBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
  },
  headerButton: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontSize: FontSizes.xl,
    fontWeight: 'bold',
    color: Colors.textInverse,
  },
  poolTabs: {
    paddingHorizontal: Spacing.md,
    paddingBottom: Spacing.md,
  },
  poolTab: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.sm,
    marginRight: Spacing.sm,
    borderRadius: BorderRadius.full,
    backgroundColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center',
  },
  poolTabActive: {
    backgroundColor: Colors.surface,
  },
  poolTabText: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.textInverse,
  },
  poolTabTextActive: {
    color: Colors.primary,
  },
  poolTabProgress: {
    fontSize: FontSizes.xs,
    color: 'rgba(255,255,255,0.7)',
  },
  poolTabProgressActive: {
    color: Colors.textSecondary,
  },
  content: {
    flex: 1,
    padding: Spacing.md,
  },
  section: {
    marginBottom: Spacing.lg,
  },
  sectionTitle: {
    fontSize: FontSizes.lg,
    fontWeight: '600',
    color: Colors.text,
    marginBottom: Spacing.md,
  },
  standingsTable: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    overflow: 'hidden',
  },
  standingsHeader: {
    flexDirection: 'row',
    backgroundColor: Colors.surfaceSecondary,
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.sm,
  },
  standingsRow: {
    flexDirection: 'row',
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  standingsRowQualified: {
    backgroundColor: Colors.successLight,
  },
  standingsCell: {
    justifyContent: 'center',
  },
  standingsCellRank: {
    width: 30,
    textAlign: 'center',
    fontWeight: 'bold',
    color: Colors.text,
  },
  standingsCellTeam: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
  },
  standingsTeamName: {
    fontSize: FontSizes.sm,
    color: Colors.text,
    flex: 1,
  },
  standingsCellStat: {
    width: 35,
    textAlign: 'center',
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
  },
  standingsCellPts: {
    width: 40,
    textAlign: 'center',
  },
  standingsPts: {
    fontWeight: 'bold',
    color: Colors.primary,
    fontSize: FontSizes.md,
  },
  statWin: {
    color: Colors.success,
  },
  statLoss: {
    color: Colors.error,
  },
  legendContainer: {
    flexDirection: 'row',
    marginTop: Spacing.sm,
    paddingHorizontal: Spacing.sm,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
  },
  legendDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  legendText: {
    fontSize: FontSizes.xs,
    color: Colors.textSecondary,
  },
  matchCard: {
    flexDirection: 'row',
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    marginBottom: Spacing.sm,
    borderLeftWidth: 4,
    borderLeftColor: Colors.warning,
  },
  matchCardFinished: {
    borderLeftColor: Colors.success,
  },
  matchTeams: {
    flex: 1,
  },
  matchTeamRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    marginBottom: Spacing.xs,
  },
  matchTeamName: {
    fontSize: FontSizes.md,
    color: Colors.text,
  },
  matchTeamWinner: {
    fontWeight: 'bold',
  },
  matchInfo: {
    alignItems: 'flex-end',
    justifyContent: 'center',
  },
  matchScore: {
    fontSize: FontSizes.md,
    fontWeight: 'bold',
    color: Colors.primary,
  },
  matchPending: {
    fontSize: FontSizes.sm,
    color: Colors.warning,
    fontWeight: '500',
  },
  matchCourt: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    marginTop: Spacing.xs,
  },
  matchCourtText: {
    fontSize: FontSizes.xs,
    color: Colors.textSecondary,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: Spacing.xl,
  },
  emptyText: {
    fontSize: FontSizes.lg,
    color: Colors.textSecondary,
    marginTop: Spacing.md,
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
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
    marginBottom: Spacing.lg,
  },
  modalTitle: {
    fontSize: FontSizes.xl,
    fontWeight: 'bold',
    color: Colors.text,
  },
  modalLabel: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.text,
    marginBottom: Spacing.sm,
    marginTop: Spacing.md,
  },
  winnerOptions: {
    gap: Spacing.sm,
  },
  winnerOption: {
    padding: Spacing.md,
    borderRadius: BorderRadius.md,
    borderWidth: 2,
    borderColor: Colors.border,
    backgroundColor: Colors.surface,
  },
  winnerOptionActive: {
    borderColor: Colors.primary,
    backgroundColor: Colors.infoLight,
  },
  winnerOptionText: {
    fontSize: FontSizes.md,
    color: Colors.text,
    textAlign: 'center',
  },
  winnerOptionTextActive: {
    fontWeight: '600',
    color: Colors.primary,
  },
  setRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  setLabel: {
    width: 60,
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
  },
  setInputs: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  scoreInput: {
    flex: 1,
    marginBottom: 0,
  },
  scoreSeparator: {
    fontSize: FontSizes.lg,
    color: Colors.text,
    marginHorizontal: Spacing.sm,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: Spacing.md,
    marginTop: Spacing.lg,
  },
  modalButton: {
    flex: 1,
  },
});