from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.pool_tournament import Pool, PoolTeam, PoolMatch
from app.models.team import Team
from app.models.player import Player
from app.models.tournament import Tournament
from app.models.club_user import ClubUser
from app.models.court import Court
from app.services.pool_generator import (
    calculate_pool_configuration,
    generate_pools,
    calculate_pool_standings,
    generate_final_phase_from_pools
)

router = APIRouter(
    prefix="/tournaments/{tournament_id}/pools",
    tags=["pools"]
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


class GeneratePoolsInput(BaseModel):
    court_ids: Optional[List[str]] = None


class PoolMatchScoreInput(BaseModel):
    score: str
    winner_team_id: str
    team1_sets: int
    team2_sets: int
    team1_games: int
    team2_games: int


# ============================================
# ENDPOINTS
# ============================================

@router.get("/config")
def get_pool_configuration(
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Retourne la configuration recommandée pour les poules"""
    check_ja_for_tournament(db, tournament_id, user.id)
    
    teams = db.query(Team).filter(Team.tournament_id == tournament_id).all()
    num_teams = len(teams)
    
    if num_teams < 4:
        return {
            "num_teams": num_teams,
            "can_use_pools": False,
            "message": "Minimum 4 équipes pour le format poules"
        }
    
    config = calculate_pool_configuration(num_teams)
    config["num_teams"] = num_teams
    config["can_use_pools"] = True
    
    return config


@router.post("/generate")
def generate_tournament_pools(
    tournament_id: str,
    payload: Optional[GeneratePoolsInput] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Génère les poules pour le tournoi"""
    tournament = check_ja_for_tournament(db, tournament_id, user.id)
    
    court_ids = payload.court_ids if payload else None
    
    # Sauvegarder les courts sélectionnés
    if court_ids:
        tournament.selected_court_ids = json.dumps(court_ids)
    
    tournament.bracket_generated = True
    db.commit()
    
    result = generate_pools(db, tournament_id, court_ids)
    
    return result


@router.get("/")
def get_pools(
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Récupère toutes les poules avec leurs équipes et matchs"""
    check_ja_for_tournament(db, tournament_id, user.id)
    
    pools = db.query(Pool).filter(
        Pool.tournament_id == tournament_id
    ).order_by(Pool.pool_order).all()
    
    result = []
    for pool in pools:
        # Récupérer les équipes de la poule avec stats
        pool_teams = db.query(PoolTeam).filter(
            PoolTeam.pool_id == pool.id
        ).all()
        
        teams_data = []
        for pt in pool_teams:
            team = db.query(Team).filter(Team.id == pt.team_id).first()
            players = db.query(Player).filter(Player.team_id == team.id).all()
            
            teams_data.append({
                "pool_team_id": str(pt.id),
                "team_id": str(team.id),
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
                ],
                "stats": {
                    "matches_played": pt.matches_played,
                    "matches_won": pt.matches_won,
                    "matches_lost": pt.matches_lost,
                    "sets_won": pt.sets_won,
                    "sets_lost": pt.sets_lost,
                    "games_won": pt.games_won,
                    "games_lost": pt.games_lost,
                    "points": pt.points
                }
            })
        
        # Trier par points
        teams_data.sort(key=lambda x: (
            x["stats"]["points"],
            x["stats"]["sets_won"] - x["stats"]["sets_lost"],
            x["stats"]["games_won"] - x["stats"]["games_lost"]
        ), reverse=True)
        
        # Assigner les rangs
        for i, td in enumerate(teams_data):
            td["rank"] = i + 1
        
        # Récupérer les matchs de la poule
        matches = db.query(PoolMatch).filter(
            PoolMatch.pool_id == pool.id
        ).order_by(PoolMatch.match_order).all()
        
        matches_data = []
        for match in matches:
            team1 = db.query(Team).filter(Team.id == match.team1_id).first()
            team2 = db.query(Team).filter(Team.id == match.team2_id).first()
            
            players1 = db.query(Player).filter(Player.team_id == team1.id).all() if team1 else []
            players2 = db.query(Player).filter(Player.team_id == team2.id).all() if team2 else []
            
            court = None
            if match.court_id:
                court_obj = db.query(Court).filter(Court.id == match.court_id).first()
                if court_obj:
                    court = {"id": str(court_obj.id), "name": court_obj.name}
            
            matches_data.append({
                "id": str(match.id),
                "match_order": match.match_order,
                "team1_id": str(match.team1_id),
                "team2_id": str(match.team2_id),
                "team1": {
                    "id": str(team1.id),
                    "players": [{"first_name": p.first_name, "last_name": p.last_name} for p in players1]
                } if team1 else None,
                "team2": {
                    "id": str(team2.id),
                    "players": [{"first_name": p.first_name, "last_name": p.last_name} for p in players2]
                } if team2 else None,
                "score": match.score,
                "winner_id": str(match.winner_id) if match.winner_id else None,
                "is_finished": match.is_finished,
                "court": court
            })
        
        # Calculer la progression
        total_matches = len(matches)
        finished_matches = sum(1 for m in matches if m.is_finished)
        
        result.append({
            "id": str(pool.id),
            "name": pool.name,
            "pool_order": pool.pool_order,
            "teams": teams_data,
            "matches": matches_data,
            "progress": {
                "total": total_matches,
                "finished": finished_matches,
                "percentage": round((finished_matches / total_matches * 100) if total_matches > 0 else 0)
            }
        })
    
    return result


@router.post("/matches/{match_id}/score")
def submit_pool_match_score(
    tournament_id: str,
    match_id: str,
    payload: PoolMatchScoreInput,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Soumet le score d'un match de poule"""
    check_ja_for_tournament(db, tournament_id, user.id)
    
    match = db.query(PoolMatch).filter(PoolMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    if match.is_finished:
        raise HTTPException(status_code=400, detail="Match already finished")
    
    # Valider le vainqueur
    winner_id = payload.winner_team_id
    if winner_id not in [str(match.team1_id), str(match.team2_id)]:
        raise HTTPException(status_code=400, detail="Invalid winner")
    
    # Mettre à jour le match
    match.score = payload.score
    match.winner_id = winner_id
    match.team1_sets = payload.team1_sets
    match.team2_sets = payload.team2_sets
    match.team1_games = payload.team1_games
    match.team2_games = payload.team2_games
    match.is_finished = True
    
    # Mettre à jour les stats des équipes
    pt1 = db.query(PoolTeam).filter(
        PoolTeam.pool_id == match.pool_id,
        PoolTeam.team_id == match.team1_id
    ).first()
    
    pt2 = db.query(PoolTeam).filter(
        PoolTeam.pool_id == match.pool_id,
        PoolTeam.team_id == match.team2_id
    ).first()
    
    if pt1:
        pt1.matches_played += 1
        pt1.sets_won += payload.team1_sets
        pt1.sets_lost += payload.team2_sets
        pt1.games_won += payload.team1_games
        pt1.games_lost += payload.team2_games
        
        if winner_id == str(match.team1_id):
            pt1.matches_won += 1
            pt1.points += 2  # Victoire = 2 points
        else:
            pt1.matches_lost += 1
            pt1.points += 1  # Défaite = 1 point
    
    if pt2:
        pt2.matches_played += 1
        pt2.sets_won += payload.team2_sets
        pt2.sets_lost += payload.team1_sets
        pt2.games_won += payload.team2_games
        pt2.games_lost += payload.team1_games
        
        if winner_id == str(match.team2_id):
            pt2.matches_won += 1
            pt2.points += 2
        else:
            pt2.matches_lost += 1
            pt2.points += 1
    
    db.commit()
    
    return {"message": "Score saved", "match_id": match_id}


@router.post("/generate-final-phase")
def generate_final_phase(
    tournament_id: str,
    payload: Optional[GeneratePoolsInput] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Génère la phase finale à partir des résultats des poules"""
    check_ja_for_tournament(db, tournament_id, user.id)
    
    court_ids = payload.court_ids if payload else None
    
    result = generate_final_phase_from_pools(db, tournament_id, court_ids)
    
    return result


@router.delete("/reset")
def reset_pools(
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Réinitialise les poules du tournoi"""
    tournament = check_ja_for_tournament(db, tournament_id, user.id)
    
    # Supprimer les poules
    pools = db.query(Pool).filter(Pool.tournament_id == tournament_id).all()
    
    for pool in pools:
        db.query(PoolMatch).filter(PoolMatch.pool_id == pool.id).delete()
        db.query(PoolTeam).filter(PoolTeam.pool_id == pool.id).delete()
    
    db.query(Pool).filter(Pool.tournament_id == tournament_id).delete()
    
    # Supprimer les rounds de phase finale
    rounds = db.query(Round).filter(Round.tournament_id == tournament_id).all()
    for r in rounds:
        db.query(Match).filter(Match.round_id == r.id).delete()
    db.query(Round).filter(Round.tournament_id == tournament_id).delete()
    
    tournament.bracket_generated = False
    db.commit()
    
    return {"message": "Pools reset"}