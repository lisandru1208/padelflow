from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.services.bracket_generator import generate_bracket
from app.models.round import Round
from app.models.match import Match
from app.models.team import Team
from app.models.player import Player
from app.models.tournament import Tournament
from app.models.club_user import ClubUser

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


@router.post("/generate-bracket")
def generate(
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    check_ja_for_tournament(db, tournament_id, user.id)
    return generate_bracket(db, tournament_id)


@router.get("/rounds")
def get_rounds(
    tournament_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Récupère tous les rounds d'un tournoi avec leurs matchs et équipes"""
    check_ja_for_tournament(db, tournament_id, user.id)

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