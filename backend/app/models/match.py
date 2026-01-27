import uuid
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class Match(Base):
    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    round_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rounds.id"),
        nullable=False
    )

    match_order = Column(Integer, nullable=False)
    team1_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    team2_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    winner_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    court_id = Column(UUID(as_uuid=True), ForeignKey("courts.id"), nullable=True)
