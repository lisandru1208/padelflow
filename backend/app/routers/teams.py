from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, conlist

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.team import Team
from app.models.player import Player
from app.models.tournament import Tournament
from app.models.club_user import ClubUser

router = APIRouter(
    prefix="/tournaments/{tournament_id}/teams",
    tags=["teams"]
)

# -------------------------
# SCHEMAS (Pydantic)
# -------------------------

class PlayerCreate(BaseModel):
    first_name: str
    last_name: str
    license_number: str
    ranking: int


class TeamCreate(BaseModel):
    seed: Optional[int] = None
    players: conlist(PlayerCreate, min_items=2, max_items=2)


# -------------------------
# HELPERS
# -------------------------

def check_ja_for_tournament(
    db: Session,
    tournament_id: str,
    user_id: str
):
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


# -------------------------
# ROUTES
# -------------------------

@router.post("/")
def create_team(
    tournament_id: str,
    team: TeamCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    check_ja_for_tournament(db, tournament_id, user.id)

    # Validation métier
    if len(team.players) != 2:
        raise HTTPException(
            status_code=400,
            detail="A team must contain exactly 2 players"
        )

    licenses = [p.license_number for p in team.players]
    if len(set(licenses)) != 2:
        raise HTTPException(
            status_code=400,
            detail="Players must have different license numbers"
        )

    if team.seed is not None:
        existing_seed = db.query(Team).filter(
            Team.tournament_id == tournament_id,
            Team.seed == team.seed
        ).first()
        if existing_seed:
            raise HTTPException(
                status_code=400,
                detail=f"Seed {team.seed} already used"
            )

    # Création équipe
    team_db = Team(
        tournament_id=tournament_id,
        seed=team.seed
    )
    db.add(team_db)
    db.commit()
    db.refresh(team_db)

    # Création joueurs
    for p in team.players:
        db.add(Player(
            team_id=team_db.id,
            first_name=p.first_name,
            last_name=p.last_name,
            license_number=p.license_number,
            ranking=p.ranking
        ))

    db.commit()

    return {
        "team_id": team_db.id,
        "seed": team_db.seed
    }


@router.delete("/{team_id}")
def delete_team(
    tournament_id: str,
    team_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    check_ja_for_tournament(db, tournament_id, user.id)

    team = db.query(Team).filter(
        Team.id == team_id,
        Team.tournament_id == tournament_id
    ).first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    db.query(Player).filter(
        Player.team_id == team.id
    ).delete()

    db.delete(team)
    db.commit()

    return {"message": "Team deleted"}
