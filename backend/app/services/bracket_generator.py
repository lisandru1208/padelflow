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


def generate_bracket(db, tournament_id: str):
    """
    Génère un bracket avec gestion correcte des BYE.
    
    Logique:
    1. Les têtes de série sont placées aux positions stratégiques
    2. Les BYE sont donnés aux meilleures têtes de série
    3. Les équipes non-têtes de série sont mélangées et placées dans les slots restants
    4. Les matchs avec BYE sont automatiquement résolus
    """
    # Initialiser le générateur aléatoire
    random.seed(time.time())
    
    teams = db.query(Team).filter(
        Team.tournament_id == tournament_id
    ).all()

    if len(teams) < 2:
        raise ValueError("Minimum 2 teams required")

    num_teams = len(teams)
    bracket_size = compute_bracket_size(num_teams)
    round_count = int(math.log2(bracket_size))
    num_byes = bracket_size - num_teams

    # Supprimer ancien bracket
    existing_rounds = db.query(Round).filter(
        Round.tournament_id == tournament_id
    ).all()
    
    for r in existing_rounds:
        db.query(Match).filter(Match.round_id == r.id).delete()
    
    db.query(Round).filter(
        Round.tournament_id == tournament_id
    ).delete()

    db.commit()

    # ============================================
    # PLACEMENT DES ÉQUIPES
    # ============================================
    
    # Séparer têtes de série et autres
    seeded_teams = sorted(
        [t for t in teams if t.is_seeded],
        key=lambda t: t.seed_position or 999
    )
    unseeded_teams = [t for t in teams if not t.is_seeded]
    
    # Mélanger les équipes non-têtes de série
    random.shuffle(unseeded_teams)
    
    # Créer les slots du bracket (None = BYE)
    slots = [None] * bracket_size
    
    # Positions optimales pour les têtes de série (pour qu'elles ne se rencontrent qu'en finale/demi)
    seed_positions = get_seed_positions(bracket_size)
    
    # Placer les têtes de série
    for team in seeded_teams:
        pos = seed_positions.get(team.seed_position)
        if pos is not None and pos < bracket_size:
            slots[pos] = team
    
    # Remplir les autres positions avec les équipes non-têtes de série
    unseeded_idx = 0
    for i in range(bracket_size):
        if slots[i] is None and unseeded_idx < len(unseeded_teams):
            slots[i] = unseeded_teams[unseeded_idx]
            unseeded_idx += 1
    
    # À ce stade, les slots restants (None) sont des BYE
    # On veut que les BYE soient face aux têtes de série
    # Réorganiser pour que les BYE soient aux bonnes positions
    slots = optimize_bye_positions(slots, seeded_teams, seed_positions, bracket_size)

    # ============================================
    # CRÉER LES ROUNDS DU WINNER BRACKET
    # ============================================
    
    winner_rounds = []
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
        winner_rounds.append(r)

    # Créer les matchs du premier round
    first_round = winner_rounds[0]
    first_round_matches = []
    
    for i in range(0, bracket_size, 2):
        team1 = slots[i]
        team2 = slots[i + 1]
        
        match = Match(
            round_id=first_round.id,
            match_order=(i // 2) + 1,
            team1_id=team1.id if team1 else None,
            team2_id=team2.id if team2 else None,
            bracket_type='winner'
        )
        
        # Si c'est un BYE (une seule équipe), résoudre automatiquement
        if team1 and not team2:
            match.is_finished = True
            match.winner_id = team1.id
            match.score = "BYE"
        elif team2 and not team1:
            match.is_finished = True
            match.winner_id = team2.id
            match.score = "BYE"
        
        db.add(match)
        first_round_matches.append(match)

    db.commit()

    # Créer les matchs des rounds suivants (vides)
    for round_idx in range(1, round_count):
        current_round = winner_rounds[round_idx]
        matches_in_round = bracket_size // (2 ** (round_idx + 1))
        
        for match_num in range(matches_in_round):
            match = Match(
                round_id=current_round.id,
                match_order=match_num + 1,
                team1_id=None,
                team2_id=None,
                bracket_type='winner'
            )
            db.add(match)

    db.commit()

    # Propager les BYE aux rounds suivants
    propagate_byes(db, winner_rounds, bracket_size)

    # ============================================
    # CRÉER LES MATCHS DE CLASSEMENT
    # ============================================
    
    create_classification_matches(db, tournament_id, round_count, bracket_size)

    return {
        "success": True,
        "teams": num_teams,
        "bracket_size": bracket_size,
        "rounds": round_count,
        "byes": num_byes,
        "seeded_teams": len(seeded_teams),
        "message": f"Bracket généré avec {num_teams} équipes et {num_byes} BYE"
    }


def get_seed_positions(bracket_size: int) -> dict:
    """
    Retourne les positions optimales pour les têtes de série.
    Les têtes de série sont placées pour ne se rencontrer qu'en finale/demi.
    """
    if bracket_size == 4:
        return {1: 0, 2: 3, 3: 1, 4: 2}
    elif bracket_size == 8:
        return {1: 0, 2: 7, 3: 3, 4: 4, 5: 1, 6: 6, 7: 2, 8: 5}
    elif bracket_size == 16:
        return {
            1: 0, 2: 15, 3: 7, 4: 8,
            5: 3, 6: 12, 7: 4, 8: 11,
            9: 1, 10: 14, 11: 6, 12: 9,
            13: 2, 14: 13, 15: 5, 16: 10
        }
    elif bracket_size == 32:
        return {
            1: 0, 2: 31, 3: 15, 4: 16,
            5: 7, 6: 24, 7: 8, 8: 23,
            9: 3, 10: 28, 11: 12, 12: 19,
            13: 4, 14: 27, 15: 11, 16: 20
        }
    else:
        # Fallback pour autres tailles
        return {1: 0, 2: bracket_size - 1}


def optimize_bye_positions(slots, seeded_teams, seed_positions, bracket_size):
    """
    Réorganise les slots pour que les BYE soient face aux têtes de série.
    """
    # Compter les BYE
    num_byes = sum(1 for s in slots if s is None)
    
    if num_byes == 0:
        return slots
    
    # Collecter toutes les équipes (non-None)
    all_teams = [s for s in slots if s is not None]
    
    # Recréer les slots
    new_slots = [None] * bracket_size
    
    # Placer les têtes de série aux positions définies
    for team in seeded_teams:
        pos = seed_positions.get(team.seed_position)
        if pos is not None and pos < bracket_size:
            new_slots[pos] = team
    
    # Les BYE vont aux positions adverses des têtes de série
    # (si TDS1 est en position 0, son adversaire en position 1 doit être un BYE si possible)
    bye_positions = []
    for i, team in enumerate(seeded_teams):
        if i >= num_byes:
            break
        pos = seed_positions.get(team.seed_position)
        if pos is not None:
            # L'adversaire direct est à pos+1 si pos est pair, pos-1 si impair
            opponent_pos = pos + 1 if pos % 2 == 0 else pos - 1
            if opponent_pos < bracket_size and opponent_pos not in bye_positions:
                bye_positions.append(opponent_pos)
    
    # Collecter les équipes non-têtes de série
    non_seeded = [t for t in all_teams if not t.is_seeded]
    random.shuffle(non_seeded)
    
    # Remplir les positions qui ne sont ni TDS ni BYE
    non_seeded_idx = 0
    for i in range(bracket_size):
        if new_slots[i] is None and i not in bye_positions:
            if non_seeded_idx < len(non_seeded):
                new_slots[i] = non_seeded[non_seeded_idx]
                non_seeded_idx += 1
    
    # S'il reste des équipes non placées (pas assez de positions), les mettre dans les positions BYE
    for i in bye_positions:
        if non_seeded_idx < len(non_seeded):
            new_slots[i] = non_seeded[non_seeded_idx]
            non_seeded_idx += 1
    
    return new_slots


def propagate_byes(db, winner_rounds, bracket_size):
    """
    Propage les vainqueurs des matchs BYE aux rounds suivants.
    """
    for round_idx in range(len(winner_rounds) - 1):
        current_round = winner_rounds[round_idx]
        next_round = winner_rounds[round_idx + 1]
        
        # Récupérer les matchs du round actuel
        current_matches = db.query(Match).filter(
            Match.round_id == current_round.id
        ).order_by(Match.match_order).all()
        
        # Récupérer les matchs du round suivant
        next_matches = db.query(Match).filter(
            Match.round_id == next_round.id
        ).order_by(Match.match_order).all()
        
        for match in current_matches:
            if match.is_finished and match.winner_id:
                # Trouver le match suivant
                next_match_order = (match.match_order + 1) // 2
                next_match_idx = next_match_order - 1
                
                if next_match_idx < len(next_matches):
                    next_match = next_matches[next_match_idx]
                    
                    # Les matchs impairs vont en team1, les pairs en team2
                    if match.match_order % 2 == 1:
                        next_match.team1_id = match.winner_id
                    else:
                        next_match.team2_id = match.winner_id
        
        db.commit()
        
        # Vérifier si des matchs du round suivant sont maintenant des BYE
        # (une seule équipe car l'autre match était aussi un BYE)
        for next_match in next_matches:
            if next_match.team1_id and not next_match.team2_id:
                # Vérifier si le match source pour team2 était un BYE résolu
                source_match_order = next_match.match_order * 2
                source_match = db.query(Match).filter(
                    Match.round_id == current_round.id,
                    Match.match_order == source_match_order
                ).first()
                
                if source_match and source_match.is_finished:
                    # Le match team2 source était un BYE, ce match devient un BYE aussi
                    if not next_match.team2_id:
                        next_match.is_finished = True
                        next_match.winner_id = next_match.team1_id
                        next_match.score = "BYE"
            
            elif next_match.team2_id and not next_match.team1_id:
                source_match_order = (next_match.match_order * 2) - 1
                source_match = db.query(Match).filter(
                    Match.round_id == current_round.id,
                    Match.match_order == source_match_order
                ).first()
                
                if source_match and source_match.is_finished:
                    if not next_match.team1_id:
                        next_match.is_finished = True
                        next_match.winner_id = next_match.team2_id
                        next_match.score = "BYE"
        
        db.commit()


def create_classification_matches(db, tournament_id: str, round_count: int, bracket_size: int):
    """Crée les matchs de classement (3ème place, 5ème place, etc.)"""
    
    if round_count >= 2:
        # Match pour la 3ème place
        r_3rd = Round(
            tournament_id=tournament_id,
            name="Match 3ème place",
            order=100
        )
        db.add(r_3rd)
        db.commit()
        db.refresh(r_3rd)
        
        match_3rd = Match(
            round_id=r_3rd.id,
            match_order=1,
            team1_id=None,
            team2_id=None,
            bracket_type='loser',
            classification_rank=3
        )
        db.add(match_3rd)
    
    if round_count >= 3:
        # Matchs pour 5-8ème place
        r_5th = Round(
            tournament_id=tournament_id,
            name="Matchs 5-8ème",
            order=101
        )
        db.add(r_5th)
        db.commit()
        db.refresh(r_5th)
        
        # Nombre de matchs = nombre de perdants des quarts / 2
        num_quarter_losers = bracket_size // 4
        num_matches_5th = num_quarter_losers // 2
        
        for i in range(max(1, num_matches_5th)):
            match = Match(
                round_id=r_5th.id,
                match_order=i + 1,
                team1_id=None,
                team2_id=None,
                bracket_type='loser',
                classification_rank=5
            )
            db.add(match)
        
        # Match pour 5ème place
        r_5th_final = Round(
            tournament_id=tournament_id,
            name="Match 5ème place",
            order=102
        )
        db.add(r_5th_final)
        db.commit()
        db.refresh(r_5th_final)
        
        match_5th = Match(
            round_id=r_5th_final.id,
            match_order=1,
            team1_id=None,
            team2_id=None,
            bracket_type='loser',
            classification_rank=5
        )
        db.add(match_5th)
        
        # Match pour 7ème place
        r_7th = Round(
            tournament_id=tournament_id,
            name="Match 7ème place",
            order=103
        )
        db.add(r_7th)
        db.commit()
        db.refresh(r_7th)
        
        match_7th = Match(
            round_id=r_7th.id,
            match_order=1,
            team1_id=None,
            team2_id=None,
            bracket_type='loser',
            classification_rank=7
        )
        db.add(match_7th)

    db.commit()


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