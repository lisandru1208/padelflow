from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.db.deps import get_db
from app.core.deps import get_current_user

from app.models.match import Match
from app.models.round import Round
from app.models.court import Court
from app.models.tournament import Tournament
from app.models.club_user import ClubUser

router = APIRouter(
    prefix="/rounds/{round_id}/matches",
    tags=["matches"]
)

def check_ja_for_round(db: Session, round_id: str, user_id: str):
    round_ = db.query(Round).filter(Round.id == round_id).first()
    if not round_:
        raise HTTPException(status_code=404, detail="Round not found")

    tournament = db.query(Tournament).filter(
        Tournament.id == round_.tournament_id
    ).first()

    membership = db.query(ClubUser).filter(
        ClubUser.club_id == tournament.club_id,
        ClubUser.user_id == user_id
    ).first()

    if not membership:
        raise HTTPException(status_code=403, detail="Not allowed")

    return round_

@router.get("/")
def list_matches(
    round_id: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    check_ja_for_round(db, round_id, user.id)

    return (
        db.query(Match)
        .filter(Match.round_id == round_id)
        .order_by(Match.match_order)
        .all()
    )

@router.put("/{match_id}/court")
def assign_court(
    round_id: str,
    match_id: str,
    court_id: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    check_ja_for_round(db, round_id, user.id)

    match = db.query(Match).filter(
        Match.id == match_id,
        Match.round_id == round_id
    ).first()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    court = db.query(Court).filter(Court.id == court_id).first()
    if not court:
        raise HTTPException(status_code=404, detail="Court not found")

    match.court_id = court_id
    db.commit()

    return {"message": "Court assigned"}


class ReorderMatches(BaseModel):
    ordered_match_ids: List[str]


@router.put("/reorder")
def reorder_matches(
    round_id: str,
    payload: ReorderMatches,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    check_ja_for_round(db, round_id, user.id)

    for index, match_id in enumerate(payload.ordered_match_ids):
        match = db.query(Match).filter(
            Match.id == match_id,
            Match.round_id == round_id
        ).first()

        if not match:
            raise HTTPException(
                status_code=404,
                detail=f"Match {match_id} not found"
            )

        match.match_order = index + 1

    db.commit()
    return {"message": "Matches reordered"}
