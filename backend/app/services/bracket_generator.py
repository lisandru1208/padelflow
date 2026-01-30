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

    # supprimer ancien tableau
    db.query(Match).join(Round).filter(
        Round.tournament_id == tournament_id
    ).delete(synchronize_session=False)

    db.query(Round).filter(
        Round.tournament_id == tournament_id
    ).delete()

    db.commit()

    # créer rounds
    rounds = []
    for i in range(round_count):
        r = Round(
            tournament_id=tournament_id,
            name=f"Round {i+1}",
            order=i + 1
        )
        db.add(r)
        db.commit()
        db.refresh(r)
        rounds.append(r)

    # seeds
    seeded = sorted(
        [t for t in teams if t.seed is not None],
        key=lambda t: t.seed
    )
    unseeded = [t for t in teams if t.seed is None]

    slots = [None] * bracket_size

    # positions seeds (V1 simple)
    seed_positions = list(range(len(seeded)))

    for team, pos in zip(seeded, seed_positions):
        slots[pos] = team

    # compléter avec non-seeds
    idx = 0
    for i in range(bracket_size):
        if slots[i] is None and idx < len(unseeded):
            slots[i] = unseeded[idx]
            idx += 1

    # créer matchs round 1
    first_round = rounds[0]

    for i in range(0, bracket_size, 2):
        match = Match(
            round_id=first_round.id,
            match_order=(i // 2) + 1,
            team1_id=slots[i].id if slots[i] else None,
            team2_id=slots[i + 1].id if slots[i + 1] else None
        )
        db.add(match)

    # créer matchs pour les rounds suivants (vides, à remplir quand les résultats arrivent)
    matches_in_round = bracket_size // 2
    for round_idx in range(1, round_count):
        matches_in_round = matches_in_round // 2
        current_round = rounds[round_idx]
        
        for match_num in range(matches_in_round):
            match = Match(
                round_id=current_round.id,
                match_order=match_num + 1,
                team1_id=None,
                team2_id=None
            )
            db.add(match)

    db.commit()

    return {
        "teams": len(teams),
        "bracket_size": bracket_size,
        "rounds": round_count
    }