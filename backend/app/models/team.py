import uuid
from sqlalchemy import Column, Integer, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tournament_id = Column(UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=False)
    combined_ranking = Column(Integer, nullable=True)
    is_seeded = Column(Boolean, default=False)
    seed_position = Column(Integer, nullable=True)