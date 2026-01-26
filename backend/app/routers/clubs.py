from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.club import Club
from app.models.club_user import ClubUser

router = APIRouter(prefix="/clubs", tags=["clubs"])


@router.post("/")
def create_club(
    name: str,
    city: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    club = Club(name=name, city=city)
    db.add(club)
    db.commit()
    db.refresh(club)

    link = ClubUser(
        club_id=club.id,
        user_id=user.id,
        role="owner"
    )
    db.add(link)
    db.commit()

    return club


@router.get("/")
def list_my_clubs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    clubs = (
        db.query(Club)
        .join(ClubUser, ClubUser.club_id == Club.id)
        .filter(ClubUser.user_id == user.id)
        .all()
    )
    return clubs


@router.post("/{club_id}/add-ja")
def add_ja_to_club(
    club_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # (V1 simple – pas encore de check owner)
    link = ClubUser(
        club_id=club_id,
        user_id=user_id,
        role="ja"
    )
    db.add(link)
    db.commit()

    return {"message": "JA added to club"}
