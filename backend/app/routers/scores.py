from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.match import Match
from app.models.round import Round
from app.models.tournament import Tournament
from app.routers.matches import check_ja_for_round


router = APIRouter(
    prefix="/matches",
    tags=["scores"]
)


class ScoreInput(BaseModel):
    score: str
    winner_team_id: str


@router.post("/{match_id}/score")
def submit_score(
    match_id: str,
    payload: ScoreInput,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Sécurité JA
    check_ja_for_round(db, str(match.round_id), user.id)

    if match.is_finished:
        raise HTTPException(status_code=400, detail="Match already finished")

    # Convertir les UUIDs en strings pour la comparaison
    team1_id_str = str(match.team1_id) if match.team1_id else None
    team2_id_str = str(match.team2_id) if match.team2_id else None
    winner_id_str = payload.winner_team_id.strip()

    if winner_id_str not in [team1_id_str, team2_id_str]:
        raise HTTPException(
            status_code=400, 
            detail=f"Winner not in match"
        )

    if not payload.score.strip():
        raise HTTPException(status_code=400, detail="Score cannot be empty")

    # Déterminer le perdant
    loser_id_str = team2_id_str if winner_id_str == team1_id_str else team1_id_str

    # Libérer le court du match terminé
    freed_court_id = match.court_id

    match.score = payload.score
    match.winner_id = winner_id_str
    match.is_finished = True

    db.commit()

    # Propager le vainqueur au match suivant (winner bracket)
    propagate_winner(db, match)
    
    # Propager le perdant vers les matchs de classement
    propagate_loser(db, match, loser_id_str)
    
    # Assigner le court libéré au prochain match disponible
    if freed_court_id:
        assign_court_to_next_match(db, match, freed_court_id)

    return {
        "message": "Score saved",
        "match_id": str(match.id),
        "winner_team_id": str(match.winner_id)
    }


def assign_court_to_next_match(db: Session, finished_match: Match, court_id):
    """Assigne le court libéré au prochain match prêt à jouer"""
    current_round = db.query(Round).filter(Round.id == finished_match.round_id).first()
    if not current_round:
        return
    
    tournament_id = current_round.tournament_id
    
    # Chercher un match prêt à jouer (2 équipes, pas de court, pas terminé)
    # Priorité : même round, puis round suivant, puis matchs de classement
    
    # 1. Chercher dans le même round
    next_match = db.query(Match).join(Round).filter(
        Round.tournament_id == tournament_id,
        Match.team1_id.isnot(None),
        Match.team2_id.isnot(None),
        Match.court_id.is_(None),
        Match.is_finished == False
    ).order_by(Round.order, Match.match_order).first()
    
    if next_match:
        next_match.court_id = court_id
        db.commit()


def propagate_winner(db: Session, match: Match):
    """Propage le vainqueur au match suivant dans le winner bracket"""
    if match.bracket_type != 'winner':
        # Pour les matchs de classement, pas de propagation winner
        return
    
    current_round = db.query(Round).filter(Round.id == match.round_id).first()
    if not current_round:
        return

    # Trouver le round suivant (winner bracket uniquement, order < 100)
    next_round = db.query(Round).filter(
        Round.tournament_id == current_round.tournament_id,
        Round.order == current_round.order + 1,
        Round.order < 100  # Les rounds de classement ont order >= 100
    ).first()

    if not next_round:
        return  # C'était la finale

    # Trouver le match suivant
    next_match_order = (match.match_order + 1) // 2
    next_match = db.query(Match).filter(
        Match.round_id == next_round.id,
        Match.match_order == next_match_order
    ).first()

    if not next_match:
        return

    # Les matchs impairs vont en team1, les pairs en team2
    if match.match_order % 2 == 1:
        next_match.team1_id = match.winner_id
    else:
        next_match.team2_id = match.winner_id

    db.commit()


def propagate_loser(db: Session, match: Match, loser_id: str):
    """Propage le perdant vers le tableau de classement approprié"""
    current_round = db.query(Round).filter(Round.id == match.round_id).first()
    if not current_round:
        return

    # Si on est DÉJÀ dans un tableau de classement
    if match.bracket_type != 'winner':
        propagate_sub_bracket(db, match, current_round, loser_id)
        return

    # Si on est dans le tableau principal
    # Loser va vers Order = current_round.order * 100
    target_round_order = current_round.order * 100
    
    print(f"Propagating Main Loser -> Round Order {target_round_order}")
    propagate_to_round(db, current_round.tournament_id, target_round_order, match.match_order, loser_id)


def propagate_sub_bracket(db: Session, match: Match, current_round: Round, loser_id: str):
    """Gère la propagation dans les tableaux de classement (vainqueur -> upper, perdant -> lower)"""
    
    if match.bracket_type == 'loser_final':
        return # Fin du chemin

    # Vainqueur -> Upper (+10)
    upper_round_order = current_round.order + 10
    propagate_to_round(db, current_round.tournament_id, upper_round_order, match.match_order, match.winner_id)
    
    # Perdant -> Lower (+20)
    lower_round_order = current_round.order + 20
    propagate_to_round(db, current_round.tournament_id, lower_round_order, match.match_order, loser_id)


def propagate_to_round(db: Session, tournament_id: str, target_order: int, source_match_order: int, team_id: str):
    """Helper générique pour déplacer une équipe vers le round cible"""
    target_round = db.query(Round).filter(
        Round.tournament_id == tournament_id,
        Round.order == target_order
    ).first()
    
    if target_round:
        target_match_order = (source_match_order + 1) // 2
        target_match = db.query(Match).filter(
            Match.round_id == target_round.id,
            Match.match_order == target_match_order
        ).first()
        
        if target_match:
            # Impair -> Team 1, Pair -> Team 2
            if source_match_order % 2 == 1:
                target_match.team1_id = team_id
                print(f"  -> Target Match {target_match_order} Team 1")
            else:
                target_match.team2_id = team_id
                print(f"  -> Target Match {target_match_order} Team 2")
            db.commit()
        else:
            print(f"  -> Target Match {target_match_order} NOT FOUND in Round {target_order}")
    else:
        print(f"  -> Target Round {target_order} NOT FOUND")
