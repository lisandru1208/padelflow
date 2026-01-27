from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.services.bracket_generator import generate_bracket

router = APIRouter(
    prefix="/tournaments/{tournament_id}",
    tags=["bracket"]
)

@router.post("/generate-bracket")
def generate(
    tournament_id: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    return generate_bracket(db, tournament_id)
