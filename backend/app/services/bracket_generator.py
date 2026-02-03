import math
import random
import time
from app.models.round import Round
from app.models.match import Match
from app.models.team import Team


def compute_bracket_size(num_teams: int) -> int:
    """Calcule la taille du bracket (puissance de 2 supérieure ou égale)"""
    if num_teams < 2:
        return 2
    return 2 ** math.ceil(math.log2(num_teams))


def get_round_name(round_number: int, total_rounds: int) -> str:
    """Retourne le nom du round"""
    remaining = total_rounds - round_number
    
    if remaining == 0:
        return "Finale"
    elif remaining == 1:
        return "Demi-finales"
    elif remaining == 2:
        return "Quarts de finale"
    elif remaining == 3:
        return "Huitièmes de finale"
    elif remaining == 4:
        return "16èmes de finale"
    else:
        return f"Tour {round_number}"


def generate_bracket(db, tournament_id: str, court_ids: list = None):
    """
    Génère un bracket avec gestion correcte des BYE.
    
    Approche simplifiée:
    1. Créer tous les rounds et matchs vides d'abord
    2. Placer les équipes dans le premier round avec les BYE
    3. Propager les BYE round par round
    """
    # Initialiser le générateur aléatoire avec timestamp
    random.seed(time.time() * 1000)
    
    teams = db.query(Team).filter(
        Team.tournament_id == tournament_id
    ).all()

    if len(teams) < 2:
        raise ValueError("Minimum 2 teams required")

    num_teams = len(teams)
    bracket_size = compute_bracket_size(num_teams)
    round_count = int(math.log2(bracket_size))
    num_byes = bracket_size - num_teams
    
    # Stocker les court_ids pour les matchs de classement
    stored_court_ids = court_ids or []

    print(f"=== GÉNÉRATION BRACKET ===")
    print(f"Équipes: {num_teams}, Bracket: {bracket_size}, Rounds: {round_count}, BYE: {num_byes}")

    # ============================================
    # NETTOYER L'ANCIEN BRACKET
    # ============================================
    
    existing_rounds = db.query(Round).filter(
        Round.tournament_id == tournament_id
    ).all()
    
    for r in existing_rounds:
        db.query(Match).filter(Match.round_id == r.id).delete()
    
    db.query(Round).filter(Round.tournament_id == tournament_id).delete()
    db.commit()

    # ============================================
    # CRÉER LES ROUNDS
    # ============================================
    
    rounds = []
    for i in range(round_count):
        round_name = get_round_name(i + 1, round_count)
        r = Round(
            tournament_id=tournament_id,
            name=round_name,
            order=i + 1
        )
        db.add(r)
        db.commit()
        db.refresh(r)
        rounds.append(r)
        print(f"Round créé: {round_name} (order={i+1})")

    # ============================================
    # CRÉER TOUS LES MATCHS VIDES AVEC TERRAINS
    # ============================================
    
    all_matches = {}  # {(round_idx, match_order): match}
    court_idx = 0  # Index pour rotation des terrains
    
    for round_idx, round_obj in enumerate(rounds):
        matches_in_round = bracket_size // (2 ** (round_idx + 1))
        for match_num in range(1, matches_in_round + 1):
            # Assigner un terrain en rotation
            court_id = None
            if stored_court_ids and len(stored_court_ids) > 0:
                court_id = stored_court_ids[court_idx % len(stored_court_ids)]
                court_idx += 1
            
            match = Match(
                round_id=round_obj.id,
                match_order=match_num,
                team1_id=None,
                team2_id=None,
                bracket_type='winner',
                is_finished=False,
                court_id=court_id
            )
            db.add(match)
            db.commit()
            db.refresh(match)
            all_matches[(round_idx, match_num)] = match
        print(f"  Round {round_idx}: {matches_in_round} matchs créés avec terrains")

    # ============================================
    # PRÉPARER LES ÉQUIPES
    # ============================================
    
    # Séparer têtes de série et autres
    seeded_teams = sorted(
        [t for t in teams if t.is_seeded],
        key=lambda t: t.seed_position or 999
    )
    unseeded_teams = [t for t in teams if not t.is_seeded]
    
    # Mélanger les non-têtes de série
    random.shuffle(unseeded_teams)
    
    print(f"Têtes de série: {len(seeded_teams)}")
    print(f"Non-têtes de série: {len(unseeded_teams)}")

    # ============================================
    # PLACER LES ÉQUIPES DANS LE PREMIER ROUND
    # ============================================
    
    # Créer la liste des slots (positions dans le bracket)
    # None = BYE
    slots = place_teams_in_bracket(seeded_teams, unseeded_teams, bracket_size, num_byes)
    
    print(f"Slots: {['BYE' if s is None else 'Team' for s in slots]}")

    # Remplir les matchs du premier round
    first_round_matches = bracket_size // 2
    bye_match_ids = []  # Pour supprimer les matchs BYE après propagation
    
    for match_num in range(1, first_round_matches + 1):
        match = all_matches[(0, match_num)]
        
        # Position dans les slots (0-indexed)
        slot_idx1 = (match_num - 1) * 2
        slot_idx2 = slot_idx1 + 1
        
        team1 = slots[slot_idx1]
        team2 = slots[slot_idx2]
        
        match.team1_id = team1.id if team1 else None
        match.team2_id = team2.id if team2 else None
        
        # Si BYE, résoudre automatiquement (pas de terrain, sera supprimé après)
        if team1 and not team2:
            match.is_finished = True
            match.winner_id = team1.id
            match.score = "BYE"
            match.court_id = None  # Pas de terrain pour un BYE
            bye_match_ids.append(match.id)
            print(f"  Match {match_num}: Team vs BYE -> winner=Team (pas de match réel)")
        elif team2 and not team1:
            match.is_finished = True
            match.winner_id = team2.id
            match.score = "BYE"
            match.court_id = None  # Pas de terrain pour un BYE
            bye_match_ids.append(match.id)
            print(f"  Match {match_num}: BYE vs Team -> winner=Team (pas de match réel)")
        elif team1 and team2:
            print(f"  Match {match_num}: Team vs Team (vrai match)")
        else:
            # Deux BYE - ne devrait pas arriver avec une bonne répartition
            bye_match_ids.append(match.id)
            print(f"  Match {match_num}: BYE vs BYE (ERREUR!)")
    
    db.commit()

    # ============================================
    # PROPAGER LES BYE AUX ROUNDS SUIVANTS
    # ============================================
    
    for round_idx in range(round_count - 1):
        current_round = rounds[round_idx]
        next_round = rounds[round_idx + 1]
        
        matches_in_current = bracket_size // (2 ** (round_idx + 1))
        matches_in_next = bracket_size // (2 ** (round_idx + 2))
        
        print(f"\nPropagation Round {round_idx} -> {round_idx + 1}")
        
        for current_match_num in range(1, matches_in_current + 1):
            current_match = all_matches[(round_idx, current_match_num)]
            
            if current_match.is_finished and current_match.winner_id:
                # Calculer le match suivant
                next_match_num = (current_match_num + 1) // 2
                next_match = all_matches.get((round_idx + 1, next_match_num))
                
                if next_match:
                    # Match impair -> team1, pair -> team2
                    if current_match_num % 2 == 1:
                        next_match.team1_id = current_match.winner_id
                        print(f"  Match {current_match_num} -> Next Match {next_match_num} team1")
                    else:
                        next_match.team2_id = current_match.winner_id
                        print(f"  Match {current_match_num} -> Next Match {next_match_num} team2")
        
        db.commit()
        
        # Vérifier les nouveaux BYE (match avec une seule équipe)
        for next_match_num in range(1, matches_in_next + 1):
            next_match = all_matches[(round_idx + 1, next_match_num)]
            
            # Si une seule équipe et l'autre source était un BYE
            if next_match.team1_id and not next_match.team2_id:
                # Vérifier si le match source (pair) était terminé
                source_match_num = next_match_num * 2
                source_match = all_matches.get((round_idx, source_match_num))
                if source_match and source_match.is_finished:
                    next_match.is_finished = True
                    next_match.winner_id = next_match.team1_id
                    next_match.score = "BYE"
                    next_match.court_id = None  # Pas de terrain pour un BYE
                    bye_match_ids.append(next_match.id)
                    print(f"  Next Match {next_match_num}: team1 only -> BYE propagé")
            
            elif next_match.team2_id and not next_match.team1_id:
                # Vérifier si le match source (impair) était terminé
                source_match_num = (next_match_num * 2) - 1
                source_match = all_matches.get((round_idx, source_match_num))
                if source_match and source_match.is_finished:
                    next_match.is_finished = True
                    next_match.winner_id = next_match.team2_id
                    next_match.score = "BYE"
                    next_match.court_id = None  # Pas de terrain pour un BYE
                    bye_match_ids.append(next_match.id)
                    print(f"  Next Match {next_match_num}: team2 only -> BYE propagé")
        
        db.commit()

    # ============================================
    # SUPPRIMER LES MATCHS BYE (pas de match réel)
    # ============================================
    
    if bye_match_ids:
        print(f"\nSuppression de {len(bye_match_ids)} matchs BYE...")
        db.query(Match).filter(Match.id.in_(bye_match_ids)).delete(synchronize_session=False)
        db.commit()

    # ============================================
    # MATCHS DE CLASSEMENT - VERSION CORRIGÉE
    # ============================================
    
    create_classification_matches(db, tournament_id, round_count, bracket_size, num_teams, stored_court_ids)

    return {
        "success": True,
        "teams": num_teams,
        "bracket_size": bracket_size,
        "rounds": round_count,
        "byes": num_byes,
        "seeded_teams": len(seeded_teams),
        "message": f"Bracket généré avec {num_teams} équipes et {num_byes} BYE"
    }


def place_teams_in_bracket(seeded_teams, unseeded_teams, bracket_size, num_byes):
    """
    Place les équipes dans le bracket avec les BYE aux bonnes positions.
    Les têtes de série reçoivent les BYE en priorité.
    
    Returns: Liste de slots [Team, Team, None (BYE), Team, ...]
    """
    slots = [None] * bracket_size
    
    # Positions pour les têtes de série (séparées pour ne pas se rencontrer tôt)
    seed_positions = get_seed_slot_positions(bracket_size)
    
    # Placer les têtes de série
    for i, team in enumerate(seeded_teams):
        seed_num = i + 1
        if seed_num in seed_positions:
            pos = seed_positions[seed_num]
            slots[pos] = team
    
    # Déterminer les positions des BYE (face aux meilleures têtes de série)
    bye_positions = []
    for i in range(min(num_byes, len(seed_positions))):
        seed_num = i + 1
        if seed_num in seed_positions:
            seed_pos = seed_positions[seed_num]
            # L'adversaire est dans le même match (position paire/impaire)
            if seed_pos % 2 == 0:
                opponent_pos = seed_pos + 1
            else:
                opponent_pos = seed_pos - 1
            bye_positions.append(opponent_pos)
    
    # S'il reste des BYE à placer (plus que de têtes de série)
    remaining_byes = num_byes - len(bye_positions)
    if remaining_byes > 0:
        # Ajouter des BYE aux positions non-TDS restantes
        for i in range(bracket_size):
            if remaining_byes <= 0:
                break
            if slots[i] is None and i not in bye_positions:
                # Vérifier que ce n'est pas face à un BYE existant
                opponent = i + 1 if i % 2 == 0 else i - 1
                if opponent not in bye_positions:
                    bye_positions.append(i)
                    remaining_byes -= 1
    
    # Placer les équipes non-têtes de série dans les positions restantes
    unseeded_idx = 0
    for i in range(bracket_size):
        if slots[i] is None and i not in bye_positions:
            if unseeded_idx < len(unseeded_teams):
                slots[i] = unseeded_teams[unseeded_idx]
                unseeded_idx += 1
    
    # Les positions bye_positions restent None (= BYE)
    
    return slots


def get_seed_slot_positions(bracket_size):
    """
    Retourne les positions des têtes de série dans le bracket.
    Format: {seed_number: slot_position}
    
    Positions calculées pour que TDS1 et TDS2 ne se rencontrent qu'en finale,
    TDS3 et TDS4 ne rencontrent TDS1/TDS2 qu'en demi, etc.
    """
    if bracket_size == 4:
        # Demi 1: slot 0 vs 1, Demi 2: slot 2 vs 3
        # TDS1 (slot 0) vs TDS4 (slot 1), TDS3 (slot 2) vs TDS2 (slot 3)
        return {1: 0, 2: 3, 3: 2, 4: 1}
    
    elif bracket_size == 8:
        # TDS1 en haut, TDS2 en bas, TDS3/4 au milieu opposés
        return {1: 0, 2: 7, 3: 4, 4: 3, 5: 2, 6: 5, 7: 6, 8: 1}
    
    elif bracket_size == 16:
        return {
            1: 0,   # Haut du bracket
            2: 15,  # Bas du bracket
            3: 8,   # Milieu bas
            4: 7,   # Milieu haut
            5: 4,
            6: 11,
            7: 12,
            8: 3,
            9: 2,
            10: 13,
            11: 10,
            12: 5,
            13: 6,
            14: 9,
            15: 14,
            16: 1
        }
    
    elif bracket_size == 32:
        return {
            1: 0, 2: 31, 3: 16, 4: 15,
            5: 8, 6: 23, 7: 24, 8: 7,
            9: 4, 10: 27, 11: 20, 12: 11,
            13: 12, 14: 19, 15: 28, 16: 3,
            17: 2, 18: 29, 19: 18, 20: 13,
            21: 14, 22: 17, 23: 30, 24: 1,
            25: 6, 26: 25, 27: 22, 28: 9,
            29: 10, 30: 21, 31: 26, 32: 5
        }
    
    else:
        # Fallback simple
        return {1: 0, 2: bracket_size - 1}


def create_classification_matches(db, tournament_id: str, round_count: int, bracket_size: int, num_teams: int, court_ids: list = None):
    """
    Crée les matchs de classement (3ème place, 5ème place, etc.) de manière dynamique.
    
    Organisation dynamique basée sur le nombre réel d'équipes :
    - À chaque round, on a des perdants qui doivent être classés
    - On crée des matchs de classement pour tous ces perdants
    
    Exemple avec 20 équipes (bracket_size=32, 12 BYE) :
    - Round 1 (16èmes) : 10 perdants réels (20 équipes jouent, pas de BYE perdants)
    - Round 2 (8èmes) : 8 perdants
    - Round 3 (quarts) : 4 perdants
    - Round 4 (demis) : 2 perdants
    - Finale : 1 perdant (2ème place)
    """
    court_idx = 0
    base_order = 100  # Commence à 100 pour les matchs de classement
    
    def get_next_court():
        nonlocal court_idx
        if court_ids and len(court_ids) > 0:
            court_id = court_ids[court_idx % len(court_ids)]
            court_idx += 1
            return court_id
        return None
    
    def get_classification_name(rank: int) -> str:
        """Retourne le nom du round de classement"""
        if rank == 3:
            return "Match 3ème place"
        elif rank == 5:
            return "Match 5ème place"
        elif rank == 7:
            return "Match 7ème place"
        elif rank == 9:
            return "Match 9ème place"
        elif rank == 11:
            return "Match 11ème place"
        elif rank == 13:
            return "Match 13ème place"
        elif rank == 15:
            return "Match 15ème place"
        else:
            return f"Match {rank}ème place"
    
    print(f"\n=== GÉNÉRATION MATCHS DE CLASSEMENT ===")
    print(f"Nombre d'équipes réelles: {num_teams}")
    print(f"Bracket size: {bracket_size}")
    print(f"Rounds: {round_count}")
    
    # Calculer le nombre de perdants à chaque round
    # Round 1 : tous les matchs réels (pas les BYE) produisent des perdants
    # Rounds suivants : la moitié des équipes restantes perdent
    
    # Calculer combien d'équipes réelles participent à chaque round
    teams_per_round = []
    current_teams = num_teams
    
    for round_idx in range(round_count):
        # Au premier round, on a toutes les équipes
        if round_idx == 0:
            teams_per_round.append(num_teams)
        else:
            # Aux rounds suivants, on a les gagnants du round précédent
            current_teams = current_teams // 2
            teams_per_round.append(current_teams)
    
    print(f"Équipes par round: {teams_per_round}")
    
    # Créer les matchs de classement pour chaque niveau
    # On commence par les demi-finales (round_count - 2) pour la 3ème place
    
    current_order = base_order
    
    # Match 3ème place (perdants des demi-finales)
    if round_count >= 2 and teams_per_round[round_count - 2] >= 4:
        print(f"\nCréation match 3ème place (perdants demi-finales)")
        r_3rd = Round(
            tournament_id=tournament_id,
            name="Match 3ème place",
            order=current_order
        )
        db.add(r_3rd)
        db.commit()
        db.refresh(r_3rd)
        current_order += 1
        
        match_3rd = Match(
            round_id=r_3rd.id,
            match_order=1,
            team1_id=None,
            team2_id=None,
            bracket_type='loser',
            classification_rank=3,
            court_id=get_next_court()
        )
        db.add(match_3rd)
        db.commit()
    
    # Pour chaque round (sauf les 2 derniers qui sont gérés séparément)
    # Créer les matchs de classement pour les perdants
    for round_idx in range(round_count - 2, 0, -1):
        # Calculer le rang de départ pour ce niveau
        # Round 2 (quarts) -> 5ème-8ème place
        # Round 1 (8èmes) -> 9ème-16ème place
        # etc.
        
        teams_at_this_round = teams_per_round[round_idx]
        losers_count = teams_at_this_round // 2  # Nombre de perdants
        
        # Ignorer si moins de 2 perdants
        if losers_count < 2:
            continue
        
        # Le rang de départ est basé sur le nombre d'équipes qui ont déjà été classées
        # Équipes classées = finaliste (1) + 3ème place (1) + rangs précédents
        rank_start = 2 ** (round_count - round_idx) + 1
        
        print(f"\nRound {round_idx} : {losers_count} perdants, rang {rank_start}-{rank_start + losers_count - 1}")
        
        # Si plus de 2 perdants, créer des demi-finales
        if losers_count > 2:
            # Demi-finales pour ce niveau
            r_semi = Round(
                tournament_id=tournament_id,
                name=f"Demi-finales {rank_start}-{rank_start + losers_count - 1}ème",
                order=current_order
            )
            db.add(r_semi)
            db.commit()
            db.refresh(r_semi)
            current_order += 1
            
            # Créer losers_count // 2 matchs de demi-finale
            num_semis = losers_count // 2
            for i in range(num_semis):
                match = Match(
                    round_id=r_semi.id,
                    match_order=i + 1,
                    team1_id=None,
                    team2_id=None,
                    bracket_type='loser',
                    classification_rank=rank_start,
                    court_id=get_next_court()
                )
                db.add(match)
            db.commit()
        
        # Match pour la meilleure place de ce niveau
        r_final = Round(
            tournament_id=tournament_id,
            name=get_classification_name(rank_start),
            order=current_order
        )
        db.add(r_final)
        db.commit()
        db.refresh(r_final)
        current_order += 1
        
        match_final = Match(
            round_id=r_final.id,
            match_order=1,
            team1_id=None,
            team2_id=None,
            bracket_type='loser',
            classification_rank=rank_start,
            court_id=get_next_court()
        )
        db.add(match_final)
        db.commit()
        
        # Si il y avait des demi-finales, créer aussi le match pour la place suivante
        if losers_count > 2:
            r_next = Round(
                tournament_id=tournament_id,
                name=get_classification_name(rank_start + 2),
                order=current_order
            )
            db.add(r_next)
            db.commit()
            db.refresh(r_next)
            current_order += 1
            
            match_next = Match(
                round_id=r_next.id,
                match_order=1,
                team1_id=None,
                team2_id=None,
                bracket_type='loser',
                classification_rank=rank_start + 2,
                court_id=get_next_court()
            )
            db.add(match_next)
            db.commit()
    
    db.commit()
    print(f"\n=== MATCHS DE CLASSEMENT CRÉÉS ===")