from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.services.bracket_generator import generate_bracket
from app.models.round import Round
from app.models.match import Match
from app.models.team import Team
from app.models.player import Player
from app.models.tournament import Tournament
from app.models.club_user import ClubUser
from app.models.court import Court

router = APIRouter(
    prefix="/tournaments/{tournament_id}",
    tags=["bracket"]
)


def check_ja_for_tournament(db: Session, tournament_id: str, user_id: str):
    tournament = db.query(Tournament).filter(
        Tournament.id == tournament_id
    ).first()

    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    membership = db.query(ClubUser).filter(
        ClubUser.club_id == tournament.club_id,
        ClubUser.user_id == user_id
    ).first()

    if not membership:
        raise HTTPException(status_code=403, detail="Not allowed")

    return tournament


class GenerateBracketInput(BaseModel):
    court_ids: Optional[List[str]] = None


@router.post("/generate-bracket")
def generate(
    tournament_id: str,
    payload: Optional[GenerateBracketInput] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    tournament = check_ja_for_tournament(db, tournament_id, user.id)
    
    # Générer le bracket
    result = generate_bracket(db, tournament_id)
    
    # Sauvegarder les courts sélectionnés si fournis
    court_ids = payload.court_ids if payload and payload.court_ids else []
    if court_ids:
        tournament.selected_court_ids = json.dumps(court_ids)
    
    # Marquer le bracket comme généré
    tournament.bracket_generated = True
    db.commit()
    
    # Assigner automatiquement les courts aux matchs du premier round
    if court_ids:
        assign_courts_to_first_round(db, tournament_id, court_ids)
    
    return result


def assign_courts_to_first_round(db: Session, tournament_id: str, court_ids: List[str]):
    """Assigne automatiquement les courts aux matchs du premier round"""
    # Récupérer le premier round
    first_round = db.query(Round).filter(
        Round.tournament_id == tournament_id,
        Round.order == 1
    ).first()
    
    if not first_round or not court_ids:
        return
    
    # Récupérer les matchs du premier round
    matches = db.query(Match).filter(
        Match.round_id == first_round.id
    ).order_by(Match.match_order).all()
    
    # Assigner les courts en rotation
    for i, match in enumerate(matches):
        court_index = i % len(court_ids)
        match.court_id = court_ids[court_index]
    
    db.commit()


@router.delete("/bracket")
def delete_bracket(
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Supprime le bracket et réinitialise le tournoi"""
    tournament = check_ja_for_tournament(db, tournament_id, user.id)
    
    # Supprimer tous les matchs et rounds
    rounds = db.query(Round).filter(
        Round.tournament_id == tournament_id
    ).all()
    
    for r in rounds:
        db.query(Match).filter(Match.round_id == r.id).delete()
    
    db.query(Round).filter(Round.tournament_id == tournament_id).delete()
    
    # Réinitialiser le statut du tournoi
    tournament.bracket_generated = False
    tournament.is_finished = False
    
    db.commit()
    
    return {"message": "Bracket deleted"}


@router.get("/rounds")
def get_rounds(
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Récupère tous les rounds d'un tournoi avec leurs matchs et équipes"""
    tournament = check_ja_for_tournament(db, tournament_id, user.id)

    rounds = db.query(Round).filter(
        Round.tournament_id == tournament_id
    ).order_by(Round.order).all()

    result = []
    for round_ in rounds:
        matches = db.query(Match).filter(
            Match.round_id == round_.id
        ).order_by(Match.match_order).all()

        matches_data = []
        for match in matches:
            # Récupérer team1 avec ses joueurs
            team1_data = None
            if match.team1_id:
                team1 = db.query(Team).filter(Team.id == match.team1_id).first()
                if team1:
                    players1 = db.query(Player).filter(Player.team_id == team1.id).all()
                    team1_data = {
                        "id": str(team1.id),
                        "seed": team1.seed,
                        "players": [
                            {
                                "id": str(p.id),
                                "first_name": p.first_name,
                                "last_name": p.last_name,
                                "license_number": p.license_number,
                                "ranking": p.ranking
                            }
                            for p in players1
                        ]
                    }

            # Récupérer team2 avec ses joueurs
            team2_data = None
            if match.team2_id:
                team2 = db.query(Team).filter(Team.id == match.team2_id).first()
                if team2:
                    players2 = db.query(Player).filter(Player.team_id == team2.id).all()
                    team2_data = {
                        "id": str(team2.id),
                        "seed": team2.seed,
                        "players": [
                            {
                                "id": str(p.id),
                                "first_name": p.first_name,
                                "last_name": p.last_name,
                                "license_number": p.license_number,
                                "ranking": p.ranking
                            }
                            for p in players2
                        ]
                    }
            
            # Récupérer le court
            court_data = None
            if match.court_id:
                court = db.query(Court).filter(Court.id == match.court_id).first()
                if court:
                    court_data = {
                        "id": str(court.id),
                        "name": court.name,
                        "indoor": court.indoor
                    }

            matches_data.append({
                "id": str(match.id),
                "round_id": str(match.round_id),
                "match_order": match.match_order,
                "team1_id": str(match.team1_id) if match.team1_id else None,
                "team2_id": str(match.team2_id) if match.team2_id else None,
                "team1": team1_data,
                "team2": team2_data,
                "winner_id": str(match.winner_id) if match.winner_id else None,
                "court_id": str(match.court_id) if match.court_id else None,
                "court": court_data,
                "score": match.score,
                "is_finished": match.is_finished
            })

        result.append({
            "id": str(round_.id),
            "tournament_id": str(round_.tournament_id),
            "name": round_.name,
            "order": round_.order,
            "matches": matches_data
        })

    return result


@router.get("/info")
def get_tournament_info(
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Récupère les infos du tournoi incluant bracket_generated et selected_court_ids"""
    tournament = check_ja_for_tournament(db, tournament_id, user.id)
    
    selected_courts = []
    if tournament.selected_court_ids:
        try:
            selected_courts = json.loads(tournament.selected_court_ids)
        except:
            selected_courts = []
    
    return {
        "id": str(tournament.id),
        "name": tournament.name,
        "category": tournament.category,
        "gender": tournament.gender,
        "start_date": str(tournament.start_date),
        "end_date": str(tournament.end_date) if tournament.end_date else None,
        "indoor": tournament.indoor,
        "is_finished": tournament.is_finished,
        "bracket_generated": tournament.bracket_generated,
        "selected_court_ids": selected_courts
    }