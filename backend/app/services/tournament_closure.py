from sqlalchemy.orm import Session

from app.models.tournament import Tournament
from app.models.round import Round
from app.models.match import Match


def can_finish_tournament(db: Session, tournament_id: str) -> bool:
    matches = (
        db.query(Match)
        .join(Round, Match.round_id == Round.id)
        .filter(Round.tournament_id == tournament_id)
        .all()
    )

    if not matches:
        return False

    return all(match.is_finished for match in matches)


def finish_tournament(db: Session, tournament_id: str):
    tournament = db.query(Tournament).filter(
        Tournament.id == tournament_id
    ).first()

    if not tournament:
        raise ValueError("Tournament not found")

    if tournament.is_finished:
        return tournament

    if not can_finish_tournament(db, tournament_id):
        raise ValueError("Not all matches are finished")

    tournament.is_finished = True
    db.commit()

    return tournament
