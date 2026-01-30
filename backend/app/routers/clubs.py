from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.club import Club
from app.models.club_user import ClubUser
from app.models.court import Court
from app.models.tournament import Tournament
from app.models.team import Team
from app.models.player import Player
from app.models.round import Round
from app.models.match import Match

router = APIRouter(
    prefix="/clubs",
    tags=["clubs"]
)


@router.post("/")
def create_club(
    name: str,
    city: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    club = Club(name=name, city=city, owner_id=user.id)
    db.add(club)
    db.commit()
    db.refresh(club)

    # Ajouter automatiquement le créateur comme JA
    link = ClubUser(club_id=club.id, user_id=user.id)
    db.add(link)
    db.commit()

    return club


@router.get("/")
def list_my_clubs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    club_ids = db.query(ClubUser.club_id).filter(
        ClubUser.user_id == user.id
    ).subquery()

    clubs = db.query(Club).filter(Club.id.in_(club_ids)).all()
    return clubs


@router.put("/{club_id}")
def update_club(
    club_id: str,
    name: Optional[str] = None,
    city: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Vérifier que l'utilisateur est membre du club
    membership = db.query(ClubUser).filter(
        ClubUser.club_id == club_id,
        ClubUser.user_id == user.id
    ).first()

    if not membership:
        raise HTTPException(status_code=403, detail="Not allowed")

    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")

    if name:
        club.name = name
    if city is not None:
        club.city = city

    db.commit()
    db.refresh(club)

    return club


@router.delete("/{club_id}")
def delete_club(
    club_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Vérifier que l'utilisateur est le propriétaire
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")

    if str(club.owner_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Only owner can delete club")

    # Supprimer en cascade : tournaments -> rounds -> matches, teams -> players, courts
    tournaments = db.query(Tournament).filter(Tournament.club_id == club_id).all()
    for tournament in tournaments:
        # Supprimer les rounds et matches
        rounds = db.query(Round).filter(Round.tournament_id == tournament.id).all()
        for r in rounds:
            db.query(Match).filter(Match.round_id == r.id).delete()
        db.query(Round).filter(Round.tournament_id == tournament.id).delete()
        
        # Supprimer les teams et players
        teams = db.query(Team).filter(Team.tournament_id == tournament.id).all()
        for team in teams:
            db.query(Player).filter(Player.team_id == team.id).delete()
        db.query(Team).filter(Team.tournament_id == tournament.id).delete()

    db.query(Tournament).filter(Tournament.club_id == club_id).delete()
    db.query(Court).filter(Court.club_id == club_id).delete()
    db.query(ClubUser).filter(ClubUser.club_id == club_id).delete()
    db.delete(club)
    db.commit()

    return {"message": "Club deleted"}


@router.post("/{club_id}/add-ja")
def add_ja_to_club(
    club_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Vérifier que l'utilisateur actuel est membre du club
    membership = db.query(ClubUser).filter(
        ClubUser.club_id == club_id,
        ClubUser.user_id == user.id
    ).first()

    if not membership:
        raise HTTPException(status_code=403, detail="Not allowed")

    # Vérifier si déjà membre
    existing = db.query(ClubUser).filter(
        ClubUser.club_id == club_id,
        ClubUser.user_id == user_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="User already member")

    link = ClubUser(club_id=club_id, user_id=user_id)
    db.add(link)
    db.commit()

    return {"message": "JA added to club"}