from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.match import Match
from app.models.round import Round
from app.models.team import Team
from app.routers.matches import check_ja_for_round


router = APIRouter(
    prefix="/matches",
    tags=["scores"]
)


# -----------------------------
# Schema
# -----------------------------

class ScoreInput(BaseModel):
    score: str
    winner_team_id: str


# -----------------------------
# Endpoint
# -----------------------------

@router.post("/{match_id}/score")
def submit_score(
    match_id: str,
    payload: ScoreInput,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Sécurité JA
    check_ja_for_round(db, str(match.round_id), user.id)

    if match.is_finished:
        raise HTTPException(status_code=400, detail="Match already finished")

    # Convertir les UUIDs en strings pour la comparaison
    team1_id_str = str(match.team1_id) if match.team1_id else None
    team2_id_str = str(match.team2_id) if match.team2_id else None
    winner_id_str = payload.winner_team_id.strip()

    if winner_id_str not in [team1_id_str, team2_id_str]:
        raise HTTPException(
            status_code=400, 
            detail=f"Winner not in match. Expected {team1_id_str} or {team2_id_str}, got {winner_id_str}"
        )

    if not payload.score.strip():
        raise HTTPException(status_code=400, detail="Score cannot be empty")

    match.score = payload.score
    match.winner_id = winner_id_str
    match.is_finished = True

    db.commit()

    # Propager le vainqueur au match suivant
    propagate_winner(db, match)

    return {
        "message": "Score saved",
        "match_id": str(match.id),
        "winner_team_id": str(match.winner_id)
    }


def propagate_winner(db: Session, match: Match):
    """Propage le vainqueur au match suivant dans le bracket"""
    # Récupérer le round actuel
    current_round = db.query(Round).filter(Round.id == match.round_id).first()
    if not current_round:
        return

    # Trouver le round suivant
    next_round = db.query(Round).filter(
        Round.tournament_id == current_round.tournament_id,
        Round.order == current_round.order + 1
    ).first()

    if not next_round:
        return  # C'était la finale

    # Trouver le match suivant (position = match_order // 2)
    next_match_order = (match.match_order + 1) // 2
    next_match = db.query(Match).filter(
        Match.round_id == next_round.id,
        Match.match_order == next_match_order
    ).first()

    if not next_match:
        return

    # Déterminer si c'est team1 ou team2 du match suivant
    # Les matchs impairs vont en team1, les pairs en team2
    if match.match_order % 2 == 1:
        next_match.team1_id = match.winner_id
    else:
        next_match.team2_id = match.winner_id

    db.commit()