from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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
def create_team(
    tournament_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    check_ja_for_tournament(db, tournament_id, user.id)

    players = payload.get("players")
    seed = payload.get("seed")

    # 🧠 Validation métier
    if not players or len(players) != 2:
        raise HTTPException(
            status_code=400,
            detail="A team must have exactly 2 players"
        )

    license_numbers = [p.get("license_number") for p in players]
    if len(set(license_numbers)) != 2:
        raise HTTPException(
            status_code=400,
            detail="Players must have unique license numbers"
        )

    # Vérifier seed unique si renseignée
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

    # Création de l'équipe
    team = Team(
        tournament_id=tournament_id,
        seed=seed
    )
    db.add(team)
    db.commit()
    db.refresh(team)

    # Création des joueurs
    for p in players:
        player = Player(
            team_id=team.id,
            first_name=p["first_name"],
            last_name=p["last_name"],
            license_number=p["license_number"],
            ranking=p["ranking"]
        )
        db.add(player)

    db.commit()

    return {
        "team_id": team.id,
        "seed": team.seed,
        "players": players
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

    # Supprimer joueurs
    db.query(Player).filter(
        Player.team_id == team.id
    ).delete()

    db.delete(team)
    db.commit()

    return {"message": "Team deleted"}
