from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.court import Court
from app.models.club_user import ClubUser
from app.models.match import Match

router = APIRouter(
    prefix="/clubs/{club_id}/courts",
    tags=["courts"]
)


def check_membership(db: Session, club_id: str, user_id: str):
    membership = db.query(ClubUser).filter(
        ClubUser.club_id == club_id,
        ClubUser.user_id == user_id
    ).first()

    if not membership:
        raise HTTPException(status_code=403, detail="Not allowed")


@router.post("/")
def add_court(
    club_id: str,
    name: str,
    indoor: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    check_membership(db, club_id, user.id)

    court = Court(
        club_id=club_id,
        name=name,
        indoor=indoor
    )
    db.add(court)
    db.commit()
    db.refresh(court)

    return court


@router.get("/")
def list_courts(
    club_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    check_membership(db, club_id, user.id)

    courts = db.query(Court).filter(Court.club_id == club_id).all()
    return courts


@router.put("/{court_id}")
def update_court(
    club_id: str,
    court_id: str,
    name: Optional[str] = None,
    indoor: Optional[bool] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    check_membership(db, club_id, user.id)

    court = db.query(Court).filter(
        Court.id == court_id,
        Court.club_id == club_id
    ).first()

    if not court:
        raise HTTPException(status_code=404, detail="Court not found")

    if name:
        court.name = name
    if indoor is not None:
        court.indoor = indoor

    db.commit()
    db.refresh(court)

    return court


@router.delete("/{court_id}")
def delete_court(
    club_id: str,
    court_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    check_membership(db, club_id, user.id)

    court = db.query(Court).filter(
        Court.id == court_id,
        Court.club_id == club_id
    ).first()

    if not court:
        raise HTTPException(status_code=404, detail="Court not found")

    # Vérifier si le court est utilisé dans des matchs
    match_with_court = db.query(Match).filter(Match.court_id == court_id).first()
    if match_with_court:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete court: it is assigned to matches"
        )

    db.delete(court)
    db.commit()

    return {"message": "Court deleted"}