from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import UploadFile, File
import csv
import io

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
    players: List[PlayerCreate] = Field(min_length=2, max_length=2)


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

@router.post("/import-csv")
def import_teams_csv(
    tournament_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    check_ja_for_tournament(db, tournament_id, user.id)

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    created = 0
    errors = []

    for i, row in enumerate(reader, start=1):
        try:
            # Validation minimale
            licenses = {
                row["p1_license"],
                row["p2_license"]
            }
            if len(licenses) != 2:
                raise ValueError("Duplicate license numbers")

            seed = row.get("team_seed")
            seed = int(seed) if seed else None

            # Vérifier seed unique
            if seed is not None:
                if db.query(Team).filter(
                    Team.tournament_id == tournament_id,
                    Team.seed == seed
                ).first():
                    raise ValueError(f"Seed {seed} already used")

            team = Team(
                tournament_id=tournament_id,
                seed=seed
            )
            db.add(team)
            db.commit()
            db.refresh(team)

            players = [
                Player(
                    team_id=team.id,
                    first_name=row["p1_first_name"],
                    last_name=row["p1_last_name"],
                    license_number=row["p1_license"],
                    ranking=int(row["p1_ranking"])
                ),
                Player(
                    team_id=team.id,
                    first_name=row["p2_first_name"],
                    last_name=row["p2_last_name"],
                    license_number=row["p2_license"],
                    ranking=int(row["p2_ranking"])
                )
            ]

            for p in players:
                db.add(p)

            db.commit()
            created += 1

        except Exception as e:
            errors.append({
                "line": i,
                "error": str(e)
            })

    return {
        "created_teams": created,
        "errors": errors
    }
