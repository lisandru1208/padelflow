// services/api.ts
// Configuration de l'API et fonctions d'appel

const API_BASE_URL = 'http://ec2-3-250-200-34.eu-west-1.compute.amazonaws.com:8000';

// Type pour les erreurs API
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

// Fonction générique pour les appels API (sera utilisée plus tard)
export async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      errorData.detail || `Erreur ${response.status}`,
      response.status
    );
  }

  const text = await response.text();
  return text ? JSON.parse(text) : ({} as T);
}

// ==================== AUTH ====================

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch(
    `${API_BASE_URL}/auth/login?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(errorData.detail || 'Échec de la connexion', response.status);
  }

  return response.json();
}

export async function register(email: string, password: string): Promise<any> {
  const response = await fetch(
    `${API_BASE_URL}/auth/register?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(errorData.detail || "Échec de l'inscription", response.status);
  }

  return response.json();
}

// ==================== CLUBS ====================

export interface Club {
  id: string;
  name: string;
  city?: string;
  owner_id: string;
}

export async function getClubs(token: string): Promise<Club[]> {
  return apiCall<Club[]>('/clubs/', { method: 'GET' }, token);
}

export async function createClub(token: string, name: string, city?: string): Promise<Club> {
  let url = `/clubs/?name=${encodeURIComponent(name)}`;
  if (city) {
    url += `&city=${encodeURIComponent(city)}`;
  }
  return apiCall<Club>(url, { method: 'POST' }, token);
}

export async function updateClub(token: string, clubId: string, name?: string, city?: string): Promise<Club> {
  let url = `/clubs/${clubId}?`;
  if (name) url += `name=${encodeURIComponent(name)}&`;
  if (city !== undefined) url += `city=${encodeURIComponent(city || '')}&`;
  return apiCall<Club>(url, { method: 'PUT' }, token);
}

export async function deleteClub(token: string, clubId: string): Promise<void> {
  return apiCall<void>(`/clubs/${clubId}`, { method: 'DELETE' }, token);
}

// ==================== COURTS ====================

export interface Court {
  id: string;
  name: string;
  indoor: boolean;
  club_id: string;
}

export async function getCourts(token: string, clubId: string): Promise<Court[]> {
  return apiCall<Court[]>(`/clubs/${clubId}/courts/`, { method: 'GET' }, token);
}

export async function createCourt(
  token: string,
  clubId: string,
  name: string,
  indoor: boolean = false
): Promise<Court> {
  const url = `/clubs/${clubId}/courts/?name=${encodeURIComponent(name)}&indoor=${indoor}`;
  return apiCall<Court>(url, { method: 'POST' }, token);
}

export async function deleteCourt(token: string, clubId: string, courtId: string): Promise<void> {
  return apiCall<void>(`/clubs/${clubId}/courts/${courtId}`, { method: 'DELETE' }, token);
}

// ==================== TOURNAMENTS ====================

export interface Tournament {
  id: string;
  name: string;
  category: string;
  gender: string;
  start_date: string;
  end_date?: string;
  indoor: boolean;
  club_id: string;
  status?: string;
}

export async function getTournaments(token: string, clubId: string): Promise<Tournament[]> {
  return apiCall<Tournament[]>(`/clubs/${clubId}/tournaments/`, { method: 'GET' }, token);
}

export async function createTournament(
  token: string,
  clubId: string,
  data: {
    name: string;
    category: string;
    gender: string;
    start_date: string;
    end_date?: string;
    indoor?: boolean;
  }
): Promise<Tournament> {
  let url = `/clubs/${clubId}/tournaments/?name=${encodeURIComponent(data.name)}&category=${encodeURIComponent(data.category)}&gender=${encodeURIComponent(data.gender)}&start_date=${data.start_date}`;
  if (data.end_date) {
    url += `&end_date=${data.end_date}`;
  }
  if (data.indoor !== undefined) {
    url += `&indoor=${data.indoor}`;
  }
  return apiCall<Tournament>(url, { method: 'POST' }, token);
}

export async function deleteTournament(token: string, clubId: string, tournamentId: string): Promise<void> {
  return apiCall<void>(`/clubs/${clubId}/tournaments/${tournamentId}`, { method: 'DELETE' }, token);
}

// ==================== TEAMS ====================

export interface Player {
  id?: string;
  first_name: string;
  last_name: string;
  license_number: string;
  ranking: number;
}

export interface Team {
  id: string;
  tournament_id: string;
  combined_ranking?: number;
  is_seeded: boolean;
  seed_position?: number;
  players: Player[];
}

export interface TeamCreate {
  players: Omit<Player, 'id'>[];
}

export interface BracketInfo {
  num_teams: number;
  bracket_size: number;
  num_byes: number;
  bye_percentage: number;
  num_seeds: number;
  recommendation: 'bracket' | 'poule' | 'minimum';
  message: string;
  recommended_courts: number;
  first_round_matches: number;
}

export async function getTeams(token: string, tournamentId: string): Promise<Team[]> {
  return apiCall<Team[]>(`/tournaments/${tournamentId}/teams/`, { method: 'GET' }, token);
}

export async function getBracketInfo(token: string, tournamentId: string): Promise<BracketInfo> {
  return apiCall<BracketInfo>(`/tournaments/${tournamentId}/teams/bracket-info`, { method: 'GET' }, token);
}

export async function createTeam(
  token: string,
  tournamentId: string,
  team: TeamCreate
): Promise<Team> {
  return apiCall<Team>(
    `/tournaments/${tournamentId}/teams/`,
    {
      method: 'POST',
      body: JSON.stringify(team),
    },
    token
  );
}

export async function deleteTeam(
  token: string,
  tournamentId: string,
  teamId: string
): Promise<void> {
  return apiCall<void>(
    `/tournaments/${tournamentId}/teams/${teamId}`,
    { method: 'DELETE' },
    token
  );
}

// ==================== BRACKET ====================

export interface Round {
  id: string;
  round_number: number;
  tournament_id: string;
}

export interface Match {
  id: string;
  round_id: string;
  position: number;
  team1_id?: string;
  team2_id?: string;
  team1?: Team;
  team2?: Team;
  winner_team_id?: string;
  score?: string;
  court_id?: string;
  court?: Court;
  status?: string;
}

export interface BracketResponse {
  rounds: Round[];
  matches: Match[];
}

export async function generateBracket(
  token: string,
  tournamentId: string,
  courtIds?: string[]
): Promise<BracketResponse> {
  return apiCall<BracketResponse>(
    `/tournaments/${tournamentId}/generate-bracket`,
    { 
      method: 'POST',
      body: JSON.stringify({ court_ids: courtIds || [] })
    },
    token
  );
}

export async function deleteBracket(
  token: string,
  tournamentId: string
): Promise<void> {
  return apiCall<void>(
    `/tournaments/${tournamentId}/bracket`,
    { method: 'DELETE' },
    token
  );
}

export interface TournamentInfo {
  id: string;
  name: string;
  category: string;
  gender: string;
  start_date: string;
  end_date?: string;
  indoor: boolean;
  is_finished: boolean;
  bracket_generated: boolean;
  selected_court_ids: string[];
}

export async function getTournamentInfo(
  token: string,
  tournamentId: string
): Promise<TournamentInfo> {
  return apiCall<TournamentInfo>(
    `/tournaments/${tournamentId}/info`,
    { method: 'GET' },
    token
  );
}

export interface RoundWithMatches {
  id: string;
  tournament_id: string;
  name: string;
  order: number;
  matches: Match[];
}

export async function getRounds(token: string, tournamentId: string): Promise<RoundWithMatches[]> {
  return apiCall<RoundWithMatches[]>(
    `/tournaments/${tournamentId}/rounds`,
    { method: 'GET' },
    token
  );
}

export async function getClassificationRounds(token: string, tournamentId: string): Promise<RoundWithMatches[]> {
  return apiCall<RoundWithMatches[]>(
    `/tournaments/${tournamentId}/classification-rounds`,
    { method: 'GET' },
    token
  );
}

export interface TeamRanking {
  rank: number;
  points: number;
  team_id: string;
  combined_ranking: number;
  is_seeded: boolean;
  seed_position?: number;
  players: Player[];
}

export interface FinalRankings {
  tournament_id: string;
  tournament_name: string;
  category: string;
  num_teams: number;
  tournament_finished: boolean;
  rankings: TeamRanking[];
}

export async function getFinalRankings(token: string, tournamentId: string): Promise<FinalRankings> {
  return apiCall<FinalRankings>(
    `/tournaments/${tournamentId}/final-rankings`,
    { method: 'GET' },
    token
  );
}

export async function finishTournament(token: string, tournamentId: string): Promise<void> {
  return apiCall<void>(
    `/tournaments/${tournamentId}/finish`,
    { method: 'POST' },
    token
  );
}

export async function getMatches(token: string, roundId: string): Promise<Match[]> {
  return apiCall<Match[]>(`/rounds/${roundId}/matches/`, { method: 'GET' }, token);
}

export async function assignCourt(
  token: string,
  roundId: string,
  matchId: string,
  courtId: string
): Promise<Match> {
  return apiCall<Match>(
    `/rounds/${roundId}/matches/${matchId}/court?court_id=${courtId}`,
    { method: 'PUT' },
    token
  );
}

// ==================== SCORES ====================

export interface ScoreInput {
  score: string;
  winner_team_id: string;
}

export async function submitScore(
  token: string,
  matchId: string,
  scoreData: ScoreInput
): Promise<Match> {
  return apiCall<Match>(
    `/matches/${matchId}/score`,
    {
      method: 'POST',
      body: JSON.stringify(scoreData),
    },
    token
  );
}

export { API_BASE_URL };