from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.match import Match
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
    check_ja_for_round(db, match.round_id, user.id)

    if match.is_finished:
        raise HTTPException(status_code=400, detail="Match already finished")

    if payload.winner_team_id not in [match.team1_id, match.team2_id]:
        raise HTTPException(status_code=400, detail="Winner not in match")

    if not payload.score.strip():
        raise HTTPException(status_code=400, detail="Score cannot be empty")

    match.score = payload.score
    match.winner_id = payload.winner_team_id
    match.is_finished = True

    db.commit()

    return {
        "message": "Score saved",
        "match_id": match.id,
        "winner_team_id": match.winner_id
    }
