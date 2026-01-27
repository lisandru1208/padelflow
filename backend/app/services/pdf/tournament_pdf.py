from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.models.tournament import Tournament
from app.models.round import Round
from app.models.match import Match
from app.models.team import Team


def generate_tournament_pdf(db: Session, tournament_id: str, output_path: str):
    tournament = db.query(Tournament).filter(
        Tournament.id == tournament_id
    ).first()

    if not tournament:
        raise ValueError("Tournament not found")

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    # ---- PAGE 1 : EN-TÊTE ----
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 40, f"Tournoi : {tournament.name}")

    c.setFont("Helvetica", 11)
    c.drawString(40, height - 70, f"Catégorie : {tournament.category}")
    c.drawString(40, height - 90, f"Date : {tournament.start_date}")

    c.showPage()

    # ---- MATCHS (ordre MOJA) ----
    rounds = (
        db.query(Round)
        .filter(Round.tournament_id == tournament_id)
        .order_by(Round.order.desc())  # IMPORTANT
        .all()
    )

    for round_ in rounds:
        c.setFont("Helvetica-Bold", 13)
        c.drawString(40, height - 40, f"Round : {round_.name}")

        y = height - 80

        matches = (
            db.query(Match)
            .filter(Match.round_id == round_.id)
            .order_by(Match.match_order)
            .all()
        )

        for match in matches:
            team1 = db.query(Team).filter(Team.id == match.team1_id).first()
            team2 = db.query(Team).filter(Team.id == match.team2_id).first()

            line = f"{team1.name if team1 else 'BYE'}"
            line += " vs "
            line += f"{team2.name if team2 else 'BYE'}"
            line += f" — Score : {match.score or 'N/A'}"

            c.setFont("Helvetica", 10)
            c.drawString(40, y, line)
            y -= 20

            if y < 60:
                c.showPage()
                y = height - 40

        c.showPage()

    c.save()
