from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.team import Team
from app.models.player import Player
from app.models.tournament import Tournament
from app.models.club_user import ClubUser
from app.models.pool_tournament import PoolMatch, PoolTeam

router = APIRouter(
    prefix="/tournaments/{tournament_id}/teams",
    tags=["teams"]
)


# ----------- Schemas -----------

class PlayerCreate(BaseModel):
    first_name: str
    last_name: str
    license_number: str
    ranking: int


class TeamCreate(BaseModel):
    players: List[PlayerCreate]


class PlayerResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    license_number: str
    ranking: int


class TeamResponse(BaseModel):
    id: str
    tournament_id: str
    combined_ranking: Optional[int]
    is_seeded: bool
    seed_position: Optional[int]
    players: List[PlayerResponse]


# ----------- Helpers -----------

def check_ja_for_tournament(db: Session, tournament_id: str, user_id: str):
    """Vérifie que l'utilisateur est JA du club du tournoi"""
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    membership = db.query(ClubUser).filter(
        ClubUser.club_id == tournament.club_id,
        ClubUser.user_id == user_id
    ).first()

    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")

    return tournament


def calculate_seeds(db: Session, tournament_id: str):
    """
    Calcule automatiquement les têtes de série basées sur le classement combiné.
    Les équipes avec le classement combiné le plus bas sont les meilleures.
    """
    teams = db.query(Team).filter(Team.tournament_id == tournament_id).all()
    
    if not teams:
        return
    
    # Calculer le nombre de têtes de série nécessaires
    # Généralement, on prend 1/4 des équipes comme têtes de série (min 2, max 8)
    num_teams = len(teams)
    num_seeds = min(max(num_teams // 4, 2), 8)
    
    if num_teams <= 4:
        num_seeds = 2
    elif num_teams <= 8:
        num_seeds = 4
    elif num_teams <= 16:
        num_seeds = 4
    else:
        num_seeds = 8
    
    # Trier les équipes par classement combiné (plus bas = meilleur)
    teams_sorted = sorted(
        [t for t in teams if t.combined_ranking is not None],
        key=lambda t: t.combined_ranking
    )
    
    # Réinitialiser toutes les têtes de série
    for team in teams:
        team.is_seeded = False
        team.seed_position = None
    
    # Assigner les têtes de série
    for i, team in enumerate(teams_sorted[:num_seeds]):
        team.is_seeded = True
        team.seed_position = i + 1
    
    db.commit()


# ----------- Endpoints -----------

@router.post("/", response_model=TeamResponse)
def create_team(
    tournament_id: str,
    payload: TeamCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    tournament = check_ja_for_tournament(db, tournament_id, user.id)

    if tournament.bracket_generated:
        raise HTTPException(
            status_code=400,
            detail="Cannot add teams after bracket is generated"
        )

    if len(payload.players) != 2:
        raise HTTPException(status_code=400, detail="A team must have exactly 2 players")

    # Calculer le classement combiné
    combined_ranking = sum(p.ranking for p in payload.players)

    # Créer l'équipe
    team = Team(
        tournament_id=tournament_id,
        combined_ranking=combined_ranking,
        is_seeded=False,
        seed_position=None
    )
    db.add(team)
    db.commit()
    db.refresh(team)

    # Créer les joueurs
    players_db = []
    for p in payload.players:
        player = Player(
            team_id=team.id,
            first_name=p.first_name,
            last_name=p.last_name,
            license_number=p.license_number,
            ranking=p.ranking
        )
        db.add(player)
        players_db.append(player)

    db.commit()

    # Recalculer les têtes de série pour tout le tournoi
    calculate_seeds(db, tournament_id)

    # Rafraîchir l'équipe pour avoir les valeurs à jour
    db.refresh(team)

    return {
        "id": str(team.id),
        "tournament_id": str(team.tournament_id),
        "combined_ranking": team.combined_ranking,
        "is_seeded": team.is_seeded,
        "seed_position": team.seed_position,
        "players": [
            {
                "id": str(p.id),
                "first_name": p.first_name,
                "last_name": p.last_name,
                "license_number": p.license_number,
                "ranking": p.ranking
            }
            for p in players_db
        ]
    }


@router.get("/", response_model=List[TeamResponse])
def list_teams(
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    check_ja_for_tournament(db, tournament_id, user.id)

    teams = db.query(Team).filter(Team.tournament_id == tournament_id).all()

    result = []
    for team in teams:
        players = db.query(Player).filter(Player.team_id == team.id).all()
        result.append({
            "id": str(team.id),
            "tournament_id": str(team.tournament_id),
            "combined_ranking": team.combined_ranking,
            "is_seeded": team.is_seeded,
            "seed_position": team.seed_position,
            "players": [
                {
                    "id": str(p.id),
                    "first_name": p.first_name,
                    "last_name": p.last_name,
                    "license_number": p.license_number,
                    "ranking": p.ranking
                }
                for p in players
            ]
        })

    # Trier par classement combiné (meilleurs en premier)
    result.sort(key=lambda t: t["combined_ranking"] if t["combined_ranking"] else 9999)

    return result


@router.delete("/{team_id}")
def delete_team(
    tournament_id: str,
    team_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    tournament = check_ja_for_tournament(db, tournament_id, user.id)

    if tournament.bracket_generated:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete teams after bracket is generated"
        )

    team = db.query(Team).filter(
        Team.id == team_id,
        Team.tournament_id == tournament_id
    ).first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Supprimer les références dans pool_matches
    db.query(PoolMatch).filter(
        (PoolMatch.team1_id == team_id) | 
        (PoolMatch.team2_id == team_id) |
        (PoolMatch.winner_id == team_id)
    ).delete(synchronize_session=False)
    
    # Supprimer les références dans pool_teams
    db.query(PoolTeam).filter(PoolTeam.team_id == team_id).delete(synchronize_session=False)

    # Supprimer les joueurs
    db.query(Player).filter(Player.team_id == team_id).delete()
    
    # Supprimer l'équipe
    db.delete(team)
    db.commit()

    # Recalculer les têtes de série
    calculate_seeds(db, tournament_id)

    return {"message": "Team deleted"}


@router.post("/recalculate-seeds")
def recalculate_seeds(
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Recalcule manuellement les têtes de série"""
    tournament = check_ja_for_tournament(db, tournament_id, user.id)

    if tournament.bracket_generated:
        raise HTTPException(
            status_code=400,
            detail="Cannot recalculate seeds after bracket is generated"
        )

    calculate_seeds(db, tournament_id)

    return {"message": "Seeds recalculated"}


@router.get("/bracket-info")
def get_bracket_info(
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Retourne des informations utiles pour la génération du bracket :
    - Nombre d'équipes
    - Taille du bracket (puissance de 2)
    - Nombre de BYE nécessaires
    - Nombre de têtes de série
    - Recommandation (bracket ou poule)
    - Nombre de terrains recommandé
    """
    import math
    
    check_ja_for_tournament(db, tournament_id, user.id)

    teams = db.query(Team).filter(Team.tournament_id == tournament_id).all()
    num_teams = len(teams)

    if num_teams < 2:
        return {
            "num_teams": num_teams,
            "bracket_size": 0,
            "num_byes": 0,
            "num_seeds": 0,
            "recommendation": "minimum",
            "message": "Il faut au moins 2 équipes",
            "recommended_courts": 1
        }

    # Calculer la taille du bracket
    bracket_size = 2 ** math.ceil(math.log2(num_teams))
    num_byes = bracket_size - num_teams
    bye_percentage = (num_byes / bracket_size) * 100

    # Nombre de têtes de série
    seeded_teams = [t for t in teams if t.is_seeded]
    num_seeds = len(seeded_teams)

    # Recommandation
    if num_teams <= 3:
        recommendation = "poule"
        message = f"Avec {num_teams} équipes, un format poule est recommandé"
    elif bye_percentage > 40:
        recommendation = "poule"
        message = f"Trop de BYE ({num_byes}). Un format poule est recommandé"
    else:
        recommendation = "bracket"
        message = f"Format bracket avec {num_byes} BYE"

    # Nombre de terrains recommandé
    # Règle : environ 1 terrain pour 4 équipes, min 1, max selon nombre de matchs simultanés possibles
    first_round_matches = bracket_size // 2
    recommended_courts = max(1, min(first_round_matches, num_teams // 4))

    return {
        "num_teams": num_teams,
        "bracket_size": bracket_size,
        "num_byes": num_byes,
        "bye_percentage": round(bye_percentage, 1),
        "num_seeds": num_seeds,
        "recommendation": recommendation,
        "message": message,
        "recommended_courts": recommended_courts,
        "first_round_matches": first_round_matches
    }