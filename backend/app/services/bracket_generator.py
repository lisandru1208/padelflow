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
    return 2 ** math.floor(math.log2(num_teams))


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
    random.seed(time.time() * 1000)

    teams = db.query(Team).filter(
        Team.tournament_id == tournament_id
    ).all()

    if len(teams) < 2:
        raise ValueError("Minimum 2 teams required")

    num_teams = len(teams)

    # On descend vers la puissance de 2 inférieure
    bracket_size = compute_bracket_size(num_teams)
    round_count = int(math.log2(bracket_size))

    num_prelim_matches = num_teams - bracket_size
    num_teams_in_prelim = num_prelim_matches * 2
    num_direct_qualified = num_teams - num_teams_in_prelim

    print(f"=== GÉNÉRATION BRACKET ===")
    print(f"Équipes: {num_teams}")
    print(f"Bracket principal: {bracket_size}")
    print(f"Matchs préliminaires: {num_prelim_matches}")
    print(f"Équipes en préliminaire: {num_teams_in_prelim}")
    print(f"Qualifiés directs: {num_direct_qualified}")

    # ============================================
    # NETTOYER
    # ============================================

    existing_rounds = db.query(Round).filter(
        Round.tournament_id == tournament_id
    ).all()

    for r in existing_rounds:
        db.query(Match).filter(Match.round_id == r.id).delete()

    db.query(Round).filter(Round.tournament_id == tournament_id).delete()
    db.commit()

    # ============================================
    # PRÉPARER LES ÉQUIPES
    # ============================================

    seeded_teams = sorted(
        [t for t in teams if t.is_seeded],
        key=lambda t: t.seed_position or 999
    )
    unseeded_teams = [t for t in teams if not t.is_seeded]

    # Qualifiés directs = meilleurs
    direct_qualified = seeded_teams[:num_direct_qualified]

    # Préliminaires = le reste
    prelim_teams = seeded_teams[num_direct_qualified:] + unseeded_teams
    random.shuffle(prelim_teams)
    prelim_teams = prelim_teams[:num_teams_in_prelim]

    # ============================================
    # ROUND 0 : PRÉLIMINAIRES
    # ============================================

    if num_prelim_matches > 0:
        r0 = Round(
            tournament_id=tournament_id,
            name="Tour préliminaire",
            order=0
        )
        db.add(r0)
        db.commit()
        db.refresh(r0)

        for i in range(num_prelim_matches):
            t1 = prelim_teams[i * 2]
            t2 = prelim_teams[i * 2 + 1]

            match = Match(
                round_id=r0.id,
                match_order=i + 1,
                team1_id=t1.id,
                team2_id=t2.id,
                bracket_type='winner'
            )
            db.add(match)

        db.commit()

    # ============================================
    # ROUND 1+ : BRACKET PARFAIT
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

    # Les équipes du vrai bracket :
    # direct_qualified + futurs vainqueurs des prélims
    # (à relier dynamiquement plus tard)

    return {
        "success": True,
        "teams": num_teams,
        "bracket_size": bracket_size,
        "rounds": round_count,
        "prelim_matches": num_prelim_matches,
        "direct_qualified": num_direct_qualified,
        "message": f"Bracket généré avec {num_teams} équipes"
    }


def place_teams_in_bracket(seeded_teams, unseeded_teams, bracket_size, num_byes):
    """
    Nouvelle logique :
    - Les meilleurs seeds vont DIRECTEMENT au tour suivant
    - Les moins bons jouent les tours préliminaires
    """

    slots = [None] * bracket_size

    # Positions fixes pour les seeds
    seed_positions = get_seed_slot_positions(bracket_size)

    # 1. On place les seeds
    for i, team in enumerate(seeded_teams):
        seed_num = i + 1
        if seed_num in seed_positions:
            slots[seed_positions[seed_num]] = team

    # 2. Les BYE = positions occupées par seeds sans adversaire
    bye_positions = []
    for i in range(num_byes):
        seed_num = i + 1
        if seed_num in seed_positions:
            bye_positions.append(seed_positions[seed_num])

    # 3. Tous les autres jouent (unseeded + seeds non protégés)
    remaining_teams = seeded_teams[num_byes:] + unseeded_teams
    random.shuffle(remaining_teams)

    idx = 0
    for i in range(bracket_size):
        if slots[i] is None and i not in bye_positions:
            if idx < len(remaining_teams):
                slots[i] = remaining_teams[idx]
                idx += 1

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


def create_classification_matches(db, tournament_id: str, round_count: int, bracket_size: int, court_ids: list = None):
    """
    Crée les matchs de classement (3ème place, 5ème place, etc.)
    
    Organisation:
    - order 100: Match 3ème place (perdants demi-finales)
    - order 101: Demi-finales 5-8ème (perdants quarts)
    - order 102: Match 5ème place
    - order 103: Match 7ème place
    - order 104: Demi-finales 9-12ème (perdants huitièmes)
    - order 105: Match 9ème place
    - order 106: Match 11ème place
    """
    court_idx = 0
    
    def get_next_court():
        nonlocal court_idx
        if court_ids and len(court_ids) > 0:
            court_id = court_ids[court_idx % len(court_ids)]
            court_idx += 1
            return court_id
        return None
    
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
    
    if round_count >= 3:
        # Demi-finales pour 5-8ème place (perdants des quarts)
        r_5th_semi = Round(
            tournament_id=tournament_id,
            name="Demi-finales 5-8ème",
            order=101
        )
        db.add(r_5th_semi)
        db.commit()
        db.refresh(r_5th_semi)
        
        # 2 matchs de demi pour la 5-8ème place
        for i in range(2):
            match = Match(
                round_id=r_5th_semi.id,
                match_order=i + 1,
                team1_id=None,
                team2_id=None,
                bracket_type='loser',
                classification_rank=5,
                court_id=get_next_court()
            )
            db.add(match)
        
        # Match pour 5ème place (vainqueurs des demis 5-8)
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
            classification_rank=5,
            court_id=get_next_court()
        )
        db.add(match_5th)
        
        # Match pour 7ème place (perdants des demis 5-8)
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
            classification_rank=7,
            court_id=get_next_court()
        )
        db.add(match_7th)
    
    if round_count >= 4:
        # Demi-finales pour 9-12ème place (perdants des huitièmes)
        r_9th_semi = Round(
            tournament_id=tournament_id,
            name="Demi-finales 9-12ème",
            order=104
        )
        db.add(r_9th_semi)
        db.commit()
        db.refresh(r_9th_semi)
        
        # 2 matchs de demi pour la 9-12ème place
        for i in range(2):
            match = Match(
                round_id=r_9th_semi.id,
                match_order=i + 1,
                team1_id=None,
                team2_id=None,
                bracket_type='loser',
                classification_rank=9,
                court_id=get_next_court()
            )
            db.add(match)
        
        # Match pour 9ème place
        r_9th_final = Round(
            tournament_id=tournament_id,
            name="Match 9ème place",
            order=105
        )
        db.add(r_9th_final)
        db.commit()
        db.refresh(r_9th_final)
        
        match_9th = Match(
            round_id=r_9th_final.id,
            match_order=1,
            team1_id=None,
            team2_id=None,
            bracket_type='loser',
            classification_rank=9,
            court_id=get_next_court()
        )
        db.add(match_9th)
        
        # Match pour 11ème place
        r_11th = Round(
            tournament_id=tournament_id,
            name="Match 11ème place",
            order=106
        )
        db.add(r_11th)
        db.commit()
        db.refresh(r_11th)
        
        match_11th = Match(
            round_id=r_11th.id,
            match_order=1,
            team1_id=None,
            team2_id=None,
            bracket_type='loser',
            classification_rank=11,
            court_id=get_next_court()
        )
        db.add(match_11th)
    
    if round_count >= 5:
        # Demi-finales pour 13-16ème place (perdants des 16èmes)
        r_13th_semi = Round(
            tournament_id=tournament_id,
            name="Demi-finales 13-16ème",
            order=107
        )
        db.add(r_13th_semi)
        db.commit()
        db.refresh(r_13th_semi)
        
        # 2 matchs de demi pour la 13-16ème place
        for i in range(2):
            match = Match(
                round_id=r_13th_semi.id,
                match_order=i + 1,
                team1_id=None,
                team2_id=None,
                bracket_type='loser',
                classification_rank=13,
                court_id=get_next_court()
            )
            db.add(match)
        
        # Match pour 13ème place
        r_13th_final = Round(
            tournament_id=tournament_id,
            name="Match 13ème place",
            order=108
        )
        db.add(r_13th_final)
        db.commit()
        db.refresh(r_13th_final)
        
        match_13th = Match(
            round_id=r_13th_final.id,
            match_order=1,
            team1_id=None,
            team2_id=None,
            bracket_type='loser',
            classification_rank=13,
            court_id=get_next_court()
        )
        db.add(match_13th)
        
        # Match pour 15ème place
        r_15th = Round(
            tournament_id=tournament_id,
            name="Match 15ème place",
            order=109
        )
        db.add(r_15th)
        db.commit()
        db.refresh(r_15th)
        
        match_15th = Match(
            round_id=r_15th.id,
            match_order=1,
            team1_id=None,
            team2_id=None,
            bracket_type='loser',
            classification_rank=15,
            court_id=get_next_court()
        )
        db.add(match_15th)

    db.commit()