import math
from app.models.round import Round
from app.models.match import Match
from app.models.team import Team


def compute_bracket_size(num_teams: int) -> int:
    """Calcule la taille du bracket (puissance de 2 supérieure ou égale)"""
    if num_teams < 2:
        return 2
    return 2 ** math.ceil(math.log2(num_teams))


def generate_bracket(db, tournament_id: str):
    teams = db.query(Team).filter(
        Team.tournament_id == tournament_id
    ).all()

    if len(teams) < 2:
        raise ValueError("Minimum 2 teams required")

    bracket_size = compute_bracket_size(len(teams))
    round_count = int(math.log2(bracket_size))

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

    # Seeds
    seeded = sorted(
        [t for t in teams if t.seed is not None],
        key=lambda t: t.seed
    )
    unseeded = [t for t in teams if t.seed is None]

    slots = [None] * bracket_size

    # Positions seeds
    seed_positions = list(range(len(seeded)))
    for team, pos in zip(seeded, seed_positions):
        slots[pos] = team

    # Compléter avec non-seeds
    idx = 0
    for i in range(bracket_size):
        if slots[i] is None and idx < len(unseeded):
            slots[i] = unseeded[idx]
            idx += 1

    # Créer matchs du premier round (winner)
    first_round = winner_rounds[0]
    for i in range(0, bracket_size, 2):
        match = Match(
            round_id=first_round.id,
            match_order=(i // 2) + 1,
            team1_id=slots[i].id if slots[i] else None,
            team2_id=slots[i + 1].id if slots[i + 1] else None,
            bracket_type='winner'
        )
        db.add(match)

    # Créer matchs vides pour les rounds suivants (winner)
    matches_in_round = bracket_size // 2
    for round_idx in range(1, round_count):
        matches_in_round = matches_in_round // 2
        current_round = winner_rounds[round_idx]
        
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

    # ============================================
    # LOSER BRACKET (Matchs de classement)
    # ============================================
    
    loser_rounds = []
    
    if round_count >= 2:
        # Match pour la 3ème place (perdants des demi-finales)
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
        # Matchs pour 5-8ème place (perdants des quarts)
        r_5th = Round(
            tournament_id=tournament_id,
            name="Matchs 5-8ème",
            order=101
        )
        db.add(r_5th)
        db.commit()
        db.refresh(r_5th)
        loser_rounds.append(r_5th)
        
        # Demi-finales du loser (2 matchs pour 8 équipes)
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
        "winner_rounds": len(winner_rounds),
        "loser_rounds": len(loser_rounds),
        "message": f"Bracket généré avec {len(teams)} équipes et matchs de classement"
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