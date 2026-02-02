from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.services.bracket_generator import generate_bracket
from app.services.points_calculator import get_points, get_available_categories
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
    
    court_ids = payload.court_ids if payload and payload.court_ids else []
    if court_ids:
        tournament.selected_court_ids = json.dumps(court_ids)
    
    # Passer les court_ids au générateur pour assigner les terrains
    result = generate_bracket(db, tournament_id, court_ids)
    
    tournament.bracket_generated = True
    db.commit()
    
    return result


def assign_courts_to_first_round(db: Session, tournament_id: str, court_ids: List[str]):
    """Assigne les courts aux matchs du premier round - DEPRECATED, maintenant fait dans generate_bracket"""
    first_round = db.query(Round).filter(
        Round.tournament_id == tournament_id,
        Round.order == 1
    ).first()
    
    if not first_round or not court_ids:
        return
    
    matches = db.query(Match).filter(
        Match.round_id == first_round.id
    ).order_by(Match.match_order).all()
    
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
    
    rounds = db.query(Round).filter(
        Round.tournament_id == tournament_id
    ).all()
    
    for r in rounds:
        db.query(Match).filter(Match.round_id == r.id).delete()
    
    db.query(Round).filter(Round.tournament_id == tournament_id).delete()
    
    tournament.bracket_generated = False
    tournament.is_finished = False
    
    db.commit()
    
    return {"message": "Bracket deleted"}


def get_match_data(db: Session, match: Match) -> dict:
    """Construit les données d'un match avec équipes et court"""
    team1_data = None
    if match.team1_id:
        team1 = db.query(Team).filter(Team.id == match.team1_id).first()
        if team1:
            players1 = db.query(Player).filter(Player.team_id == team1.id).all()
            team1_data = {
                "id": str(team1.id),
                "combined_ranking": team1.combined_ranking,
                "is_seeded": team1.is_seeded,
                "seed_position": team1.seed_position,
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

    team2_data = None
    if match.team2_id:
        team2 = db.query(Team).filter(Team.id == match.team2_id).first()
        if team2:
            players2 = db.query(Player).filter(Player.team_id == team2.id).all()
            team2_data = {
                "id": str(team2.id),
                "combined_ranking": team2.combined_ranking,
                "is_seeded": team2.is_seeded,
                "seed_position": team2.seed_position,
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
    
    court_data = None
    if match.court_id:
        court = db.query(Court).filter(Court.id == match.court_id).first()
        if court:
            court_data = {
                "id": str(court.id),
                "name": court.name,
                "indoor": court.indoor
            }

    return {
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
        "is_finished": match.is_finished,
        "bracket_type": match.bracket_type or 'winner',
        "classification_rank": match.classification_rank
    }


@router.get("/rounds")
def get_rounds(
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Récupère les rounds du winner bracket"""
    check_ja_for_tournament(db, tournament_id, user.id)

    # Rounds du winner bracket (order < 100)
    rounds = db.query(Round).filter(
        Round.tournament_id == tournament_id,
        Round.order < 100
    ).order_by(Round.order).all()

    result = []
    for round_ in rounds:
        matches = db.query(Match).filter(
            Match.round_id == round_.id
        ).order_by(Match.match_order).all()

        matches_data = [get_match_data(db, m) for m in matches]

        result.append({
            "id": str(round_.id),
            "tournament_id": str(round_.tournament_id),
            "name": round_.name,
            "order": round_.order,
            "matches": matches_data
        })

    return result


@router.get("/classification-rounds")
def get_classification_rounds(
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Récupère les rounds de classement (loser bracket)"""
    check_ja_for_tournament(db, tournament_id, user.id)

    # Rounds de classement (order >= 100)
    rounds = db.query(Round).filter(
        Round.tournament_id == tournament_id,
        Round.order >= 100
    ).order_by(Round.order).all()

    result = []
    for round_ in rounds:
        matches = db.query(Match).filter(
            Match.round_id == round_.id
        ).order_by(Match.match_order).all()

        matches_data = [get_match_data(db, m) for m in matches]

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
    """Récupère les infos du tournoi"""
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


@router.get("/final-rankings")
def get_final_rankings(
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Calcule le classement final avec les points attribués.
    Doit être appelé une fois le tournoi terminé.
    """
    tournament = check_ja_for_tournament(db, tournament_id, user.id)
    
    # Récupérer toutes les équipes
    teams = db.query(Team).filter(Team.tournament_id == tournament_id).all()
    num_teams = len(teams)
    
    if num_teams == 0:
        return {"rankings": [], "tournament_finished": False}
    
    # Récupérer tous les matchs pour déterminer le classement
    rounds = db.query(Round).filter(
        Round.tournament_id == tournament_id
    ).order_by(Round.order).all()
    
    rankings = {}  # team_id -> {"rank": X, "team": team_data}
    
    # Parcourir les matchs pour déterminer les classements
    for round_ in rounds:
        matches = db.query(Match).filter(Match.round_id == round_.id).all()
        
        for match in matches:
            if not match.is_finished:
                continue
            
            # Finale (winner bracket, dernier round < 100)
            if round_.name == "Finale" and match.winner_id:
                rankings[str(match.winner_id)] = {"rank": 1}
                loser_id = str(match.team1_id) if str(match.winner_id) == str(match.team2_id) else str(match.team2_id)
                if loser_id and loser_id != "None":
                    rankings[loser_id] = {"rank": 2}
            
            # Match 3ème place
            elif round_.name == "Match 3ème place" and match.winner_id:
                rankings[str(match.winner_id)] = {"rank": 3}
                loser_id = str(match.team1_id) if str(match.winner_id) == str(match.team2_id) else str(match.team2_id)
                if loser_id and loser_id != "None":
                    rankings[loser_id] = {"rank": 4}
            
            # Match 5ème place
            elif round_.name == "Match 5ème place" and match.winner_id:
                rankings[str(match.winner_id)] = {"rank": 5}
                loser_id = str(match.team1_id) if str(match.winner_id) == str(match.team2_id) else str(match.team2_id)
                if loser_id and loser_id != "None":
                    rankings[loser_id] = {"rank": 6}
            
            # Match 7ème place
            elif round_.name == "Match 7ème place" and match.winner_id:
                rankings[str(match.winner_id)] = {"rank": 7}
                loser_id = str(match.team1_id) if str(match.winner_id) == str(match.team2_id) else str(match.team2_id)
                if loser_id and loser_id != "None":
                    rankings[loser_id] = {"rank": 8}
    
    # Assigner un rang par défaut aux équipes non classées (perdants premiers tours)
    next_rank = 9
    for team in teams:
        team_id = str(team.id)
        if team_id not in rankings:
            rankings[team_id] = {"rank": next_rank}
            next_rank += 1
    
    # Construire le résultat final avec les points
    result = []
    category = tournament.category or "P25"
    
    for team in teams:
        team_id = str(team.id)
        rank = rankings.get(team_id, {}).get("rank", num_teams)
        points = get_points(category, rank, num_teams)
        
        players = db.query(Player).filter(Player.team_id == team.id).all()
        
        result.append({
            "rank": rank,
            "points": points,
            "team_id": team_id,
            "combined_ranking": team.combined_ranking,
            "is_seeded": team.is_seeded,
            "seed_position": team.seed_position,
            "players": [
                {
                    "id": str(p.id),
                    "first_name": p.first_name,
                    "last_name": p.last_name,
                    "ranking": p.ranking
                }
                for p in players
            ]
        })
    
    # Trier par rang
    result.sort(key=lambda x: x["rank"])
    
    # Vérifier si le tournoi est terminé (finale jouée)
    finale_played = any(r["rank"] == 1 for r in result)
    
    return {
        "tournament_id": str(tournament.id),
        "tournament_name": tournament.name,
        "category": category,
        "num_teams": num_teams,
        "tournament_finished": finale_played,
        "rankings": result
    }


@router.post("/finish")
def finish_tournament(
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Marque le tournoi comme terminé"""
    tournament = check_ja_for_tournament(db, tournament_id, user.id)
    tournament.is_finished = True
    db.commit()
    return {"message": "Tournament marked as finished"}