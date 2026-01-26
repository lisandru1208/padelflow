from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.tournament import Tournament
from app.models.club_user import ClubUser

router = APIRouter(
    prefix="/clubs/{club_id}/tournaments",
    tags=["tournaments"]
)


@router.post("/")
def create_tournament(
    club_id: str,
    name: str,
    category: str,
    gender: str,
    start_date: date,
    end_date: date | None = None,
    indoor: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Vérifier que le JA appartient au club
    membership = db.query(ClubUser).filter(
        ClubUser.club_id == club_id,
        ClubUser.user_id == user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this club"
        )

    tournament = Tournament(
        club_id=club_id,
        name=name,
        category=category,
        gender=gender,
        start_date=start_date,
        end_date=end_date,
        indoor=indoor
    )

    db.add(tournament)
    db.commit()
    db.refresh(tournament)

    return tournament


@router.get("/")
def list_tournaments(
    club_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    membership = db.query(ClubUser).filter(
        ClubUser.club_id == club_id,
        ClubUser.user_id == user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this club"
        )

    tournaments = db.query(Tournament).filter(
        Tournament.club_id == club_id
    ).all()

    return tournaments
