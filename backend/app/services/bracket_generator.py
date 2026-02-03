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
    # MATCHS DE CLASSEMENT
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


def create_classification_matches(db, tournament_id: str, round_count: int, bracket_size: int, total_teams: int, court_ids: list = None):
    """
    Génère tous les matchs de classement pour déterminer un classement complet.
    """
    court_idx = 0
    
    def get_next_court():
        nonlocal court_idx
        if court_ids and len(court_ids) > 0:
            court_id = court_ids[court_idx % len(court_ids)]
            court_idx += 1
            return court_id
        return None

    # Pour chaque tour principal (sauf la finale), les perdants basculent dans un tableau de classement
    for main_round_idx in range(round_count - 1):
        num_losers = bracket_size // (2 ** (main_round_idx + 1))
        best_rank = (bracket_size // (2 ** main_round_idx)) // 2 + 1
        
        # Si le meilleur rang possible est déjà au-delà du nombre d'équipes, on ignore
        if best_rank > total_teams:
            continue

        print(f"Génération tableau classement pour perdants Round {main_round_idx}")
        print(f"Num losers: {num_losers}, Vise rang: {best_rank}")
        
        create_sub_bracket(
            db, 
            tournament_id, 
            num_teams=num_losers, 
            start_rank=best_rank, 
            base_round_order=100 * (main_round_idx + 1),
            get_court_func=get_next_court,
            total_teams=total_teams
        )
    
    db.commit()



def create_sub_bracket(db, tournament_id, num_teams, start_rank, base_round_order, get_court_func, total_teams):
    """
    Fonction récursive pour créer un arbre de classement.
    """
    if num_teams < 2:
        return

    # Si le rang de départ est au-delà du nombre d'équipes, on arrête
    if start_rank > total_teams:
        return

    # Si on a 2 équipes, c'est un match sec pour une position précise
    if num_teams == 2:
        round_name = f"Match {start_rank}ème place"
        
        r = Round(
            tournament_id=tournament_id,
            name=round_name,
            order=base_round_order
        )
        db.add(r)
        db.commit()
        db.refresh(r)
        
        m = Match(
            round_id=r.id,
            match_order=1,
            team1_id=None,
            team2_id=None,
            bracket_type='loser_final', # Marqueur final
            classification_rank=start_rank,
            court_id=get_court_func()
        )
        db.add(m)
        print(f"    - Créé: {round_name} (Rank {start_rank})")
        return

    # Sinon, on crée un tour intermédiaire
    end_rank = start_rank + num_teams - 1
    
    # Clamp le nom du round au nombre total d'équipes
    display_end_rank = min(end_rank, total_teams)
    
    round_name = f"Barrages {start_rank}-{display_end_rank}"
    
    if num_teams == 4:
        round_name = f"Demi-finales {start_rank}-{display_end_rank}"
    elif num_teams == 8:
        round_name = f"Quarts {start_rank}-{display_end_rank}"
        
    r = Round(
        tournament_id=tournament_id,
        name=round_name,
        order=base_round_order
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    
    num_matches = num_teams // 2
    for i in range(num_matches):
        m = Match(
            round_id=r.id,
            match_order=i + 1,
            team1_id=None,
            team2_id=None,
            bracket_type='loser_node', # Noeud intermédiaire
            classification_rank=start_rank, 
            court_id=get_court_func()
        )
        db.add(m)
    
    print(f"    - Créé: {round_name} ({num_matches} matchs)")

    # Récursion
    mid_rank = start_rank + (num_teams // 2) - 1
    
    # Branche Vainqueurs (Upper) -> Order + 10
    create_sub_bracket(
        db,
        tournament_id,
        num_teams=num_teams // 2,
        start_rank=start_rank,
        base_round_order=base_round_order + 10,
        get_court_func=get_court_func,
        total_teams=total_teams
    )
    
    # Branche Perdants (Lower) -> Order + 20
    create_sub_bracket(
        db,
        tournament_id,
        num_teams=num_teams // 2,
        start_rank=mid_rank + 1,
        base_round_order=base_round_order + 20,
        get_court_func=get_court_func,
        total_teams=total_teams
    )
