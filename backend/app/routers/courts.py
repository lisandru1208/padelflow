from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.court import Court
from app.models.club_user import ClubUser

router = APIRouter(
    prefix="/clubs/{club_id}/courts",
    tags=["courts"]
)


@router.post("/")
def add_court(
    club_id: str,
    name: str,
    indoor: bool = False,
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
    membership = db.query(ClubUser).filter(
        ClubUser.club_id == club_id,
        ClubUser.user_id == user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this club"
        )

    courts = db.query(Court).filter(
        Court.club_id == club_id
    ).all()

    return courts
