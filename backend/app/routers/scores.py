from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.match import Match
from app.models.round import Round
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

    match.score = payload.score
    match.winner_id = winner_id_str
    match.is_finished = True

    db.commit()

    # Propager le vainqueur au match suivant (winner bracket)
    propagate_winner(db, match)
    
    # Propager le perdant vers les matchs de classement
    propagate_loser(db, match, loser_id_str)

    return {
        "message": "Score saved",
        "match_id": str(match.id),
        "winner_team_id": str(match.winner_id)
    }


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
    """Propage le perdant vers les matchs de classement appropriés"""
    if match.bracket_type != 'winner':
        # Si c'est déjà un match de classement, propager vers le match suivant
        propagate_loser_bracket_winner(db, match)
        propagate_loser_bracket_loser(db, match, loser_id)
        return
    
    current_round = db.query(Round).filter(Round.id == match.round_id).first()
    if not current_round:
        return
    
    tournament_id = current_round.tournament_id
    round_order = current_round.order
    
    # Compter le nombre total de rounds winner
    total_winner_rounds = db.query(Round).filter(
        Round.tournament_id == tournament_id,
        Round.order < 100
    ).count()
    
    # Demi-finales (avant-dernier round) → Match 3ème place
    if round_order == total_winner_rounds - 1:
        # Trouver le match de 3ème place
        round_3rd = db.query(Round).filter(
            Round.tournament_id == tournament_id,
            Round.name == "Match 3ème place"
        ).first()
        
        if round_3rd:
            match_3rd = db.query(Match).filter(
                Match.round_id == round_3rd.id,
                Match.match_order == 1
            ).first()
            
            if match_3rd:
                # Match 1 des demis → team1, Match 2 → team2
                if match.match_order == 1:
                    match_3rd.team1_id = loser_id
                else:
                    match_3rd.team2_id = loser_id
                db.commit()
    
    # Quarts de finale (2 rounds avant la finale) → Matchs 5-8ème
    elif round_order == total_winner_rounds - 2:
        round_5th = db.query(Round).filter(
            Round.tournament_id == tournament_id,
            Round.name == "Matchs 5-8ème"
        ).first()
        
        if round_5th:
            # 4 perdants des quarts → 2 matchs de demi-finale loser
            # Match 1,2 quarts → match 1 loser
            # Match 3,4 quarts → match 2 loser
            loser_match_order = (match.match_order + 1) // 2
            
            loser_match = db.query(Match).filter(
                Match.round_id == round_5th.id,
                Match.match_order == loser_match_order
            ).first()
            
            if loser_match:
                if match.match_order % 2 == 1:
                    loser_match.team1_id = loser_id
                else:
                    loser_match.team2_id = loser_id
                db.commit()


def propagate_loser_bracket_winner(db: Session, match: Match):
    """Propage le vainqueur d'un match de classement vers le match suivant"""
    current_round = db.query(Round).filter(Round.id == match.round_id).first()
    if not current_round:
        return
    
    tournament_id = current_round.tournament_id
    
    # Si c'est un match des "Matchs 5-8ème", le vainqueur va au "Match 5ème place"
    if current_round.name == "Matchs 5-8ème":
        round_5th_final = db.query(Round).filter(
            Round.tournament_id == tournament_id,
            Round.name == "Match 5ème place"
        ).first()
        
        if round_5th_final:
            match_5th = db.query(Match).filter(
                Match.round_id == round_5th_final.id,
                Match.match_order == 1
            ).first()
            
            if match_5th:
                if match.match_order == 1:
                    match_5th.team1_id = match.winner_id
                else:
                    match_5th.team2_id = match.winner_id
                db.commit()


def propagate_loser_bracket_loser(db: Session, match: Match, loser_id: str):
    """Propage le perdant d'un match de classement vers le match de 7ème place"""
    current_round = db.query(Round).filter(Round.id == match.round_id).first()
    if not current_round:
        return
    
    tournament_id = current_round.tournament_id
    
    # Si c'est un match des "Matchs 5-8ème", le perdant va au "Match 7ème place"
    if current_round.name == "Matchs 5-8ème":
        round_7th = db.query(Round).filter(
            Round.tournament_id == tournament_id,
            Round.name == "Match 7ème place"
        ).first()
        
        if round_7th:
            match_7th = db.query(Match).filter(
                Match.round_id == round_7th.id,
                Match.match_order == 1
            ).first()
            
            if match_7th:
                if match.match_order == 1:
                    match_7th.team1_id = loser_id
                else:
                    match_7th.team2_id = loser_id
                db.commit()