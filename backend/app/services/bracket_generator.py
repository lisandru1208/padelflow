import math
import random
from app.models.round import Round
from app.models.match import Match
from app.models.team import Team


def compute_bracket_size(num_teams: int) -> int:
    """Calcule la taille du bracket (puissance de 2 supérieure ou égale)"""
    if num_teams < 2:
        return 2
    return 2 ** math.ceil(math.log2(num_teams))


def get_seed_positions(bracket_size: int) -> dict:
    """
    Retourne les positions optimales pour les têtes de série.
    Les têtes de série sont placées pour ne se rencontrer qu'en finale/demi.
    """
    # Positions standards pour les têtes de série
    positions = {
        4: {1: 0, 2: 3},  # 4 équipes: TDS1 en haut, TDS2 en bas
        8: {1: 0, 2: 7, 3: 3, 4: 4},  # 8 équipes
        16: {1: 0, 2: 15, 3: 7, 4: 8, 5: 3, 6: 12, 7: 4, 8: 11},  # 16 équipes
        32: {1: 0, 2: 31, 3: 15, 4: 16, 5: 7, 6: 24, 7: 8, 8: 23}  # 32 équipes
    }
    return positions.get(bracket_size, {1: 0, 2: bracket_size - 1})


def generate_bracket(db, tournament_id: str):
    teams = db.query(Team).filter(
        Team.tournament_id == tournament_id
    ).all()

    if len(teams) < 2:
        raise ValueError("Minimum 2 teams required")

    bracket_size = compute_bracket_size(len(teams))
    round_count = int(math.log2(bracket_size))
    num_byes = bracket_size - len(teams)

    # Supprimer ancien tableau
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
    # TIRAGE AU SORT INTELLIGENT
    # ============================================
    
    # Séparer têtes de série et autres
    seeded_teams = sorted(
        [t for t in teams if t.is_seeded],
        key=lambda t: t.seed_position or 999
    )
    unseeded_teams = [t for t in teams if not t.is_seeded]
    
    # Mélanger les équipes non-têtes de série
    random.shuffle(unseeded_teams)
    
    # Créer les slots du bracket
    slots = [None] * bracket_size
    
    # Placer les têtes de série aux positions stratégiques
    seed_positions = get_seed_positions(bracket_size)
    for team in seeded_teams:
        pos = seed_positions.get(team.seed_position)
        if pos is not None and pos < bracket_size:
            slots[pos] = team
    
    # Les BYE vont aux têtes de série (positions opposées)
    # BYE = adversaire de la tête de série au premier tour
    bye_positions = []
    for team in seeded_teams[:num_byes]:
        pos = seed_positions.get(team.seed_position)
        if pos is not None:
            # L'adversaire de la tête de série est à la position +1 ou -1 selon si pair/impair
            if pos % 2 == 0:
                bye_pos = pos + 1
            else:
                bye_pos = pos - 1
            if bye_pos < bracket_size and bye_pos not in bye_positions:
                bye_positions.append(bye_pos)
    
    # Remplir les positions restantes avec les équipes non-têtes de série
    unseeded_idx = 0
    for i in range(bracket_size):
        if slots[i] is None and i not in bye_positions:
            if unseeded_idx < len(unseeded_teams):
                slots[i] = unseeded_teams[unseeded_idx]
                unseeded_idx += 1

    # ============================================
    # WINNER BRACKET
    # ============================================
    
    winner_rounds = []
    for i in range(round_count):
        round_name = get_round_name(i + 1, round_count, is_loser=False)
        r = Round(
            tournament_id=tournament_id,
            name=round_name,
            order=i + 1
        )
        db.add(r)
        db.commit()
        db.refresh(r)
        winner_rounds.append(r)

    # Créer matchs du premier round
    first_round = winner_rounds[0]
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
        db.add(match)
        
        # Si c'est un BYE (une seule équipe), propager automatiquement au tour suivant
        if (team1 and not team2) or (team2 and not team1):
            match.is_finished = True
            match.winner_id = team1.id if team1 else team2.id
            match.score = "BYE"

    db.commit()

    # Propager les BYE au tour suivant
    if round_count > 1:
        first_round_matches = db.query(Match).filter(
            Match.round_id == first_round.id
        ).order_by(Match.match_order).all()
        
        second_round = winner_rounds[1]
        
        for match in first_round_matches:
            if match.is_finished and match.score == "BYE":
                # Trouver le match du tour suivant
                next_match_order = (match.match_order + 1) // 2
                next_match = db.query(Match).filter(
                    Match.round_id == second_round.id,
                    Match.match_order == next_match_order
                ).first()
                
                if not next_match:
                    # Créer le match s'il n'existe pas encore
                    next_match = Match(
                        round_id=second_round.id,
                        match_order=next_match_order,
                        team1_id=None,
                        team2_id=None,
                        bracket_type='winner'
                    )
                    db.add(next_match)
                    db.commit()
                    db.refresh(next_match)
                
                # Propager le vainqueur
                if match.match_order % 2 == 1:
                    next_match.team1_id = match.winner_id
                else:
                    next_match.team2_id = match.winner_id

    db.commit()

    # Créer matchs vides pour les rounds suivants (winner)
    matches_in_round = bracket_size // 2
    for round_idx in range(1, round_count):
        matches_in_round = matches_in_round // 2
        current_round = winner_rounds[round_idx]
        
        # Vérifier si les matchs existent déjà
        existing_matches = db.query(Match).filter(
            Match.round_id == current_round.id
        ).count()
        
        for match_num in range(matches_in_round):
            # Vérifier si ce match existe déjà
            existing = db.query(Match).filter(
                Match.round_id == current_round.id,
                Match.match_order == match_num + 1
            ).first()
            
            if not existing:
                match = Match(
                    round_id=current_round.id,
                    match_order=match_num + 1,
                    team1_id=None,
                    team2_id=None,
                    bracket_type='winner'
                )
                db.add(match)

    db.commit()

    # ============================================
    # LOSER BRACKET (Matchs de classement)
    # ============================================
    
    loser_rounds = []
    
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
        loser_rounds.append(r_3rd)
        
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
        loser_rounds.append(r_5th)
        
        num_quarter_matches = bracket_size // 4
        for i in range(num_quarter_matches):
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
        loser_rounds.append(r_5th_final)
        
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
        loser_rounds.append(r_7th)
        
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

    return {
        "success": True,
        "teams": len(teams),
        "bracket_size": bracket_size,
        "rounds": round_count,
        "byes": num_byes,
        "seeded_teams": len(seeded_teams),
        "winner_rounds": len(winner_rounds),
        "loser_rounds": len(loser_rounds),
        "message": f"Bracket généré avec {len(teams)} équipes, {num_byes} BYE et matchs de classement"
    }


def get_round_name(round_number: int, total_rounds: int, is_loser: bool = False) -> str:
    """Retourne le nom du round"""
    remaining = total_rounds - round_number
    
    if is_loser:
        return f"Classement Tour {round_number}"
    
    if remaining == 0:
        return "Finale"
    elif remaining == 1:
        return "Demi-finales"
    elif remaining == 2:
        return "Quarts de finale"
    elif remaining == 3:
        return "Huitièmes de finale"
    else:
        return f"Tour {round_number}"