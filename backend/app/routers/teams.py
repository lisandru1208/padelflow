from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.team import Team
from app.models.tournament import Tournament
from app.models.club_user import ClubUser

router = APIRouter(
    prefix="/tournaments/{tournament_id}/teams",
    tags=["teams"]
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


@router.post("/")
def add_team(
    tournament_id: str,
    name: str,
    seed: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    check_ja_for_tournament(db, tournament_id, user.id)

    if seed is not None:
        existing_seed = db.query(Team).filter(
            Team.tournament_id == tournament_id,
            Team.seed == seed
        ).first()
        if existing_seed:
            raise HTTPException(
                status_code=400,
                detail=f"Seed {seed} already used"
            )

    team = Team(
        tournament_id=tournament_id,
        name=name,
        seed=seed
    )

    db.add(team)
    db.commit()
    db.refresh(team)

    return team


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

    db.delete(team)
    db.commit()

    return {"message": "Team deleted"}
