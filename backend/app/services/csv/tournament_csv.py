import csv
from sqlalchemy.orm import Session

from app.models.tournament import Tournament
from app.models.round import Round
from app.models.match import Match
from app.models.team import Team
from app.models.court import Court


def generate_tournament_csv(db: Session, tournament_id: str, output_path: str):
    tournament = db.query(Tournament).filter(
        Tournament.id == tournament_id
    ).first()

    if not tournament:
        raise ValueError("Tournament not found")

    rounds = (
        db.query(Round)
        .filter(Round.tournament_id == tournament_id)
        .order_by(Round.order.desc())  # ordre MOJA
        .all()
    )

    with open(output_path, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile, delimiter=";")

        # Header
        writer.writerow([
            "tournament_name",
            "round_order",
            "round_name",
            "match_order",
            "team1",
            "team2",
            "score",
            "winner",
            "court"
        ])

        for round_ in rounds:
            matches = (
                db.query(Match)
                .filter(Match.round_id == round_.id)
                .order_by(Match.match_order)
                .all()
            )

            for match in matches:
                team1 = db.query(Team).filter(Team.id == match.team1_id).first()
                team2 = db.query(Team).filter(Team.id == match.team2_id).first()
                winner = db.query(Team).filter(Team.id == match.winner_id).first()
                court = db.query(Court).filter(Court.id == match.court_id).first()

                writer.writerow([
                    tournament.name,
                    round_.order,
                    round_.name,
                    match.match_order,
                    team1.name if team1 else "BYE",
                    team2.name if team2 else "BYE",
                    match.score or "",
                    winner.name if winner else "",
                    court.name if court else ""
                ])
