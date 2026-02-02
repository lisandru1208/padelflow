// app/tournament/[id]/bracket.tsx
// Écran bracket avec onglets Winner, Classement, Passages et Résultats

import React, { useState, useCallback, useMemo } from 'react';
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
  getRounds,
  getClassificationRounds,
  getFinalRankings,
  submitScore,
  RoundWithMatches,
  Match,
  Team,
  FinalRankings,
} from '../../../services/api';
import { Button, Input } from '../../../components';
import { Colors, Spacing, FontSizes, BorderRadius } from '../../../constants/theme';

export default function BracketScreen() {
  const { id, clubId } = useLocalSearchParams<{ id: string; clubId: string }>();
  const { token } = useAuth();

  const [winnerRounds, setWinnerRounds] = useState<RoundWithMatches[]>([]);
  const [classificationRounds, setClassificationRounds] = useState<RoundWithMatches[]>([]);
  const [finalRankings, setFinalRankings] = useState<FinalRankings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  // Onglets
  const [activeTab, setActiveTab] = useState<'winner' | 'classification' | 'passages' | 'results'>('winner');

  // Modal score
  const [showScoreModal, setShowScoreModal] = useState(false);
  const [selectedMatch, setSelectedMatch] = useState<Match | null>(null);
  const [scores, setScores] = useState({ set1: ['', ''], set2: ['', ''], set3: ['', ''] });
  const [winnerId, setWinnerId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchData = async () => {
    if (!token || !id) return;
    try {
      const [winnerData, classificationData, rankingsData] = await Promise.all([
        getRounds(token, id),
        getClassificationRounds(token, id),
        getFinalRankings(token, id)
      ]);
      setWinnerRounds(Array.isArray(winnerData) ? winnerData : []);
      setClassificationRounds(Array.isArray(classificationData) ? classificationData : []);
      setFinalRankings(rankingsData);
    } catch (e: any) {
      console.error('Erreur:', e);
      Alert.alert('Erreur', e.message || 'Impossible de charger le bracket');
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

  const openScoreModal = (match: Match) => {
    setSelectedMatch(match);
    setScores({ set1: ['', ''], set2: ['', ''], set3: ['', ''] });
    setWinnerId(null);
    setShowScoreModal(true);
  };

  const formatScoreString = (): string => {
    const sets = [];
    if (scores.set1[0] && scores.set1[1]) {
      sets.push(`${scores.set1[0]}-${scores.set1[1]}`);
    }
    if (scores.set2[0] && scores.set2[1]) {
      sets.push(`${scores.set2[0]}-${scores.set2[1]}`);
    }
    if (scores.set3[0] && scores.set3[1]) {
      sets.push(`${scores.set3[0]}-${scores.set3[1]}`);
    }
    return sets.join(' / ');
  };

  const handleSubmitScore = async () => {
    if (!selectedMatch || !winnerId || !token) {
      Alert.alert('Erreur', 'Veuillez sélectionner le vainqueur');
      return;
    }

    const scoreString = formatScoreString();
    if (!scoreString) {
      Alert.alert('Erreur', 'Veuillez entrer au moins le score du premier set');
      return;
    }

    setIsSubmitting(true);
    try {
      await submitScore(token, selectedMatch.id, {
        score: scoreString,
        winner_team_id: winnerId,
      });

      setShowScoreModal(false);
      Alert.alert('Succès', 'Score enregistré !');
      fetchData();
    } catch (e: any) {
      Alert.alert('Erreur', e.message || 'Impossible d\'enregistrer le score');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getTeamDisplay = (team?: Team | null): string => {
    if (!team || !team.players || team.players.length < 2) {
      return 'À déterminer';
    }
    return `${team.players[0].last_name} / ${team.players[1].last_name}`;
  };

  const getRoundName = (roundOrder: number, totalRounds: number): string => {
    const remaining = totalRounds - roundOrder;
    switch (remaining) {
      case 0:
        return 'Finale';
      case 1:
        return 'Demi-finales';
      case 2:
        return 'Quarts de finale';
      case 3:
        return 'Huitièmes';
      default:
        return `Tour ${roundOrder}`;
    }
  };

  const renderMatch = (match: Match) => {
    const isCompleted = match.is_finished || !!match.winner_id;
    const team1IsWinner = match.winner_id === match.team1_id;
    const team2IsWinner = match.winner_id === match.team2_id;
    const canEnterScore = match.team1 && match.team2 && !isCompleted;

    return (
      <TouchableOpacity
        key={match.id}
        style={styles.matchCard}
        onPress={() => canEnterScore && openScoreModal(match)}
        disabled={!canEnterScore}
      >
        <View style={styles.matchContent}>
          {/* Équipe 1 */}
          <View style={[
            styles.teamRow,
            team1IsWinner && styles.teamRowWinner,
          ]}>
            <Text style={[
              styles.teamName,
              team1IsWinner && styles.teamNameWinner,
              !match.team1 && styles.teamNamePending,
            ]}>
              {getTeamDisplay(match.team1)}
            </Text>
            {isCompleted && match.score && (
              <View style={styles.scoreContainer}>
                {match.score.split(' / ').map((set, idx) => (
                  <Text key={idx} style={[
                    styles.setScore,
                    team1IsWinner && styles.setScoreWinner,
                  ]}>
                    {set.split('-')[0]}
                  </Text>
                ))}
              </View>
            )}
            {team1IsWinner && (
              <Ionicons name="checkmark-circle" size={18} color={Colors.success} />
            )}
          </View>

          {/* Séparateur */}
          <View style={styles.matchSeparator} />

          {/* Équipe 2 */}
          <View style={[
            styles.teamRow,
            team2IsWinner && styles.teamRowWinner,
          ]}>
            <Text style={[
              styles.teamName,
              team2IsWinner && styles.teamNameWinner,
              !match.team2 && styles.teamNamePending,
            ]}>
              {getTeamDisplay(match.team2)}
            </Text>
            {isCompleted && match.score && (
              <View style={styles.scoreContainer}>
                {match.score.split(' / ').map((set, idx) => (
                  <Text key={idx} style={[
                    styles.setScore,
                    team2IsWinner && styles.setScoreWinner,
                  ]}>
                    {set.split('-')[1]}
                  </Text>
                ))}
              </View>
            )}
            {team2IsWinner && (
              <Ionicons name="checkmark-circle" size={18} color={Colors.success} />
            )}
          </View>
        </View>

        {/* Indicateur de statut */}
        {canEnterScore && (
          <View style={styles.matchStatus}>
            <Text style={styles.matchStatusText}>Tap pour saisir le score</Text>
          </View>
        )}

        {/* Match en attente */}
        {(!match.team1 || !match.team2) && !isCompleted && (
          <View style={styles.matchPending}>
            <Text style={styles.matchPendingText}>En attente</Text>
          </View>
        )}
        
        {/* Court assigné */}
        {match.court && (
          <View style={styles.courtBadge}>
            <Ionicons name="location" size={12} color={Colors.textSecondary} />
            <Text style={styles.courtBadgeText}>{match.court.name}</Text>
          </View>
        )}
      </TouchableOpacity>
    );
  };

  const renderFinalRankings = () => {
    if (!finalRankings || finalRankings.rankings.length === 0) {
      return (
        <View style={styles.emptyBracket}>
          <Ionicons name="podium-outline" size={48} color={Colors.textLight} />
          <Text style={styles.emptyBracketText}>Aucun résultat disponible</Text>
          <Text style={styles.emptySubtext}>Les résultats apparaîtront une fois les matchs terminés</Text>
        </View>
      );
    }

    const getMedalColor = (rank: number) => {
      switch (rank) {
        case 1: return '#FFD700'; // Or
        case 2: return '#C0C0C0'; // Argent
        case 3: return '#CD7F32'; // Bronze
        default: return Colors.textLight;
      }
    };

    const getMedalIcon = (rank: number) => {
      if (rank <= 3) return 'medal';
      return 'ribbon';
    };

    return (
      <View style={styles.rankingsContainer}>
        {/* Header avec infos tournoi */}
        <View style={styles.rankingsHeader}>
          <Text style={styles.rankingsTitle}>{finalRankings.tournament_name}</Text>
          <View style={styles.rankingsInfo}>
            <View style={styles.rankingsBadge}>
              <Text style={styles.rankingsBadgeText}>{finalRankings.category}</Text>
            </View>
            <Text style={styles.rankingsTeams}>{finalRankings.num_teams} équipes</Text>
          </View>
          {!finalRankings.tournament_finished && (
            <View style={styles.inProgressBanner}>
              <Ionicons name="time" size={16} color={Colors.warning} />
              <Text style={styles.inProgressText}>Tournoi en cours</Text>
            </View>
          )}
        </View>

        {/* Liste des classements */}
        {finalRankings.rankings.map((team, index) => (
          <View key={team.team_id} style={[
            styles.rankingCard,
            team.rank <= 3 && styles.rankingCardTop3
          ]}>
            <View style={styles.rankingLeft}>
              <View style={[
                styles.rankBadge,
                { backgroundColor: team.rank <= 3 ? getMedalColor(team.rank) : Colors.surfaceSecondary }
              ]}>
                {team.rank <= 3 ? (
                  <Ionicons name={getMedalIcon(team.rank)} size={20} color={Colors.textInverse} />
                ) : (
                  <Text style={styles.rankNumber}>{team.rank}</Text>
                )}
              </View>
            </View>
            
            <View style={styles.rankingMiddle}>
              <View style={styles.rankingNameRow}>
                <Text style={styles.rankingTeamName}>
                  {team.players.length >= 2 
                    ? `${team.players[0].last_name} / ${team.players[1].last_name}`
                    : 'Équipe'}
                </Text>
                {team.is_seeded && (
                  <View style={styles.seededBadgeSmall}>
                    <Ionicons name="star" size={10} color={Colors.accent} />
                  </View>
                )}
              </View>
              <Text style={styles.rankingPlayers}>
                {team.players.map(p => `${p.first_name} ${p.last_name}`).join(' & ')}
              </Text>
            </View>
            
            <View style={styles.rankingRight}>
              <Text style={styles.rankingPoints}>{team.points}</Text>
              <Text style={styles.rankingPointsLabel}>pts</Text>
            </View>
          </View>
        ))}
      </View>
    );
  };

  // Grouper tous les matchs par terrain pour l'onglet Passages
  const allMatchesByCourt = useMemo(() => {
    const allRounds = [...winnerRounds, ...classificationRounds];
    const matchesByCourt: { [courtName: string]: { match: Match; roundName: string }[] } = {};
    const matchesNoCourt: { match: Match; roundName: string }[] = [];
    
    allRounds.forEach(round => {
      round.matches.forEach(match => {
        const item = { match, roundName: round.name };
        if (match.court?.name) {
          if (!matchesByCourt[match.court.name]) {
            matchesByCourt[match.court.name] = [];
          }
          matchesByCourt[match.court.name].push(item);
        } else {
          matchesNoCourt.push(item);
        }
      });
    });
    
    return { matchesByCourt, matchesNoCourt };
  }, [winnerRounds, classificationRounds]);

  const getTeamDisplayName = (team: Team | undefined | null): string => {
    if (!team || !team.players || team.players.length < 2) return 'À déterminer';
    return `${team.players[0].last_name} / ${team.players[1].last_name}`;
  };

  const renderPassages = () => {
    const { matchesByCourt, matchesNoCourt } = allMatchesByCourt;
    const courtNames = Object.keys(matchesByCourt).sort();
    
    if (courtNames.length === 0 && matchesNoCourt.length === 0) {
      return (
        <View style={styles.emptyBracket}>
          <Ionicons name="list-outline" size={48} color={Colors.textLight} />
          <Text style={styles.emptyBracketText}>Aucun match à afficher</Text>
        </View>
      );
    }

    return (
      <View style={styles.passagesContainer}>
        {courtNames.map(courtName => (
          <View key={courtName} style={styles.courtSection}>
            <View style={styles.courtHeader}>
              <Ionicons name="location" size={20} color={Colors.primary} />
              <Text style={styles.courtTitle}>{courtName}</Text>
            </View>
            {matchesByCourt[courtName].map((item, idx) => (
              <TouchableOpacity
                key={item.match.id}
                style={[
                  styles.passageCard,
                  item.match.is_finished && styles.passageCardFinished,
                  !item.match.team1 || !item.match.team2 ? styles.passageCardPending : null
                ]}
                onPress={() => openScoreModal(item.match)}
                disabled={item.match.is_finished || !item.match.team1 || !item.match.team2}
              >
                <View style={styles.passageNumber}>
                  <Text style={styles.passageNumberText}>{idx + 1}</Text>
                </View>
                <View style={styles.passageContent}>
                  <Text style={styles.passageRound}>{item.roundName}</Text>
                  <View style={styles.passageTeams}>
                    <Text style={[
                      styles.passageTeamName,
                      item.match.winner_id === item.match.team1?.id && styles.passageTeamWinner
                    ]}>
                      {getTeamDisplayName(item.match.team1)}
                    </Text>
                    <Text style={styles.passageVs}>vs</Text>
                    <Text style={[
                      styles.passageTeamName,
                      item.match.winner_id === item.match.team2?.id && styles.passageTeamWinner
                    ]}>
                      {getTeamDisplayName(item.match.team2)}
                    </Text>
                  </View>
                </View>
                <View style={styles.passageStatus}>
                  {item.match.is_finished ? (
                    <View style={styles.passageScoreContainer}>
                      <Text style={styles.passageScore}>{item.match.score}</Text>
                      <Ionicons name="checkmark-circle" size={18} color={Colors.success} />
                    </View>
                  ) : item.match.team1 && item.match.team2 ? (
                    <Text style={styles.passageWaiting}>À jouer</Text>
                  ) : (
                    <Text style={styles.passagePending}>En attente</Text>
                  )}
                </View>
              </TouchableOpacity>
            ))}
          </View>
        ))}
        
        {matchesNoCourt.length > 0 && (
          <View style={styles.courtSection}>
            <View style={styles.courtHeader}>
              <Ionicons name="help-circle" size={20} color={Colors.textSecondary} />
              <Text style={styles.courtTitle}>Sans terrain assigné</Text>
            </View>
            {matchesNoCourt.map((item, idx) => (
              <View key={item.match.id} style={[styles.passageCard, styles.passageCardNoCourt]}>
                <View style={styles.passageNumber}>
                  <Text style={styles.passageNumberText}>?</Text>
                </View>
                <View style={styles.passageContent}>
                  <Text style={styles.passageRound}>{item.roundName}</Text>
                  <View style={styles.passageTeams}>
                    <Text style={styles.passageTeamName}>{getTeamDisplayName(item.match.team1)}</Text>
                    <Text style={styles.passageVs}>vs</Text>
                    <Text style={styles.passageTeamName}>{getTeamDisplayName(item.match.team2)}</Text>
                  </View>
                </View>
                <View style={styles.passageStatus}>
                  {item.match.is_finished ? (
                    <Text style={styles.passageScore}>{item.match.score}</Text>
                  ) : (
                    <Text style={styles.passagePending}>En attente</Text>
                  )}
                </View>
              </View>
            ))}
          </View>
        )}
      </View>
    );
  };

  const renderBracket = (rounds: RoundWithMatches[], isClassification: boolean = false) => {
    if (rounds.length === 0) {
      return (
        <View style={styles.emptyBracket}>
          <Ionicons name="git-branch-outline" size={48} color={Colors.textLight} />
          <Text style={styles.emptyBracketText}>
            {isClassification ? 'Pas de matchs de classement' : 'Aucun match'}
          </Text>
        </View>
      );
    }

    return (
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        <View style={styles.bracketContainer}>
          {rounds.map((round) => (
            <View key={round.id} style={styles.roundColumn}>
              <Text style={[
                styles.roundTitle,
                isClassification && styles.roundTitleClassification
              ]}>
                {round.name}
              </Text>
              <View style={styles.matchesColumn}>
                {round.matches.map((match) => renderMatch(match))}
              </View>
            </View>
          ))}
        </View>
      </ScrollView>
    );
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={styles.loadingText}>Chargement du bracket...</Text>
      </View>
    );
  }

  if (winnerRounds.length === 0 && classificationRounds.length === 0) {
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
              <Text style={styles.headerTitle}>Bracket</Text>
              <View style={styles.headerButton} />
            </View>
          </View>
          <View style={styles.emptyContainer}>
            <Ionicons name="git-branch-outline" size={64} color={Colors.textLight} />
            <Text style={styles.emptyText}>Aucun bracket généré</Text>
            <Text style={styles.emptySubtext}>Générez d'abord le bracket depuis la page du tournoi</Text>
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
            <Text style={styles.headerTitle}>Bracket</Text>
            <View style={styles.headerButton} />
          </View>
          
          {/* Onglets */}
          <View style={styles.tabsContainer}>
            <TouchableOpacity
              style={[styles.tab, activeTab === 'winner' && styles.tabActive]}
              onPress={() => setActiveTab('winner')}
            >
              <Ionicons 
                name="trophy" 
                size={18} 
                color={activeTab === 'winner' ? Colors.primary : Colors.textInverse} 
              />
              <Text style={[styles.tabtextab, activeTab === 'winner' && styles.tabTextActive]}>
                Tableau
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.tab, activeTab === 'classification' && styles.tabActive]}
              onPress={() => setActiveTab('classification')}
            >
              <Ionicons 
                name="medal" 
                size={18} 
                color={activeTab === 'classification' ? Colors.primary : Colors.textInverse} 
              />
              <Text style={[styles.tabtextab, activeTab === 'classification' && styles.tabTextActive]}>
                Classement
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.tab, activeTab === 'passages' && styles.tabActive]}
              onPress={() => setActiveTab('passages')}
            >
              <Ionicons 
                name="list" 
                size={18} 
                color={activeTab === 'passages' ? Colors.primary : Colors.textInverse} 
              />
              <Text style={[styles.tabtextab, activeTab === 'passages' && styles.tabTextActive]}>
                Passages
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.tab, activeTab === 'results' && styles.tabActive]}
              onPress={() => setActiveTab('results')}
            >
              <Ionicons 
                name="podium" 
                size={18} 
                color={activeTab === 'results' ? Colors.primary : Colors.textInverse} 
              />
              <Text style={[styles.tabtextab, activeTab === 'results' && styles.tabTextActive]}>
                Points
              </Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Contenu */}
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
          {activeTab === 'winner' && renderBracket(winnerRounds, false)}
          {activeTab === 'classification' && renderBracket(classificationRounds, true)}
          {activeTab === 'passages' && renderPassages()}
          {activeTab === 'results' && renderFinalRankings()}

          {/* Légende - seulement pour les onglets bracket */}
          {(activeTab === 'winner' || activeTab === 'classification') && (
            <View style={styles.legend}>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: Colors.success }]} />
                <Text style={styles.legendText}>Match terminé</Text>
              </View>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: Colors.warning }]} />
                <Text style={styles.legendText}>En attente de score</Text>
              </View>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: Colors.textLight }]} />
                <Text style={styles.legendText}>En attente d'adversaire</Text>
              </View>
            </View>
          )}
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
                <Text style={styles.label}>Vainqueur</Text>
                <View style={styles.winnerSelection}>
                  <TouchableOpacity
                    style={[
                      styles.winnerOption,
                      winnerId === selectedMatch.team1_id && styles.winnerOptionActive,
                    ]}
                    onPress={() => setWinnerId(selectedMatch.team1_id || null)}
                  >
                    <Text style={[
                      styles.winnerOptionText,
                      winnerId === selectedMatch.team1_id && styles.winnerOptionTextActive,
                    ]}>
                      {getTeamDisplay(selectedMatch.team1)}
                    </Text>
                    {winnerId === selectedMatch.team1_id && (
                      <Ionicons name="checkmark-circle" size={20} color={Colors.primary} />
                    )}
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={[
                      styles.winnerOption,
                      winnerId === selectedMatch.team2_id && styles.winnerOptionActive,
                    ]}
                    onPress={() => setWinnerId(selectedMatch.team2_id || null)}
                  >
                    <Text style={[
                      styles.winnerOptionText,
                      winnerId === selectedMatch.team2_id && styles.winnerOptionTextActive,
                    ]}>
                      {getTeamDisplay(selectedMatch.team2)}
                    </Text>
                    {winnerId === selectedMatch.team2_id && (
                      <Ionicons name="checkmark-circle" size={20} color={Colors.primary} />
                    )}
                  </TouchableOpacity>
                </View>

                {/* Scores par set */}
                <Text style={styles.label}>Score</Text>
                
                {/* Set 1 */}
                <View style={styles.setRow}>
                  <Text style={styles.setLabel}>Set 1</Text>
                  <View style={styles.setInputs}>
                    <Input
                      placeholder="0"
                      value={scores.set1[0]}
                      onChangeText={(v) => setScores({ ...scores, set1: [v, scores.set1[1]] })}
                      keyboardType="numeric"
                      containerStyle={styles.scoreInput}
                    />
                    <Text style={styles.scoreSeparator}>-</Text>
                    <Input
                      placeholder="0"
                      value={scores.set1[1]}
                      onChangeText={(v) => setScores({ ...scores, set1: [scores.set1[0], v] })}
                      keyboardType="numeric"
                      containerStyle={styles.scoreInput}
                    />
                  </View>
                </View>

                {/* Set 2 */}
                <View style={styles.setRow}>
                  <Text style={styles.setLabel}>Set 2</Text>
                  <View style={styles.setInputs}>
                    <Input
                      placeholder="0"
                      value={scores.set2[0]}
                      onChangeText={(v) => setScores({ ...scores, set2: [v, scores.set2[1]] })}
                      keyboardType="numeric"
                      containerStyle={styles.scoreInput}
                    />
                    <Text style={styles.scoreSeparator}>-</Text>
                    <Input
                      placeholder="0"
                      value={scores.set2[1]}
                      onChangeText={(v) => setScores({ ...scores, set2: [scores.set2[0], v] })}
                      keyboardType="numeric"
                      containerStyle={styles.scoreInput}
                    />
                  </View>
                </View>

                {/* Set 3 (optionnel) */}
                <View style={styles.setRow}>
                  <Text style={styles.setLabel}>Set 3</Text>
                  <View style={styles.setInputs}>
                    <Input
                      placeholder="0"
                      value={scores.set3[0]}
                      onChangeText={(v) => setScores({ ...scores, set3: [v, scores.set3[1]] })}
                      keyboardType="numeric"
                      containerStyle={styles.scoreInput}
                    />
                    <Text style={styles.scoreSeparator}>-</Text>
                    <Input
                      placeholder="0"
                      value={scores.set3[1]}
                      onChangeText={(v) => setScores({ ...scores, set3: [scores.set3[0], v] })}
                      keyboardType="numeric"
                      containerStyle={styles.scoreInput}
                    />
                  </View>
                </View>

                {/* Aperçu */}
                <View style={styles.scorePreview}>
                  <Text style={styles.scorePreviewLabel}>Résultat :</Text>
                  <Text style={styles.scorePreviewValue}>
                    {formatScoreString() || '-'}
                  </Text>
                </View>
              </>
            )}

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
  tabtextab:{
    fontSize: FontSizes.xs,
    color: Colors.textInverse,
    fontWeight: '500',
  },
  tabTextActive: {
    color: Colors.primary,
  },
  scrollContent: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.background,
  },
  loadingText: {
    marginTop: Spacing.md,
    color: Colors.textSecondary,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.background,
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
    textAlign: 'center',
    marginTop: Spacing.sm,
  },
  emptyBracket: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: Spacing.xxl,
  },
  emptyBracketText: {
    fontSize: FontSizes.md,
    color: Colors.textSecondary,
    marginTop: Spacing.md,
  },
  bracketContainer: {
    flexDirection: 'row',
    padding: Spacing.md,
  },
  roundColumn: {
    marginRight: Spacing.lg,
    minWidth: 180,
  },
  roundTitle: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: Spacing.md,
    backgroundColor: Colors.primary,
    color: Colors.textInverse,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.md,
    overflow: 'hidden',
  },
  roundTitleClassification: {
    backgroundColor: Colors.accent,
  },
  matchesColumn: {
    justifyContent: 'space-around',
    flex: 1,
  },
  matchCard: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    marginBottom: Spacing.md,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  matchContent: {
    padding: Spacing.sm,
  },
  teamRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Spacing.xs,
    paddingHorizontal: Spacing.sm,
    borderRadius: BorderRadius.sm,
  },
  teamRowWinner: {
    backgroundColor: Colors.successLight,
  },
  teamName: {
    flex: 1,
    fontSize: FontSizes.sm,
    color: Colors.text,
  },
  teamNameWinner: {
    fontWeight: '600',
  },
  teamNamePending: {
    color: Colors.textLight,
    fontStyle: 'italic',
  },
  scoreContainer: {
    flexDirection: 'row',
    gap: Spacing.xs,
  },
  setScore: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    fontWeight: '500',
    backgroundColor: Colors.surfaceSecondary,
    paddingHorizontal: Spacing.xs,
    borderRadius: BorderRadius.sm,
    overflow: 'hidden',
  },
  setScoreWinner: {
    color: Colors.success,
    fontWeight: '600',
  },
  matchSeparator: {
    height: 1,
    backgroundColor: Colors.border,
    marginVertical: Spacing.xs,
  },
  matchStatus: {
    backgroundColor: Colors.warningLight,
    paddingVertical: Spacing.xs,
    alignItems: 'center',
  },
  matchStatusText: {
    fontSize: FontSizes.xs,
    color: Colors.warning,
  },
  matchPending: {
    backgroundColor: Colors.surfaceSecondary,
    paddingVertical: Spacing.xs,
    alignItems: 'center',
  },
  matchPendingText: {
    fontSize: FontSizes.xs,
    color: Colors.textLight,
  },
  courtBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: Spacing.xs,
    backgroundColor: Colors.surfaceSecondary,
    gap: Spacing.xs,
  },
  courtBadgeText: {
    fontSize: FontSizes.xs,
    color: Colors.textSecondary,
  },
  legend: {
    flexDirection: 'row',
    justifyContent: 'center',
    flexWrap: 'wrap',
    gap: Spacing.md,
    padding: Spacing.md,
    marginTop: Spacing.md,
    marginBottom: Spacing.xl,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  legendText: {
    fontSize: FontSizes.xs,
    color: Colors.textSecondary,
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
    marginBottom: Spacing.lg,
  },
  modalTitle: {
    fontSize: FontSizes.xl,
    fontWeight: 'bold',
    color: Colors.text,
  },
  label: {
    fontSize: FontSizes.sm,
    fontWeight: '600',
    color: Colors.text,
    marginBottom: Spacing.sm,
  },
  winnerSelection: {
    gap: Spacing.sm,
    marginBottom: Spacing.lg,
  },
  winnerOption: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: Spacing.md,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
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
  scorePreview: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: Spacing.md,
    backgroundColor: Colors.surfaceSecondary,
    borderRadius: BorderRadius.md,
    marginVertical: Spacing.md,
  },
  scorePreviewLabel: {
    fontSize: FontSizes.md,
    color: Colors.textSecondary,
    marginRight: Spacing.sm,
  },
  scorePreviewValue: {
    fontSize: FontSizes.lg,
    fontWeight: '600',
    color: Colors.text,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: Spacing.md,
    marginTop: Spacing.md,
  },
  modalButton: {
    flex: 1,
  },
  // Rankings styles
  rankingsContainer: {
    padding: Spacing.md,
  },
  rankingsHeader: {
    alignItems: 'center',
    marginBottom: Spacing.lg,
    padding: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
  },
  rankingsTitle: {
    fontSize: FontSizes.xl,
    fontWeight: 'bold',
    color: Colors.text,
    marginBottom: Spacing.sm,
  },
  rankingsInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
  },
  rankingsBadge: {
    backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.full,
  },
  rankingsBadgeText: {
    color: Colors.textInverse,
    fontWeight: '600',
    fontSize: FontSizes.sm,
  },
  rankingsTeams: {
    fontSize: FontSizes.md,
    color: Colors.textSecondary,
  },
  inProgressBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.warningLight,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.full,
    marginTop: Spacing.sm,
    gap: Spacing.xs,
  },
  inProgressText: {
    color: Colors.warning,
    fontWeight: '500',
    fontSize: FontSizes.sm,
  },
  rankingCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    marginBottom: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  rankingCardTop3: {
    borderColor: Colors.accent,
    borderWidth: 2,
  },
  rankingLeft: {
    marginRight: Spacing.md,
  },
  rankBadge: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rankNumber: {
    fontSize: FontSizes.md,
    fontWeight: 'bold',
    color: Colors.text,
  },
  rankingMiddle: {
    flex: 1,
  },
  rankingNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
  },
  rankingTeamName: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.text,
  },
  seededBadgeSmall: {
    backgroundColor: Colors.warningLight,
    borderRadius: 8,
    padding: 2,
  },
  rankingPlayers: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    marginTop: 2,
  },
  rankingRight: {
    alignItems: 'center',
  },
  rankingPoints: {
    fontSize: FontSizes.xl,
    fontWeight: 'bold',
    color: Colors.primary,
  },
  rankingPointsLabel: {
    fontSize: FontSizes.xs,
    color: Colors.textSecondary,
  },
  // Styles pour l'onglet Passages
  passagesContainer: {
    padding: Spacing.md,
  },
  courtSection: {
    marginBottom: Spacing.lg,
  },
  courtHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    marginBottom: Spacing.md,
    paddingBottom: Spacing.sm,
    borderBottomWidth: 2,
    borderBottomColor: Colors.primary,
  },
  courtTitle: {
    fontSize: FontSizes.lg,
    fontWeight: 'bold',
    color: Colors.text,
  },
  passageCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    padding: Spacing.sm,
    marginBottom: Spacing.sm,
    borderLeftWidth: 4,
    borderLeftColor: Colors.warning,
  },
  passageCardFinished: {
    borderLeftColor: Colors.success,
    opacity: 0.8,
  },
  passageCardPending: {
    borderLeftColor: Colors.textLight,
  },
  passageCardNoCourt: {
    borderLeftColor: Colors.error,
  },
  passageNumber: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: Colors.surfaceSecondary,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: Spacing.sm,
  },
  passageNumberText: {
    fontSize: FontSizes.sm,
    fontWeight: 'bold',
    color: Colors.textSecondary,
  },
  passageContent: {
    flex: 1,
  },
  passageRound: {
    fontSize: FontSizes.xs,
    color: Colors.textSecondary,
    marginBottom: 2,
  },
  passageTeams: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  passageTeamName: {
    fontSize: FontSizes.sm,
    color: Colors.text,
  },
  passageTeamWinner: {
    fontWeight: 'bold',
    color: Colors.primary,
  },
  passageVs: {
    fontSize: FontSizes.xs,
    color: Colors.textLight,
    marginHorizontal: Spacing.xs,
  },
  passageStatus: {
    alignItems: 'flex-end',
    minWidth: 60,
  },
  passageScoreContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
  },
  passageScore: {
    fontSize: FontSizes.sm,
    fontWeight: 'bold',
    color: Colors.primary,
  },
  passageWaiting: {
    fontSize: FontSizes.xs,
    color: Colors.warning,
    fontWeight: '500',
  },
  passagePending: {
    fontSize: FontSizes.xs,
    color: Colors.textLight,
  },
});