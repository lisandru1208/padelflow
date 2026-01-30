from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.tournament import Tournament
from app.models.club_user import ClubUser
from app.models.team import Team
from app.models.player import Player
from app.models.round import Round
from app.models.match import Match
from fastapi.responses import FileResponse
from app.services.pdf.tournament_pdf import generate_tournament_pdf
from app.services.csv.tournament_csv import generate_tournament_csv

router = APIRouter(
    prefix="/clubs/{club_id}/tournaments",
    tags=["tournaments"]
)


def check_membership(db: Session, club_id: str, user_id: str):
    membership = db.query(ClubUser).filter(
        ClubUser.club_id == club_id,
        ClubUser.user_id == user_id
    ).first()

    if not membership:
        raise HTTPException(status_code=403, detail="Not allowed")


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
    check_membership(db, club_id, user.id)

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
    check_membership(db, club_id, user.id)

    tournaments = db.query(Tournament).filter(
        Tournament.club_id == club_id
    ).all()

    return tournaments


@router.put("/{tournament_id}")
def update_tournament(
    club_id: str,
    tournament_id: str,
    name: Optional[str] = None,
    category: Optional[str] = None,
    gender: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    indoor: Optional[bool] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    check_membership(db, club_id, user.id)

    tournament = db.query(Tournament).filter(
        Tournament.id == tournament_id,
        Tournament.club_id == club_id
    ).first()

    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    if tournament.bracket_generated:
        raise HTTPException(
            status_code=400, 
            detail="Cannot modify tournament after bracket is generated"
        )

    if name:
        tournament.name = name
    if category:
        tournament.category = category
    if gender:
        tournament.gender = gender
    if start_date:
        tournament.start_date = start_date
    if end_date is not None:
        tournament.end_date = end_date
    if indoor is not None:
        tournament.indoor = indoor

    db.commit()
    db.refresh(tournament)

    return tournament


@router.delete("/{tournament_id}")
def delete_tournament(
    club_id: str,
    tournament_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    check_membership(db, club_id, user.id)

    tournament = db.query(Tournament).filter(
        Tournament.id == tournament_id,
        Tournament.club_id == club_id
    ).first()

    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    # Supprimer les rounds et matches
    rounds = db.query(Round).filter(Round.tournament_id == tournament_id).all()
    for r in rounds:
        db.query(Match).filter(Match.round_id == r.id).delete()
    db.query(Round).filter(Round.tournament_id == tournament_id).delete()

    # Supprimer les teams et players
    teams = db.query(Team).filter(Team.tournament_id == tournament_id).all()
    for team in teams:
        db.query(Player).filter(Player.team_id == team.id).delete()
    db.query(Team).filter(Team.tournament_id == tournament_id).delete()

    db.delete(tournament)
    db.commit()

    return {"message": "Tournament deleted"}


@router.get("/{tournament_id}/export-pdf")
def export_pdf(
    club_id: str,
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    check_membership(db, club_id, user.id)
    
    output_path = f"/tmp/tournament_{tournament_id}.pdf"
    generate_tournament_pdf(db, tournament_id, output_path)

    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename="tournament_results.pdf"
    )


@router.get("/{tournament_id}/export-csv")
def export_csv(
    club_id: str,
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    check_membership(db, club_id, user.id)
    
    output_path = f"/tmp/tournament_{tournament_id}.csv"
    generate_tournament_csv(db, tournament_id, output_path)

    return FileResponse(
        output_path,
        media_type="text/csv",
        filename="tournament_results.csv"
    )